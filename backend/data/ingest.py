import math
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import Company, Dividend, Financial, Price

_failures: dict[str, list[str]] = {}


def log_failure(ticker: str, stage: str, reason: str) -> None:
    _failures.setdefault(ticker, []).append(f"{stage}: {reason}")


def get_failures() -> dict[str, list[str]]:
    return _failures


def fetch_company_metadata(ticker: str, yf_ticker: yf.Ticker) -> dict:
    result: dict = {}
    try:
        info = yf_ticker.get_info()
        if not info:
            return result
        result["company_name"] = info.get("longName") or info.get("shortName")
        result["sector"] = info.get("sector")
        result["industry"] = info.get("industry")
        parts = [p for p in [info.get("city"), info.get("state"), info.get("country")] if p]
        result["headquarters"] = ", ".join(parts) if parts else None
    except Exception as e:
        log_failure(ticker, "metadata", str(e))
    return result


def fetch_price_history(ticker: str, yf_ticker: yf.Ticker) -> Optional[pd.DataFrame]:
    try:
        df = yf_ticker.history(period="5y", interval="1d", auto_adjust=True, actions=False)
        if df is None or df.empty:
            return None
        df.index = df.index.date
        return df
    except Exception as e:
        log_failure(ticker, "prices", str(e))
        return None


def fetch_financials(ticker: str, yf_ticker: yf.Ticker) -> list[dict]:
    records = []
    try:
        stmt = yf_ticker.get_income_stmt(freq="yearly")
        if stmt is None or stmt.empty:
            return records
        for col in stmt.columns:
            year = col.year
            revenue = _safe_get(stmt, "TotalRevenue", col)
            net_income = _safe_get(stmt, "NetIncome", col)
            eps = _safe_get(stmt, "BasicEPS", col) or _safe_get(stmt, "DilutedEPS", col)

            if revenue is None and net_income is None:
                continue

            profit_margin = None
            if revenue is not None and net_income is not None and revenue != 0:
                profit_margin = net_income / revenue

            records.append(
                {
                    "year": year,
                    "revenue": revenue,
                    "net_income": net_income,
                    "eps": eps,
                    "profit_margin": profit_margin,
                }
            )
    except Exception as e:
        log_failure(ticker, "financials", str(e))
    return records


def fetch_dividends(ticker: str, yf_ticker: yf.Ticker) -> Optional[pd.Series]:
    try:
        divs = yf_ticker.get_dividends(period="max")
        if divs is None or len(divs) == 0:
            return None
        #yfinance may return a DataFrame or a Series depending on version
        if isinstance(divs, pd.DataFrame):
            divs = divs["Dividends"]
        return divs
    except Exception as e:
        log_failure(ticker, "dividends", str(e))
        return None


def upsert_company(ticker: str, wiki_row: dict, meta: dict, engine: Engine) -> None:
    with Session(engine) as session:
        company = session.get(Company, ticker)
        if company is None:
            company = Company(ticker=ticker)
        company.company_name = meta.get("company_name") or wiki_row.get("company_name")
        company.sector = meta.get("sector") or wiki_row.get("sector")
        company.industry = meta.get("industry") or wiki_row.get("industry")
        company.headquarters = meta.get("headquarters") or wiki_row.get("headquarters")
        session.merge(company)
        session.commit()


def bulk_insert_prices(ticker: str, df: pd.DataFrame, engine: Engine) -> None:
    rows = []
    for date, row in df.iterrows():
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "open": _clean_float(row.get("Open")),
                "close": _clean_float(row.get("Close")),
                "high": _clean_float(row.get("High")),
                "low": _clean_float(row.get("Low")),
                "volume": _clean_int(row.get("Volume")),
            }
        )
    if not rows:
        return
    with Session(engine) as session:
        stmt = sqlite_insert(Price).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "date"])
        session.execute(stmt)
        session.commit()


def bulk_insert_financials(ticker: str, records: list[dict], engine: Engine) -> None:
    rows = [{"ticker": ticker, **r} for r in records]
    with Session(engine) as session:
        stmt = sqlite_insert(Financial).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "year"])
        session.execute(stmt)
        session.commit()


def bulk_insert_dividends(ticker: str, series: pd.Series, engine: Engine) -> None:
    rows = []
    for ts, amount in series.items():
        date = ts.date() if hasattr(ts, "date") else ts
        val = _clean_float(amount)
        if val is None:
            continue
        rows.append({"ticker": ticker, "date": date, "dividend_amount": val})
    if not rows:
        return
    with Session(engine) as session:
        stmt = sqlite_insert(Dividend).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "date"])
        session.execute(stmt)
        session.commit()


def _safe_get(df: pd.DataFrame, row_label: str, col) -> Optional[float]:
    try:
        val = df.loc[row_label, col]
        if pd.isna(val):
            return None
        return float(val)
    except (KeyError, TypeError, ValueError):
        return None


def _clean_float(val) -> Optional[float]:
    try:
        if val is None:
            return None
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _clean_int(val) -> Optional[int]:
    try:
        if val is None:
            return None
        f = float(val)
        return None if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return None
