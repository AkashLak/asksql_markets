"""
AskSQL Markets — Evaluation suite.

25 test cases covering all tables, query types, and edge cases.
Each case defines what the agent's response must satisfy to pass.

Scoring per case:
  PASS    — SQL ran, all structural checks pass
  PARTIAL — SQL ran but columns/rows/value check failed
  FAIL    — SQL error, forbidden keyword, or wrong CANNOT_ANSWER behaviour
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class EvalCase:
    id: int
    category: str
    question: str
    # If False, agent must return CANNOT_ANSWER (no SQL, success=True, sql=None)
    should_answer: bool
    # SQL must reference all of these table names (case-insensitive substring match)
    expected_tables: list[str] = field(default_factory=list)
    # Result columns must include all of these (case-insensitive)
    expected_columns: list[str] = field(default_factory=list)
    # Acceptable row count range for data rows (ignoring cap sentinel)
    min_rows: int = 1
    max_rows: int = 500
    # Optional: receives (columns, results) → bool for value-level checks
    value_check: Optional[Callable] = None
    notes: str = ""


def _col_index(columns: list[str], name: str) -> int:
    """
    Flexible column lookup — tries exact match first, then substring.
    Handles model aliases like 'avg_eps_billions' when looking for 'avg',
    or 'num_companies' when looking for 'count'.
    """
    name_lower = name.lower()
    # 1. Exact match
    for i, c in enumerate(columns):
        if c.lower() == name_lower:
            return i
    # 2. Substring: expected name is contained in column name (e.g. "avg" in "avg_revenue")
    for i, c in enumerate(columns):
        if name_lower in c.lower():
            return i
    # 3. Reverse substring: column name is contained in expected name
    for i, c in enumerate(columns):
        if c.lower() in name_lower:
            return i
    return -1


def _get(columns: list[str], results: list[list], col: str, row: int = 0):
    i = _col_index(columns, col)
    if i == -1 or row >= len(results):
        return None
    return results[row][i]


EVAL_SUITE: list[EvalCase] = [

    # ── Single table: companies ───────────────────────────────────────────────

    EvalCase(
        id=1,
        category="companies",
        question="How many companies are in the S&P 500 database?",
        should_answer=True,
        expected_tables=["companies"],
        expected_columns=["count"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: 490 <= float(_get(cols, rows, "count") or 0) <= 510,
        notes="Expect ~503",
    ),
    EvalCase(
        id=2,
        category="companies",
        question="How many companies are in each sector?",
        should_answer=True,
        expected_tables=["companies"],
        expected_columns=["sector"],
        min_rows=8, max_rows=20,
        notes="Should GROUP BY sector",
    ),
    EvalCase(
        id=3,
        category="companies",
        question="Which company has the ticker AAPL?",
        should_answer=True,
        expected_tables=["companies"],
        expected_columns=["company_name"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: "apple" in str(_get(cols, rows, "company_name") or "").lower(),
        notes="Should return Apple Inc.",
    ),

    # ── Single table: prices ──────────────────────────────────────────────────

    EvalCase(
        id=4,
        category="prices",
        question="What are the top 5 stocks by closing price today?",
        should_answer=True,
        expected_tables=["prices"],
        expected_columns=["ticker", "close"],
        min_rows=5, max_rows=5,
        notes="Should use MAX(date) and LIMIT 5",
    ),
    EvalCase(
        id=5,
        category="prices",
        question="What was Apple's closing price on the most recent trading day?",
        should_answer=True,
        expected_tables=["prices"],
        expected_columns=["close"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "close") or 0) > 50,
        notes="Should filter ticker=AAPL and use MAX(date)",
    ),
    EvalCase(
        id=6,
        category="prices",
        question="What was the average daily trading volume for Tesla in 2023?",
        should_answer=True,
        expected_tables=["prices"],
        expected_columns=["avg"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "avg") or 0) > 1_000_000,
        notes="AVG(volume) for TSLA in 2023, expect ~100M+",
    ),
    EvalCase(
        id=7,
        category="prices",
        question="How many distinct trading dates exist in the prices table?",
        should_answer=True,
        expected_tables=["prices"],
        expected_columns=["count"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: 1000 <= float(_get(cols, rows, "count") or 0) <= 5000,
        notes="COUNT(DISTINCT date), expect ~1255 — 'distinct' keyword forces correct aggregation",
    ),

    # ── Single table: financials ──────────────────────────────────────────────

    EvalCase(
        id=8,
        category="financials",
        question="Which company had the highest revenue in 2024?",
        should_answer=True,
        expected_tables=["financials"],
        expected_columns=["ticker"],
        min_rows=1, max_rows=5,
        notes="ORDER BY revenue DESC LIMIT 1",
    ),
    EvalCase(
        id=9,
        category="financials",
        question="What was Microsoft's profit margin in 2023?",
        should_answer=True,
        expected_tables=["financials"],
        expected_columns=["profit_margin"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: 0.1 < float(_get(cols, rows, "profit_margin") or 0) < 0.9,
        notes="Filter ticker=MSFT, year=2023",
    ),
    EvalCase(
        id=10,
        category="financials",
        question="How many companies reported a net loss in 2023?",
        should_answer=True,
        expected_tables=["financials"],
        expected_columns=["count"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "count") or 0) > 0,
        notes="WHERE net_income < 0 AND year=2023",
    ),
    EvalCase(
        id=11,
        category="financials",
        question="What is the average EPS for technology companies in 2024?",
        should_answer=True,
        expected_tables=["financials", "companies"],
        expected_columns=["avg"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "avg") or 0) > 0,
        notes="JOIN companies, sector=Technology, year=2024 — tests fiscal_year fix",
    ),

    # ── Single table: dividends ───────────────────────────────────────────────

    EvalCase(
        id=12,
        category="dividends",
        question="Show the 10 most recent dividend payments for Apple",
        should_answer=True,
        expected_tables=["dividends"],
        expected_columns=["date", "dividend_amount"],
        min_rows=10, max_rows=10,
        notes="Filter AAPL, ORDER BY date DESC LIMIT 10",
    ),
    EvalCase(
        id=13,
        category="dividends",
        question="How many distinct companies paid dividends in 2023?",
        should_answer=True,
        expected_tables=["dividends"],
        expected_columns=["count"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "count") or 0) > 100,
        notes="COUNT(DISTINCT ticker) with date filter",
    ),
    EvalCase(
        id=14,
        category="dividends",
        question="What is the total dividend amount paid by Apple across all time?",
        should_answer=True,
        expected_tables=["dividends"],
        expected_columns=["total"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "total") or 0) > 1,
        notes="SUM(dividend_amount) for AAPL",
    ),

    # ── Multi-table JOINs ─────────────────────────────────────────────────────

    EvalCase(
        id=15,
        category="join",
        question="Which sector has the highest average revenue in 2024?",
        should_answer=True,
        expected_tables=["financials", "companies"],
        expected_columns=["sector"],
        min_rows=1, max_rows=20,
        notes="JOIN + GROUP BY sector + ORDER BY avg revenue",
    ),
    EvalCase(
        id=16,
        category="join",
        question="Which companies had a profit margin above 30% in 2023?",
        should_answer=True,
        expected_tables=["financials", "companies"],
        expected_columns=["company_name", "profit_margin"],
        min_rows=5, max_rows=100,
        notes="JOIN + WHERE profit_margin > 0.30",
    ),
    EvalCase(
        id=17,
        category="join",
        question="What are the top 5 Technology companies by revenue in 2024?",
        should_answer=True,
        expected_tables=["financials", "companies"],
        expected_columns=["company_name"],
        min_rows=5, max_rows=5,
        notes="JOIN + WHERE sector=Technology + ORDER BY revenue DESC LIMIT 5",
    ),
    EvalCase(
        id=18,
        category="join",
        question="What is the average closing price for Healthcare stocks on the most recent trading day?",
        should_answer=True,
        expected_tables=["prices", "companies"],
        expected_columns=["avg"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "avg") or 0) > 0,
        notes="JOIN + WHERE sector='Health Care' + MAX(date)",
    ),
    EvalCase(
        id=19,
        category="join",
        question="How many companies in each sector paid dividends in 2023?",
        should_answer=True,
        expected_tables=["dividends", "companies"],
        expected_columns=["sector", "count"],
        min_rows=5, max_rows=20,
        notes="JOIN dividends + companies + GROUP BY sector + date filter",
    ),
    EvalCase(
        id=20,
        category="join",
        question="Which Technology companies had positive EPS in 2024?",
        should_answer=True,
        expected_tables=["financials", "companies"],
        expected_columns=["company_name"],
        min_rows=1, max_rows=100,
        notes="JOIN + WHERE sector=Technology + eps > 0 + year=2024",
    ),
    EvalCase(
        id=21,
        category="join",
        question="List the 10 companies with the highest trading volume on the most recent trading day",
        should_answer=True,
        expected_tables=["prices", "companies"],
        expected_columns=["company_name", "volume"],
        min_rows=10, max_rows=10,
        notes="JOIN prices + companies + MAX(date) + ORDER BY volume DESC LIMIT 10",
    ),

    # ── Aggregation / complex ─────────────────────────────────────────────────

    EvalCase(
        id=22,
        category="aggregation",
        question="What is the total revenue across all S&P 500 companies in 2024?",
        should_answer=True,
        expected_tables=["financials"],
        expected_columns=["total"],
        min_rows=1, max_rows=1,
        value_check=lambda cols, rows: float(_get(cols, rows, "total") or 0) > 1000,
        notes="SUM(revenue)/1e9 for year=2024, expect ~17000 billion",
    ),
    EvalCase(
        id=23,
        category="aggregation",
        question="Which year had the highest average profit margin across all companies?",
        should_answer=True,
        expected_tables=["financials"],
        expected_columns=["year"],
        min_rows=1, max_rows=10,
        notes="GROUP BY year ORDER BY AVG(profit_margin) DESC",
    ),
    EvalCase(
        id=24,
        category="aggregation",
        question="What is the highest single-day closing price ever recorded in the database?",
        should_answer=True,
        expected_tables=["prices"],
        expected_columns=["close"],
        min_rows=1, max_rows=5,
        value_check=lambda cols, rows: float(_get(cols, rows, "close") or 0) > 1000,
        notes="MAX(close) — expect NVR ~7000+",
    ),

    # ── CANNOT_ANSWER ─────────────────────────────────────────────────────────

    EvalCase(
        id=25,
        category="cannot_answer",
        question="What will Apple's stock price be next week?",
        should_answer=False,
        notes="Future prediction — must return CANNOT_ANSWER",
    ),
]
