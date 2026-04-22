# AskSQL Markets

A natural-language-to-SQL interface over S&P 500 financial data. Ask questions in plain English and get a generated SQL query, real results, and a plain-English explanation powered by an LLM and a SQLite database of 503 companies.

**Live demo:** https://asksql-markets.vercel.app

---

## Screenshots

<img src="docs/landing.png" width="800" alt="AskSQL Landing"/>

![Query result](docs/results.png)

---

## What it does

Type a question like "Which technology companies had the highest profit margin in 2024?" and the app:

1. Retrieves relevant schema context via Chroma RAG
2. Generates a SQL query using an LLM (OpenAI or local Ollama)
3. Executes it against a SQLite database of S&P 500 data
4. Returns results, a bar/line chart, and a plain-English explanation

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Vite + Tailwind + Framer Motion |
| Backend | Python + FastAPI + LangChain + slowapi |
| Database | SQLite (503 companies, 625k+ price rows, 5 years of data) |
| LLM (local) | Ollama — llama3.2 + nomic-embed-text |
| LLM (cloud) | OpenAI — gpt-4o-mini + text-embedding-3-small |
| Vector store | Chroma (schema RAG) |
| Data refresh | GitHub Actions (daily, weekdays) |
| Deployment | Vercel (frontend) + Render (backend) |

---

## Project Structure

```
asksql_markets/
├── .env.example                     # Environment variable template
├── .github/
│   └── workflows/
│       └── daily_refresh.yml        # Scheduled daily data refresh
├── backend/
│   ├── agent/
│   │   ├── llm_factory.py           # Swaps between Ollama and OpenAI via env var
│   │   ├── schema_store.py          # Chroma RAG (embeds schema + Q->SQL examples)
│   │   └── sql_agent.py             # Core pipeline: generate SQL -> execute -> explain
│   ├── api/
│   │   └── main.py                  # FastAPI: /ask /health /schema /admin/sync
│   ├── data/
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── scraper.py               # Wikipedia S&P 500 scraper
│   │   ├── ingest.py                # yfinance data fetcher + bulk upserts
│   │   ├── run_pipeline.py          # CLI entry point for full data ingestion
│   │   └── daily_refresh.py        # Incremental refresh (last 7 days, prices + dividends)
│   ├── eval/
│   │   ├── suite.py                 # 25 test cases with structural checks
│   │   └── run_eval.py              # Eval runner with rich output + JSON results
│   ├── start.sh                     # Render startup script
│   ├── render.yaml                  # Render deployment config
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # State machine: idle -> loading -> done/error
│   │   ├── components/
│   │   │   ├── SearchBar.tsx        # Query input with example chips
│   │   │   ├── AnswerCard.tsx       # Explanation with number highlighting
│   │   │   ├── DataChart.tsx        # Auto bar/line chart via Recharts
│   │   │   ├── SqlDisplay.tsx       # Collapsible SQL block with copy button
│   │   │   └── ResultsTable.tsx     # Animated results table
│   │   ├── api.ts                   # Fetch wrapper (uses VITE_API_URL env var)
│   │   └── index.css                # Glass morphism, blob animations, grid overlay
│   ├── vercel.json
│   └── vite.config.ts               # Proxies /ask /health /schema -> :8000 in dev
└── README.md
```

---

## Database

SQLite at `backend/data/markets.db` (gitignored). Built by scraping Wikipedia for S&P 500 tickers and fetching data via yfinance.

| Table | Rows | Description |
|-------|------|-------------|
| `companies` | 503 | Ticker, name, sector, industry, headquarters |
| `prices` | ~625,000 | Daily OHLCV — 5 years of history |
| `financials` | ~2,000 | Annual revenue, net income, EPS, profit margin |
| `dividends` | ~49,000 | Full dividend history per ticker |
| `query_history` | — | Logs every question asked |

The database is distributed as a compressed release asset (`markets.db.gz`) on the `db-latest` GitHub Release tag. The backend downloads and decompresses it automatically on cold start.

---

## Agent Architecture

Fixed generate→execute→explain pipeline (not a ReAct loop — more reliable across model sizes):

