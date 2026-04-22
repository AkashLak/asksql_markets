"""
Incremental daily price + dividend refresh

Fetches the last 7 days of data from yfinance for every S&P 500 ticker
and upserts into Turso. Runs in ~3-5 minutes vs the full pipeline's 22 min.

Usage:
    cd backend
    python -m data.daily_refresh
"""

import math
import os
import time
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

TURSO_URL = os.getenv("TURSO_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

INTER_TICKER_DELAY = 0.5  # sec between tickers (lighter than full pipeline's 1.2s)
COMMIT_EVERY = 20         # batch commits to reduce round-trips

console = Console()


def main() -> None:
    if not TURSO_URL or not TURSO_AUTH_TOKEN:
        console.print("[red]Error:[/] TURSO_URL and TURSO_AUTH_TOKEN must be set in .env or environment.")
        raise SystemExit(1)

    import libsql_experimental as libsql

    conn = libsql.connect(TURSO_URL, auth_token=TURSO_AUTH_TOKEN)

    tickers = [
        row[0]
        for row in conn.execute("SELECT ticker FROM companies ORDER BY ticker").fetchall()
    ]
    if not tickers:
        console.print("[red]No tickers found in Turso. Run migrate_to_turso first.[/]")
        raise SystemExit(1)

    console.print(f"[bold blue]Daily refresh[/] — {len(tickers)} tickers\n")

    price_rows = 0
    div_rows = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        refresh_per_second=4,
    ) as progress:
        task = progress.add_task("Starting...", total=len(tickers))

        for i, ticker in enumerate(tickers):
            progress.update(task, description=f"[cyan]{ticker:<6}[/]")
            try:
                yf_t = yf.Ticker(ticker)

                # Prices: last 7 calendar days
                df = yf_t.history(period="7d", interval="1d", auto_adjust=True, actions=False)
                if df is not None and not df.empty:
                    for date_idx, row in df.iterrows():
                        d = date_idx.date() if hasattr(date_idx, "date") else date_idx
                        conn.execute(
                            "INSERT OR IGNORE INTO prices "
                            "(ticker, date, open, close, high, low, volume) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            [
                                ticker,
                                str(d),
                                _clean_float(row.get("Open")),
                                _clean_float(row.get("Close")),
                                _clean_float(row.get("High")),
                                _clean_float(row.get("Low")),
                                _clean_int(row.get("Volume")),
                            ],
                        )
                        price_rows += 1

                # Dividends paid in the last 7 days
                divs = yf_t.get_dividends()
                if divs is not None and len(divs) > 0:
                    if isinstance(divs, pd.DataFrame):
                        divs = divs["Dividends"]
                    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
                    for ts, amount in divs[divs.index >= cutoff].items():
                        d = ts.date() if hasattr(ts, "date") else ts
                        v = _clean_float(amount)
                        if v is not None:
                            conn.execute(
                                "INSERT OR IGNORE INTO dividends (ticker, date, dividend_amount) "
                                "VALUES (?, ?, ?)",
                                [ticker, str(d), v],
                            )
                            div_rows += 1

            except Exception as exc:
                errors += 1
                progress.console.print(f"  [yellow]  {ticker}:[/] {exc}")

            if (i + 1) % COMMIT_EVERY == 0:
                conn.commit()

            progress.advance(task)
            time.sleep(INTER_TICKER_DELAY)

    conn.commit()

    console.print(
        f"\n[bold green]Done![/]  "
        f"Prices +{price_rows} rows | "
        f"Dividends +{div_rows} rows | "
        f"Errors: {errors} tickers"
    )


def _clean_float(val) -> float | None:
    try:
        if val is None:
            return None
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _clean_int(val) -> int | None:
    try:
        if val is None:
            return None
        f = float(val)
        return None if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
