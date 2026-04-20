"""
AskSQL Markets — FastAPI backend.

Endpoints:
  POST /ask     — natural language → SQL + results + explanation
  GET  /health  — DB connection check + row counts + active LLM provider
  GET  /schema  — returns the full schema context string used by the agent
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

load_dotenv()

from data.models import Base, get_engine
from agent.llm_factory import get_provider_name
from agent.schema_store import get_schema_context
from agent.sql_agent import ask

engine = get_engine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create query_history table (and any other new tables) on startup
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="AskSQL Markets",
    description="Natural language querying over S&P 500 financial data.",
    version="0.1.0",
    lifespan=lifespan,
)

_frontend_url = os.getenv("FRONTEND_URL", "")
_origins = ["http://localhost:5173"]
if _frontend_url:
    _origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    sql: str | None
    columns: list[str]
    results: list[list]
    explanation: str
    success: bool
    error: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    result = ask(req.question, engine)
    return AskResponse(**result)


@app.get("/health")
def health():
    table_counts: dict[str, int] = {}
    try:
        with engine.connect() as conn:
            for tbl in ["companies", "prices", "financials", "dividends", "query_history"]:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()[0]
                table_counts[tbl] = count
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    return {
        "status": "ok",
        "provider": get_provider_name(),
        "tables": table_counts,
    }


@app.get("/schema")
def schema_endpoint(question: str = "general schema overview"):
    context = get_schema_context(question, k=10)
    return {"description": context}