```
Question
  -> Pre-check: regex guard rejects greetings/non-data queries immediately
  -> Chroma RAG (top-3 schema docs + Q->SQL examples)
  -> LLM: generate SQL
  -> SQLite execute (retry up to 2x on error, feeding error back to LLM)
  -> LLM: explain results in plain English
  -> Response
```

**Safety guards:**
- Forbidden keyword check blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, and other write operations
- `CANNOT_ANSWER` path handles questions outside scope (future predictions, non-S&P companies)
- Results capped at 200 rows with a UI warning to prevent cartesian-product floods
- Rate limiting via slowapi: 20 req/min on `/ask`, 5 req/min on `/admin/sync`
- Input validation: questions capped at 500 characters (Pydantic + HTML `maxLength`)

---

## Running Locally

### Prerequisites

```bash
# Install Ollama and pull models (one-time)
ollama pull llama3.2
ollama pull nomic-embed-text
```

### Backend

```bash
# Terminal 1
ollama serve

# Terminal 2
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build the database (first time only, ~22 min for all 503 tickers)
python -m data.run_pipeline

# Start the API
uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # dev server on :5173, proxies API calls to :8000
```

Open http://localhost:5173.

---

## LLM Provider

Controlled by `LLM_PROVIDER` in `.env` (copy `.env.example` to get started):

```bash
LLM_PROVIDER=ollama   # free, local (requires Ollama running)
LLM_PROVIDER=openai   # requires OPENAI_API_KEY, uses gpt-4o-mini
```

> **Note:** Switching providers requires rebuilding the Chroma vector index. Ollama (`nomic-embed-text`) produces 768-dim embeddings; OpenAI (`text-embedding-3-small`) produces 1536-dim. Mixing them causes a dimension mismatch error.

```bash
# 1. Update LLM_PROVIDER in .env
# 2. Delete the old Chroma index
rm -rf backend/data/chroma_schema
# 3. Rebuild
cd backend && source venv/bin/activate
python -c "from agent.schema_store import build_schema_store; build_schema_store()"
```

---

## Daily Data Refresh

A GitHub Actions workflow (`.github/workflows/daily_refresh.yml`) runs every weekday at 9 PM UTC (5 PM ET, after US market close):

1. Downloads the current `markets.db.gz` from the `db-latest` GitHub Release
2. Runs `daily_refresh.py` — fetches the last 7 days of prices + dividends from yfinance for all 503 tickers (~3–5 min)
3. Compresses and re-uploads the updated database to the `db-latest` release
4. Pings the Render backend's `/admin/sync` endpoint to hot-swap the live database

The workflow can also be triggered manually from the GitHub Actions UI.

---

## Eval Suite

25 test cases covering single-table queries, multi-table joins, aggregations, and edge cases:

| Provider | Pass | Usable | Avg latency |
|----------|------|--------|-------------|
| Ollama llama3.2 (local) | **84%** | **96%** | 5s |
| OpenAI gpt-4o-mini (production) | **84%** | **96%** | 3s |

```bash
cd backend && source venv/bin/activate

python -m eval.run_eval                    # run all 25 cases (~5 min)
python -m eval.run_eval --ids 1 5 11       # run specific cases
python -m eval.run_eval --category join    # run by category
```

Results saved to `eval/eval_results.json`.

---

## Deployment

- **Frontend** — Vercel (auto-deploys from `main`)
- **Backend** — Render free tier (Python 3.11, 512 MB RAM)
- **Database** — `markets.db.gz` stored in GitHub Releases (`db-latest` tag), downloaded at backend startup; refreshed daily via GitHub Actions

### Environment variables

**Render (backend):**

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | Set to `openai` |
| `OPENAI_API_KEY` | OpenAI API key |
| `GITHUB_REPO` | Repo name for DB download (e.g. `AkashLak/asksql_markets`) |
| `FRONTEND_URL` | Vercel URL (for CORS) |
| `SYNC_SECRET` | Shared secret protecting `/admin/sync` (optional) |
| `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` | Set to `python` — required for chromadb on Render |

**Vercel (frontend):**

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Render backend URL |

**GitHub Actions secrets:**

| Secret | Purpose |
|--------|---------|
| `RENDER_APP_URL` | Render backend URL (for post-refresh sync ping) |
| `SYNC_SECRET` | Must match the value set on Render |

> Render free tier spins down after 15 min of inactivity — first request after idle takes ~50s to wake up.
