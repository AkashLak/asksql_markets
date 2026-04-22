"""
AskSQL Markets - FastAPI backend

Endpoints:
  POST /ask        - natural language → SQL + results + explanation
  GET  /health     - DB connection check + row counts + active LLM provider
  GET  /schema     - schema context string used by the agent
  POST /admin/sync - re-download latest markets.db from GitHub Releases
"""

import asyncio
import gzip
import os
import urllib.request
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

GITHUB_REPO = os.getenv("GITHUB_REPO", "")   # e.g. "AkashLak/asksql_markets"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "") # only needed for private repos
SYNC_SECRET = os.getenv("SYNC_SECRET", "")

_DB_PATH = Path(__file__).parent.parent / "data" / "markets.db"

engine = None


def _download_db() -> None:
    """Download markets.db.gz from GitHub Releases and decompress to _DB_PATH."""
    if not GITHUB_REPO:
        raise RuntimeError("GITHUB_REPO env var is not set — cannot download DB.")

    url = f"https://github.com/{GITHUB_REPO}/releases/download/db-latest/markets.db.gz"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

    temp_gz = _DB_PATH.with_suffix(".db.gz.tmp")
    temp_db = _DB_PATH.with_suffix(".db.tmp")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            temp_gz.write_bytes(resp.read())
        with gzip.open(temp_gz, "rb") as gz_in, open(temp_db, "wb") as db_out:
            db_out.write(gz_in.read())
        os.replace(temp_db, _DB_PATH)  # atomic on POSIX
    finally:
        temp_gz.unlink(missing_ok=True)
        if temp_db.exists():
            temp_db.unlink(missing_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine

    if not _DB_PATH.exists():
        try:
            await asyncio.get_event_loop().run_in_executor(None, _download_db)
        except Exception as exc:
            # db-latest release may not exist yet (first deploy before seed).
            # Start anyway — /health will show 0 rows; /admin/sync recovers it.
            print(f"Warning: could not download DB on startup ({exc}). Starting without data.")

    engine = get_engine(db_path=_DB_PATH)
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
    """Re-download latest markets.db from GitHub Releases. Called by GitHub Actions after daily_refresh."""
    if SYNC_SECRET and x_sync_secret != SYNC_SECRET:
        raise HTTPException(status_code=403, detail="Invalid sync secret.")
    await asyncio.get_event_loop().run_in_executor(None, _download_db)
    global engine
    if engine:
        engine.dispose()
    engine = get_engine(db_path=_DB_PATH)
    return {"status": "ok", "message": "Downloaded latest DB from GitHub Releases."}
