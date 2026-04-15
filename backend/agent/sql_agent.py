"""
LangChain SQL agent — the core of AskSQL Markets.

ask(question, engine) → dict with keys:
  sql         — the generated SQL query
  columns     — list of column names
  results     — list of rows (each row is a list)
  explanation — natural language answer
  success     — bool

The agent:
1. Retrieves relevant schema context from Chroma (RAG)
2. Sends question + schema context to the LLM
3. LLM generates SQL via LangChain's SQL agent toolkit
4. Result is executed and returned
5. Everything is logged to query_history
"""

import re
from datetime import datetime, timezone
from typing import Any

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .llm_factory import get_llm_and_embeddings, get_provider_name
from .schema_store import get_schema_context

# Matches a bare SQL block (with or without markdown fences)
_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE)\b",
    re.IGNORECASE,
)

_SYSTEM_PROMPT_TEMPLATE = """\
You are AskSQL Markets, an AI assistant that answers questions about S&P 500 \
financial data by writing and executing SQLite SQL queries.

RELEVANT SCHEMA CONTEXT (retrieved for this question):
{schema_context}

RULES — follow them exactly:
1. Only write SELECT statements. Never INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE.
2. Always add LIMIT 100 unless the user asks for more or the query is an aggregation \
   returning a single row.
3. Use the exact table and column names from the schema above.
4. Revenue and net_income are in raw dollars — when displaying to users, divide by 1e9 \
   and label as "billions".
5. profit_margin is a decimal (0.25 = 25%) — when displaying, multiply by 100.
6. If you cannot answer with the available data, say so clearly instead of guessing.
7. After showing results, always provide a concise natural language explanation.
"""


def ask(question: str, engine: Engine) -> dict[str, Any]:
    """
    Ask a natural language question and return SQL + results + explanation.
    Logs the query to query_history regardless of success/failure.
    """
    from data.models import QueryHistory

    llm, _ = get_llm_and_embeddings()
    schema_context = get_schema_context(question)
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(schema_context=schema_context)

    db = SQLDatabase(engine, include_tables=["companies", "prices", "financials", "dividends"])

    agent = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="openai-tools" if get_provider_name() == "openai" else "zero-shot-react-description",
        system_message=system_prompt,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=10,
    )

    generated_sql: str | None = None
    success = False
    error_msg: str | None = None
    columns: list[str] = []
    results: list[list] = []
    explanation = ""

    try:
        response = agent.invoke({"input": question})
        raw_output: str = response.get("output", "")

        # Extract SQL from agent's intermediate steps if available
        for step in response.get("intermediate_steps", []):
            action, _ = step if isinstance(step, tuple) else (step, None)
            tool_input = getattr(action, "tool_input", None)
            if tool_input and _is_select(str(tool_input)):
                generated_sql = str(tool_input).strip()
                break

        # Execute the extracted SQL to get structured results
        if generated_sql:
            with engine.connect() as conn:
                from sqlalchemy import text
                result_proxy = conn.execute(text(generated_sql))
                columns = list(result_proxy.keys())
                results = [list(row) for row in result_proxy.fetchall()]

        explanation = raw_output
        success = True

    except Exception as exc:
        error_msg = str(exc)
        explanation = f"I was unable to answer that question. Error: {error_msg}"

    # Log to query_history
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
        pass  # never let logging failures surface to the caller

    return {
        "sql": generated_sql,
        "columns": columns,
        "results": results,
        "explanation": explanation,
        "success": success,
        "error": error_msg,
    }


def _is_select(sql: str) -> bool:
    stripped = sql.strip()
    return stripped.upper().startswith("SELECT") and not _FORBIDDEN_RE.search(stripped)
