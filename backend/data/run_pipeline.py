"""
Entry point for the AskSQL Markets data ingestion pipeline.

Usage:
    cd backend
    python -m data.run_pipeline              # full run
    python -m data.run_pipeline --retry-failed  # only retry previously failed tickers
"""

import argparse
import json
import time
from pathlib import Path
from textwrap import dedent

import yfinance as yf
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
from rich.table import Table
from sqlalchemy import text

from .ingest import (
    bulk_insert_dividends,
    bulk_insert_financials,
    bulk_insert_prices,
    fetch_company_metadata,
    fetch_dividends,
    fetch_financials,
    fetch_price_history,
    get_failures,
    log_failure,
    upsert_company,
)
from .models import Base, get_engine
from .scraper import scrape_sp500_wikipedia

INTER_TICKER_DELAY = 1.2       # seconds between each ticker
BATCH_COOLDOWN_EVERY = 50      # extra pause every N tickers
BATCH_COOLDOWN_SECS = 5.0
RATE_LIMIT_BACKOFF_BASE = 10   # seconds; doubles per retry
RATE_LIMIT_MAX_RETRIES = 3

FAILURES_PATH = Path(__file__).parent / "ingest_failures.json"

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="AskSQL Markets ingestion pipeline")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Only retry tickers that failed in the previous run",
    )
    args = parser.parse_args()

    # --- Step 1: get ticker list ---
    if args.retry_failed:
        tickers_to_run = _load_failed_tickers()
        if not tickers_to_run:
            console.print("[yellow]No failed tickers found. Nothing to retry.[/]")
            return
        console.print(f"[bold blue]Retrying[/] {len(tickers_to_run)} previously failed tickers")
        wiki_rows = {row["ticker"]: row for row in scrape_sp500_wikipedia()}
        sp500_rows = [wiki_rows.get(t, {"ticker": t}) for t in tickers_to_run]
    else:
        console.print("[bold blue]Step 1/3[/] Scraping S&P 500 list from Wikipedia...")
        sp500_rows = scrape_sp500_wikipedia()
        console.print(f"  Found [bold]{len(sp500_rows)}[/] tickers\n")

    # --- Step 2: initialize DB schema ---
    console.print("[bold blue]Step 2/3[/] Initializing database schema...")
    engine = get_engine()
    Base.metadata.create_all(engine)
    console.print("  Schema ready\n")

    # --- Step 3: ingest ---
    console.print(f"[bold blue]Step 3/3[/] Ingesting data for {len(sp500_rows)} tickers...\n")

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
        task = progress.add_task("Starting...", total=len(sp500_rows))

        for i, row in enumerate(sp500_rows):
            ticker_str = row["ticker"]
            progress.update(task, description=f"[cyan]{ticker_str:<6}[/]")

            if i > 0 and i % BATCH_COOLDOWN_EVERY == 0:
                progress.update(task, description=f"[yellow]cooldown ({BATCH_COOLDOWN_SECS}s)[/]")
                time.sleep(BATCH_COOLDOWN_SECS)

            _ingest_single(ticker_str, row, engine, progress, task)
            time.sleep(INTER_TICKER_DELAY)

    # --- Write failure log ---
    failures = get_failures()
    with open(FAILURES_PATH, "w") as f:
        json.dump(failures, f, indent=2)

    # --- Print summary ---
    _print_summary(engine, failures)

    # --- Inline spot-checks ---
    _run_spot_checks(engine)


def _ingest_single(ticker_str: str, wiki_row: dict, engine, progress, task) -> None:
    from yfinance.exceptions import YFRateLimitError

    for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
        try:
            yf_ticker = yf.Ticker(ticker_str)

            meta = fetch_company_metadata(ticker_str, yf_ticker)
            upsert_company(ticker_str, wiki_row, meta, engine)

            price_df = fetch_price_history(ticker_str, yf_ticker)
            if price_df is not None:
                bulk_insert_prices(ticker_str, price_df, engine)

            fin_records = fetch_financials(ticker_str, yf_ticker)
            if fin_records:
                bulk_insert_financials(ticker_str, fin_records, engine)

            div_series = fetch_dividends(ticker_str, yf_ticker)
            if div_series is not None:
                bulk_insert_dividends(ticker_str, div_series, engine)

            break  # success

        except YFRateLimitError:
            if attempt < RATE_LIMIT_MAX_RETRIES:
                wait = (2**attempt) * RATE_LIMIT_BACKOFF_BASE
                time.sleep(wait)
            else:
                log_failure(ticker_str, "rate_limit", "exceeded max retries")
                break
        except Exception as e:
            log_failure(ticker_str, "pipeline", str(e))
            break

    progress.advance(task)


def _print_summary(engine, failures: dict) -> None:
    console.print()
    table = Table(title="Ingestion Summary", show_header=True)
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right", style="green")

    table_names = ["companies", "prices", "financials", "dividends"]
    with engine.connect() as conn:
        for name in table_names:
            row = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).fetchone()
            table.add_row(name, f"{row[0]:,}")

    console.print(table)

    if failures:
        console.print(
            f"\n[yellow]Failed tickers: {len(failures)}[/] — see [bold]{FAILURES_PATH}[/]"
        )
    else:
        console.print("\n[bold green]All tickers ingested successfully.[/]")


def _run_spot_checks(engine) -> None:
    console.print("\n[bold blue]Spot Checks[/]")
    checks = [
        (
            "Companies with no sector",
            "SELECT COUNT(*) FROM companies WHERE sector IS NULL",
            lambda r: f"{r[0]} (expect < 10)",
            lambda r: r[0] < 10,
        ),
        (
            "FK integrity check",
            "PRAGMA foreign_key_check",
            lambda r: "PASS" if r is None else f"FAIL — violations found",
            lambda r: r is None,
        ),
        (
            "Tickers with no prices",
            dedent("""
                SELECT COUNT(*) FROM companies
                WHERE ticker NOT IN (SELECT DISTINCT ticker FROM prices)
            """),
            lambda r: f"{r[0]} tickers (should match failure count)",
            lambda _: True,
        ),
        (
            "Avg revenue sanity (billions)",
            "SELECT AVG(revenue) FROM financials WHERE revenue IS NOT NULL",
            lambda r: f"${r[0] / 1e9:.1f}B" if r[0] else "NULL",
            lambda r: r[0] is not None and r[0] > 1e8,
        ),
    ]

    with engine.connect() as conn:
        for label, query, fmt, passing in checks:
            result = conn.execute(text(query)).fetchone()
            ok = passing(result)
            status = "[green]PASS[/]" if ok else "[red]WARN[/]"
            console.print(f"  {status} {label}: {fmt(result)}")


def _load_failed_tickers() -> list[str]:
    if not FAILURES_PATH.exists():
        return []
    with open(FAILURES_PATH) as f:
        data = json.load(f)
    return list(data.keys())


if __name__ == "__main__":
    main()
