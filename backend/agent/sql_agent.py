"""
AskSQL Markets - NL-to-SQL agent

Two-step pipeline that works reliably with both small local models (Ollama)
and cloud models (OpenAI):
  1. Generate SQL - LLM receives schema context + question, returns only SQL
  2. Execute SQL - run against SQLite, get structured results (with retry on error)
  3. Explain - LLM receives question + results, returns plain-English answer

Avoids the ReAct agent loop (Thought/Action/Observation format) which
requires larger models to follow reliably
"""

import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .llm_factory import get_llm_and_embeddings
from .schema_store import get_schema_context

#Hard cap on rows returned to the UI - prevents cartesian-product floods
#when the LLM omits LIMIT on multi-table joins.
MAX_RESULT_ROWS = 200

#How many times to ask the LLM to fix broken SQL before giving up.
MAX_SQL_RETRIES = 2

_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)
_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*([\s\S]*?)```", re.IGNORECASE)

_QUESTION_START_RE = re.compile(
    r"^(what|which|who|how|when|where|show|list|find|get|give|tell|compare|"
    r"calculate|top|average|total|does|is|are|do|did|can|will|would|has|have)",
    re.IGNORECASE,
)

def _normalize_question(q: str) -> str:
    """Ensure every query ends with ? so gpt-4o-mini treats it as a question, not a CANNOT_ANSWER."""
    q = q.strip()
    if not q.endswith("?"):
        q = q + "?"
    return q

#Questions about future events or predictions can't be answered with historical data
_FUTURE_RE = re.compile(
    r"\b(will\s+\w+|predict|forecast|next\s+(week|month|year|quarter)|"
    r"future\s+(price|revenue|stock|performance)|going\s+to\s+be|tomorrow['']?s)\b",
    re.IGNORECASE,
)

_SQL_SYSTEM_PROMPT = """\
You are a SQL expert for a financial database called AskSQL Markets.
Your job is to convert a natural language question into a single valid SQLite SELECT query.

SCHEMA CONTEXT (relevant tables for this question):
{schema_context}

RULES:
1. Return ONLY the raw SQL query — no explanation, no markdown fences, no comments.
2. Only SELECT statements are allowed. Never write INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE.
3. Always include LIMIT 100 unless the query is a single-row aggregation.
4. Use the exact table and column names from the schema above.
5. revenue and net_income are stored in raw dollars — divide by 1e9 to get billions.
   eps is already in USD per share — do NOT divide by 1e9.
   profit_margin is a decimal (0.25 = 25%) — do NOT multiply by 100.
6. This is SQLite — use SQLite date functions, NOT PostgreSQL syntax:
   - CORRECT:   date('now', '-2 years')  or  date('now', '-1 month')
   - INCORRECT: DATE 'now' - INTERVAL '2 year'  (this is PostgreSQL, will fail)
7. Short phrases without question marks are valid queries — treat them as implicit data requests.
   - "Apple dividend history" → show Apple's dividend history
   - "Tesla revenue" → show Tesla's revenue from financials
   - "Microsoft stock price" → show Microsoft's recent prices
   Do NOT return CANNOT_ANSWER for terse phrases about data that exists in the database.
8. If the question cannot be answered with the available data, return exactly: CANNOT_ANSWER
   Examples that require CANNOT_ANSWER:
   - "What will Apple's stock price be next week?" → future prediction, no future data exists
   - "Which company will have the highest revenue in 2026?" → future prediction
   - "What is the sentiment on Tesla stock?" → no sentiment data in the database
   - "Compare Apple to Samsung" → Samsung is not an S&P 500 company in the database
9. Common column name mistakes to avoid:
   - financials year column: use f.year  — NEVER f.fiscal_year (that column does not exist)
   - sector filter: use c.sector = 'Technology'  — NEVER 'tech' or 'technology' (case-sensitive)
   - volume column: use p.volume from the prices table  — NEVER f.volume (financials has no volume column)
   - profit margin: use f.profit_margin from financials  — NEVER c.profit_margin (companies has no profit_margin column)
   - closing price: the column is p.close  — NEVER p.closing_price (that column does not exist)
   - "S&P 500 companies" means all rows — do NOT filter by sector = 'S&P 500' (not a valid sector value)
10. Company name matching: company names include suffixes like "Inc.", "Corp.", "Ltd." — NEVER use exact match.
   - CORRECT:   c.ticker = 'TSLA'  or  c.company_name LIKE '%Tesla%'
   - INCORRECT: c.company_name = 'Tesla'  (will return zero rows)
   Prefer filtering by ticker when the ticker is obvious from context (TSLA, AAPL, MSFT, AMZN, GOOGL, META, NVDA, etc.)
11. Year filtering: when a specific year like "2023" is mentioned, use BETWEEN — NEVER use date('now', ...) which always refers to the current date (2026).
    - CORRECT for prices:     p.date BETWEEN '2023-01-01' AND '2023-12-31'
    - CORRECT for financials: f.year = 2023
    - INCORRECT: p.date >= date('now', 'start of year')  (this is the current year, not 2023)
"""

_EXPLAIN_SYSTEM_PROMPT = """\
You are AskSQL Markets, a financial data assistant with expertise in S&P 500 companies.
Given a user question, the SQL that was run, and the results, write a clear and insightful answer.

Guidelines:
- Lead with the direct answer to the question (the key finding).
- Highlight standout values — the highest, lowest, or most surprising result.
- When amounts are large, express them naturally (e.g. "$2.4 trillion", not "$2400000000000").
- Keep it to 2-4 sentences. Be specific — name companies, sectors, or figures when relevant.
- Do not mention SQL, databases, or technical details. Write for a non-technical reader.
- If results are empty, say clearly that no data matched the criteria.
"""


def ask(question: str, engine: Engine) -> dict[str, Any]:
    """
    Convert a natural language question to SQL, execute it, and explain the results.
    Logs every attempt to query_history.
    """
    llm, _ = get_llm_and_embeddings()
    question = _normalize_question(question)
    schema_context = get_schema_context(question)

    generated_sql: str | None = None
    success = False
    error_msg: str | None = None
    columns: list[str] = []
    results: list[list] = []
    explanation = ""

    try:
        #Pre-check: reject future/prediction questions immediately
        if _FUTURE_RE.search(question):
            explanation = "This database only contains historical data and can't answer questions about future prices, revenue, or predictions."
            success = True
            _log_query(engine, question, None, True, None)
            return {
                "sql": None,
                "columns": [],
                "results": [],
                "explanation": explanation,
                "success": True,
                "error": None,
            }

        #---Step 1: Generate SQL---
        sql_messages = [
            SystemMessage(content=_SQL_SYSTEM_PROMPT.format(schema_context=schema_context)),
            HumanMessage(content=question),
        ]
        sql_response = llm.invoke(sql_messages)
        raw_sql = sql_response.content.strip()

        #Strip markdown fences if the model added them despite instructions
        fence_match = _SQL_FENCE_RE.search(raw_sql)
        if fence_match:
            raw_sql = fence_match.group(1).strip()

        if raw_sql == "CANNOT_ANSWER":
            explanation = "I don't have the data needed to answer that question."
            success = True
        elif _FORBIDDEN_RE.search(raw_sql):
            error_msg = "Generated SQL contains forbidden keywords."
            explanation = "I can only run SELECT queries. That question would require modifying the database."
        else:
            generated_sql = raw_sql

            #---Step 2: Execute SQL (with retry on failure)---
            sql_messages_so_far = sql_messages + [AIMessage(content=generated_sql)]
            last_exc: Exception | None = None

            for attempt in range(MAX_SQL_RETRIES + 1):
                try:
                    with engine.connect() as conn:
                        result_proxy = conn.execute(text(generated_sql))
                        columns = list(result_proxy.keys())
                        raw_rows = result_proxy.fetchall()

                    #Cap rows so cartesian-product queries don't flood the UI
                    truncated = len(raw_rows) > MAX_RESULT_ROWS
                    results = [list(row) for row in raw_rows[:MAX_RESULT_ROWS]]
                    if truncated:
                        # Append a sentinel row the UI can detect and display as a notice
                        results.append([f"… results capped at {MAX_RESULT_ROWS} rows"] + [""] * (len(columns) - 1))

                    last_exc = None
                    break  #success - exit retry loop

                except Exception as exc:
                    last_exc = exc
                    if attempt < MAX_SQL_RETRIES:
                        #Feed the error back and ask the LLM to fix the SQL
                        sql_messages_so_far = sql_messages_so_far + [
                            HumanMessage(
                                content=(
                                    f"That SQL failed with this error:\n{exc}\n\n"
                                    "Fix the SQL and return only the corrected query — "
                                    "no explanation, no markdown fences."
                                )
                            )
                        ]
                        fix_response = llm.invoke(sql_messages_so_far)
                        fixed_sql = fix_response.content.strip()
                        fence_match = _SQL_FENCE_RE.search(fixed_sql)
                        if fence_match:
                            fixed_sql = fence_match.group(1).strip()
                        generated_sql = fixed_sql
                        sql_messages_so_far = sql_messages_so_far + [AIMessage(content=generated_sql)]

            if last_exc is not None:
                raise last_exc

            #---Step 3: Explain results---
            results_preview = _format_results_for_prompt(columns, results)
            explain_messages = [
                SystemMessage(content=_EXPLAIN_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Question: {question}\n\n"
                        f"SQL used:\n{generated_sql}\n\n"
                        f"Results:\n{results_preview}"
                    )
                ),
            ]
            explain_response = llm.invoke(explain_messages)
            explanation = explain_response.content.strip()
            success = True

    except Exception as exc:
        error_msg = str(exc)
        explanation = f"Something went wrong while answering your question: {error_msg}"

    _log_query(engine, question, generated_sql, success, error_msg)

    return {
        "sql": generated_sql,
        "columns": columns,
        "results": results,
        "explanation": explanation,
        "success": success,
        "error": error_msg,
    }


def _log_query(
    engine: Engine,
    question: str,
    generated_sql: str | None,
    success: bool,
    error_msg: str | None,
) -> None:
    from data.models import QueryHistory
    try:
        with Session(engine) as session:
            session.add(
                QueryHistory(
                    question=question,
                    generated_sql=generated_sql,
                    success=success,
                    error_msg=error_msg,
                    created_at=datetime.now(tz=timezone.utc),
                )
            )
            session.commit()
    except Exception:
        pass


def _format_results_for_prompt(columns: list[str], results: list[list], max_rows: int = 20) -> str:
    if not results:
        return "No rows returned."
    header = " | ".join(columns)
    divider = "-" * len(header)
    rows = [" | ".join(str(v) for v in row) for row in results[:max_rows]]
    suffix = f"\n... ({len(results) - max_rows} more rows)" if len(results) > max_rows else ""
    return f"{header}\n{divider}\n" + "\n".join(rows) + suffix
