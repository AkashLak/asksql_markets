"""
AskSQL Markets - FastAPI backend

Endpoints:
  POST /ask        - natural language → SQL + results + explanation
  GET  /health     - DB connection check + row counts + active LLM provider
  GET  /schema     - schema context string used by the agent
  POST /admin/sync - (production) pull latest data from Turso into local replica
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

load_dotenv()

from data.models import Base, get_engine
from agent.llm_factory import get_provider_name
from agent.schema_store import get_schema_context
from agent.sql_agent import ask

TURSO_URL = os.getenv("TURSO_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
# Optional: set SYNC_SECRET on Render + GitHub to protect /admin/sync
SYNC_SECRET = os.getenv("SYNC_SECRET", "")

_REPLICA_PATH = Path(__file__).parent.parent / "data" / "markets_replica.db"

_turso_conn = None
engine = None


async def _do_sync() -> None:
    """Pull latest data from Turso into the local embedded replica."""
    if _turso_conn is not None:
        await asyncio.get_event_loop().run_in_executor(None, _turso_conn.sync)


async def _periodic_sync(interval_seconds: int = 21_600) -> None:
    """Re-sync from Turso every 6 hours so fresh data becomes visible without a restart."""
    while True:
        await asyncio.sleep(interval_seconds)
        await _do_sync()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _turso_conn, engine

    if TURSO_URL and TURSO_AUTH_TOKEN:
        import libsql_experimental as libsql

        # Create a local embedded replica that mirrors Turso.
        # SQLAlchemy reads from the local file (fast); libsql keeps it in sync.
        _turso_conn = libsql.connect(
            str(_REPLICA_PATH),
            sync_url=TURSO_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
        _turso_conn.sync()
        engine = get_engine(db_path=_REPLICA_PATH)
        asyncio.create_task(_periodic_sync())
    else:
        engine = get_engine()

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


#--- Request/Response models ---

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    sql: str | None
    columns: list[str]
    results: list[list]
    explanation: str
    success: bool
    error: str | None = None


#--- Endpoints ---

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


@app.post("/admin/sync")
async def admin_sync(x_sync_secret: str = Header(default="")):
    """Pull latest data from Turso into the local replica. Called by GitHub Actions after daily_refresh."""
    if SYNC_SECRET and x_sync_secret != SYNC_SECRET:
        raise HTTPException(status_code=403, detail="Invalid sync secret.")
    if _turso_conn is None:
        return {"status": "skipped", "reason": "Turso not configured — using local SQLite"}
    await _do_sync()
    return {"status": "ok", "message": "Synced from Turso."}
