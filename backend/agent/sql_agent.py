"""
AskSQL Markets — NL-to-SQL agent.

Two-step pipeline that works reliably with both small local models (Ollama)
and cloud models (OpenAI):
  1. Generate SQL  — LLM receives schema context + question, returns only SQL
  2. Execute SQL   — run against SQLite, get structured results
  3. Explain       — LLM receives question + results, returns plain-English answer

This avoids the ReAct agent loop (Thought/Action/Observation format) which
requires larger models to follow reliably.
"""

import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .llm_factory import get_llm_and_embeddings
from .schema_store import get_schema_context

_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)
_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*([\s\S]*?)```", re.IGNORECASE)

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
5. Revenue and net_income are stored in raw dollars (divide by 1e9 for billions).
6. profit_margin is a decimal (0.25 = 25%).
7. This is SQLite — use SQLite date functions, NOT PostgreSQL syntax:
   - CORRECT:   date('now', '-2 years')  or  date('now', '-1 month')
   - INCORRECT: DATE 'now' - INTERVAL '2 year'  (this is PostgreSQL, will fail)
8. If the question cannot be answered with the available data, return exactly: CANNOT_ANSWER
"""

_EXPLAIN_SYSTEM_PROMPT = """\
You are AskSQL Markets, a helpful financial data assistant.
Given a user question, the SQL that was run, and the results returned, write a concise
natural language answer (2-4 sentences). Focus on the insight, not the mechanics.
Do not repeat the SQL. Use plain English suitable for a non-technical user.
"""


def ask(question: str, engine: Engine) -> dict[str, Any]:
    """
    Convert a natural language question to SQL, execute it, and explain the results.
    Logs every attempt to query_history.
    """
    from data.models import QueryHistory

    llm, _ = get_llm_and_embeddings()
    schema_context = get_schema_context(question)

    generated_sql: str | None = None
    success = False
    error_msg: str | None = None
    columns: list[str] = []
    results: list[list] = []
    explanation = ""

    try:
        # ── Step 1: Generate SQL ──────────────────────────────────────────────
        sql_messages = [
            SystemMessage(content=_SQL_SYSTEM_PROMPT.format(schema_context=schema_context)),
            HumanMessage(content=question),
        ]
        sql_response = llm.invoke(sql_messages)
        raw_sql = sql_response.content.strip()

        # Strip markdown fences if the model added them despite instructions
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

            # ── Step 2: Execute SQL ───────────────────────────────────────────
            with engine.connect() as conn:
                result_proxy = conn.execute(text(generated_sql))
                columns = list(result_proxy.keys())
                results = [list(row) for row in result_proxy.fetchall()]

            # ── Step 3: Explain results ───────────────────────────────────────
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

    # ── Log to query_history ──────────────────────────────────────────────────
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

    return {
        "sql": generated_sql,
        "columns": columns,
        "results": results,
        "explanation": explanation,
        "success": success,
        "error": error_msg,
    }


def _format_results_for_prompt(columns: list[str], results: list[list], max_rows: int = 20) -> str:
    if not results:
        return "No rows returned."
    header = " | ".join(columns)
    divider = "-" * len(header)
    rows = [" | ".join(str(v) for v in row) for row in results[:max_rows]]
    suffix = f"\n... ({len(results) - max_rows} more rows)" if len(results) > max_rows else ""
    return f"{header}\n{divider}\n" + "\n".join(rows) + suffix
