"""
Chroma-backed schema store for RAG-enhanced SQL generation

Stores embeddings of:
  - One document per table (columns, types, purpose, domain notes)
  - Example natural-language -> SQL pairs

At query time, the user's question is embedded and the top-k most
relevant documents are retrieved and injected into the agent prompt.
LLM can see the right schema context even as the
database grows.

Chroma index is persisted at backend/data/chroma_schema/ and rebuilt
automatically if it doesn't exist
"""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from .llm_factory import get_llm_and_embeddings

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_schema"

# ---
# Schema documents - one per table + example Q->SQL pairs
# ---

_SCHEMA_DOCS = [
    Document(
        page_content=(
            "Table: companies\n"
            "Purpose: Master list of S&P 500 companies. One row per company.\n"
            "Columns:\n"
            "  ticker       TEXT PRIMARY KEY  — stock ticker symbol (e.g. 'AAPL', 'MSFT')\n"
            "  company_name TEXT              — full company name (e.g. 'Apple Inc.')\n"
            "  sector       TEXT              — GICS sector (e.g. 'Technology', 'Health Care', 'Financials')\n"
            "  industry     TEXT              — GICS industry (e.g. 'Consumer Electronics')\n"
            "  headquarters TEXT              — city, state, country (e.g. 'Cupertino, CA, United States')\n"
            "Notes: Join to other tables on ticker. All 503 S&P 500 companies are present."
        ),
        metadata={"type": "schema", "table": "companies"},
    ),
    Document(
        page_content=(
            "Table: prices\n"
            "Purpose: Daily OHLCV (Open/High/Low/Close/Volume) stock prices. ~625k rows.\n"
            "Columns:\n"
            "  id     INTEGER PRIMARY KEY\n"
            "  ticker TEXT FK → companies.ticker\n"
            "  date   DATE    — trading date (format: YYYY-MM-DD), range: 2021-04-14 to present\n"
            "  open   REAL    — opening price in USD\n"
            "  close  REAL    — closing price in USD\n"
            "  high   REAL    — intraday high in USD\n"
            "  low    REAL    — intraday low in USD\n"
            "  volume INTEGER — shares traded that day\n"
            "Notes: ~1255 rows per ticker (5 years of trading days). Use date filtering for "
            "performance. Unique constraint on (ticker, date)."
        ),
        metadata={"type": "schema", "table": "prices"},
    ),
    Document(
        page_content=(
            "Table: financials\n"
            "Purpose: Annual income statement data per company. ~2000 rows.\n"
            "Columns:\n"
            "  id            INTEGER PRIMARY KEY\n"
            "  ticker        TEXT FK → companies.ticker\n"
            "  year          INTEGER — the column is named 'year', NOT 'fiscal_year' (e.g. 2022, 2023, 2024, 2025)\n"
            "  revenue       REAL    — total annual revenue in RAW DOLLARS (not millions/billions)\n"
            "  net_income    REAL    — net income in RAW DOLLARS\n"
            "  eps           REAL    — earnings per share in USD\n"
            "  profit_margin REAL    — net_income / revenue as a decimal (e.g. 0.25 = 25%)\n"
            "Notes: 4 years of data per ticker (2022-2025). Revenue is in raw dollars — divide by "
            "1e9 to get billions. Unique constraint on (ticker, year)."
        ),
        metadata={"type": "schema", "table": "financials"},
    ),
    Document(
        page_content=(
            "Table: dividends\n"
            "Purpose: Historical dividend payments per company. ~49k rows.\n"
            "Columns:\n"
            "  id              INTEGER PRIMARY KEY\n"
            "  ticker          TEXT FK → companies.ticker\n"
            "  date            DATE — ex-dividend date (YYYY-MM-DD), full history going back decades\n"
            "  dividend_amount REAL — dividend paid per share in USD\n"
            "Notes: Not all S&P 500 companies pay dividends (~426 of 503 do). "
            "Growth stocks like GOOG, AMZN, META have no rows. "
            "Unique constraint on (ticker, date)."
        ),
        metadata={"type": "schema", "table": "dividends"},
    ),
    Document(
        page_content=(
            "Table: query_history\n"
            "Purpose: Log of all natural-language questions asked through AskSQL Markets.\n"
            "Columns:\n"
            "  id            INTEGER PRIMARY KEY\n"
            "  question      TEXT    — the original natural language question\n"
            "  generated_sql TEXT    — the SQL query that was generated\n"
            "  success       BOOLEAN — whether the query executed without error\n"
            "  error_msg     TEXT    — error message if success=false, NULL otherwise\n"
            "  created_at    DATETIME — UTC timestamp of the query"
        ),
        metadata={"type": "schema", "table": "query_history"},
    ),
    Document(
        page_content=(
            "Example: 'Which sector has the highest average revenue in 2024?'\n"
            "SQL:\n"
            "SELECT c.sector, AVG(f.revenue) / 1e9 AS avg_revenue_billions\n"
            "FROM financials f\n"
            "JOIN companies c ON f.ticker = c.ticker\n"
            "WHERE f.year = 2024\n"
            "GROUP BY c.sector\n"
            "ORDER BY avg_revenue_billions DESC\n"
            "LIMIT 10;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'Which company had the highest revenue in 2024?'\n"
            "Note: 2024 is a HISTORICAL year — this is NOT a future prediction. Use f.year = 2024.\n"
            "SQL:\n"
            "SELECT c.company_name, c.ticker, f.revenue / 1e9 AS revenue_billions\n"
            "FROM financials f\n"
            "JOIN companies c ON f.ticker = c.ticker\n"
            "WHERE f.year = 2024\n"
            "ORDER BY f.revenue DESC\n"
            "LIMIT 1;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'What are the top 5 stocks by closing price today?'\n"
            "SQL:\n"
            "SELECT p.ticker, c.company_name, p.close\n"
            "FROM prices p\n"
            "JOIN companies c ON p.ticker = c.ticker\n"
            "WHERE p.date = (SELECT MAX(date) FROM prices)\n"
            "ORDER BY p.close DESC\n"
            "LIMIT 5;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'Show dividend history for Apple'\n"
            "SQL:\n"
            "SELECT d.date, d.dividend_amount\n"
            "FROM dividends d\n"
            "JOIN companies c ON d.ticker = c.ticker\n"
            "WHERE c.company_name LIKE '%Apple%' OR d.ticker = 'AAPL'\n"
            "ORDER BY d.date DESC\n"
            "LIMIT 20;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'Which companies had a profit margin above 30% in 2023?'\n"
            "SQL:\n"
            "SELECT c.company_name, c.sector, f.profit_margin\n"
            "FROM financials f\n"
            "JOIN companies c ON f.ticker = c.ticker\n"
            "WHERE f.year = 2023 AND f.profit_margin > 0.30\n"
            "ORDER BY f.profit_margin DESC\n"
            "LIMIT 100;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'What was the average daily volume for Tesla in 2023?'\n"
            "SQL:\n"
            "SELECT AVG(p.volume) AS avg_daily_volume\n"
            "FROM prices p\n"
            "WHERE p.ticker = 'TSLA'\n"
            "  AND p.date >= '2023-01-01'\n"
            "  AND p.date < '2024-01-01';"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'How many companies in each sector paid dividends in 2023?'\n"
            "SQL:\n"
            "SELECT c.sector, COUNT(DISTINCT d.ticker) AS count\n"
            "FROM dividends d\n"
            "JOIN companies c ON d.ticker = c.ticker\n"
            "WHERE d.date >= '2023-01-01' AND d.date < '2024-01-01'\n"
            "GROUP BY c.sector\n"
            "ORDER BY count DESC;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'What is the total dividend amount paid by a company across all time?'\n"
            "SQL:\n"
            "SELECT SUM(d.dividend_amount) AS total\n"
            "FROM dividends d\n"
            "WHERE d.ticker = 'AAPL';"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'List the 10 companies with the highest trading volume on the most recent trading day'\n"
            "SQL:\n"
            "SELECT p.ticker, c.company_name, p.volume\n"
            "FROM prices p\n"
            "JOIN companies c ON p.ticker = c.ticker\n"
            "WHERE p.date = (SELECT MAX(date) FROM prices)\n"
            "ORDER BY p.volume DESC\n"
            "LIMIT 10;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'What is the total revenue across all S&P 500 companies in 2024?'\n"
            "Note: 'S&P 500 companies' means ALL rows in financials — there is no sector called "
            "'S&P 500', so do NOT add a WHERE sector filter.\n"
            "SQL:\n"
            "SELECT SUM(f.revenue) / 1e9 AS total\n"
            "FROM financials f\n"
            "WHERE f.year = 2024;"
        ),
        metadata={"type": "example"},
    ),
    Document(
        page_content=(
            "Example: 'What will Apple's stock price be next week?'\n"
            "This question asks for a future prediction. The database only contains historical data — "
            "there are no future prices, forecasts, or predictions available.\n"
            "Return exactly: CANNOT_ANSWER"
        ),
        metadata={"type": "cannot_answer"},
    ),
    Document(
        page_content=(
            "Example: 'Which company will have the highest revenue in 2026?'\n"
            "This question asks about a future year. The financials table only contains data up to 2025 — "
            "future revenue cannot be predicted from historical records.\n"
            "Return exactly: CANNOT_ANSWER"
        ),
        metadata={"type": "cannot_answer"},
    ),
    Document(
        page_content=(
            "Example: 'What is the analyst sentiment on Tesla?' or 'Should I buy NVDA stock?'\n"
            "These questions require analyst ratings, sentiment data, or investment advice — "
            "none of which exist in this database. Only OHLCV prices, financials, and dividends are available.\n"
            "Return exactly: CANNOT_ANSWER"
        ),
        metadata={"type": "cannot_answer"},
    ),
]


def build_schema_store() -> Chroma:
    """Build and persist the Chroma index. Call once (or to rebuild)"""
    _, embeddings = get_llm_and_embeddings()
    store = Chroma.from_documents(
        documents=_SCHEMA_DOCS,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="schema",
    )
    print(f"Schema store built: {len(_SCHEMA_DOCS)} documents → {CHROMA_DIR}")
    return store


def load_schema_store() -> Chroma:
    """Load existing Chroma index, building it first if it doesn't exist"""
    _, embeddings = get_llm_and_embeddings()
    if not CHROMA_DIR.exists():
        return build_schema_store()
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="schema",
    )


def get_schema_context(question: str, k: int = 5) -> str:
    """
    Embed the question, retrieve top-k relevant schema docs, and return
    them as a formatted string ready to inject into a system prompt
    """
    store = load_schema_store()
    docs = store.similarity_search(question, k=k)
    return "\n\n---\n\n".join(doc.page_content for doc in docs)
