"""
Backfill the dividends table without re-running the full pipeline

Usage:
    cd backend
    python -m data.backfill_dividends
"""

import time

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

from .ingest import bulk_insert_dividends, fetch_dividends, log_failure, get_failures
from .models import get_engine

INTER_TICKER_DELAY = 1.2
BATCH_COOLDOWN_EVERY = 50
BATCH_COOLDOWN_SECS = 5.0
RATE_LIMIT_BACKOFF_BASE = 10
RATE_LIMIT_MAX_RETRIES = 3

console = Console()


def main() -> None:
    engine = get_engine()

    with engine.connect() as conn:
        tickers = [row[0] for row in conn.execute(text("SELECT ticker FROM companies ORDER BY ticker"))]

    console.print(f"[bold blue]Backfilling dividends[/] for {len(tickers)} tickers...\n")

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

        for i, ticker_str in enumerate(tickers):
            progress.update(task, description=f"[cyan]{ticker_str:<6}[/]")

            if i > 0 and i % BATCH_COOLDOWN_EVERY == 0:
                progress.update(task, description=f"[yellow]cooldown ({BATCH_COOLDOWN_SECS}s)[/]")
                time.sleep(BATCH_COOLDOWN_SECS)

            _backfill_single(ticker_str, engine)
            progress.advance(task)
            time.sleep(INTER_TICKER_DELAY)

    failures = get_failures()
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM dividends")).fetchone()[0]

    console.print()
    table = Table(title="Dividends Backfill Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    table.add_row("Total dividend rows inserted", f"{count:,}")
    table.add_row("Tickers with failures", str(len(failures)))
    console.print(table)

    if failures:
        console.print("\n[yellow]Failed tickers:[/]")
        for t, reasons in failures.items():
            console.print(f"  [red]{t}[/]: {reasons}")
    else:
        console.print("\n[bold green]All tickers processed successfully.[/]")


def _backfill_single(ticker_str: str, engine) -> None:
    from yfinance.exceptions import YFRateLimitError

    for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
        try:
            yf_ticker = yf.Ticker(ticker_str)
            divs = fetch_dividends(ticker_str, yf_ticker)
            if divs is not None and len(divs) > 0:
                bulk_insert_dividends(ticker_str, divs, engine)
            break
        except YFRateLimitError:
            if attempt < RATE_LIMIT_MAX_RETRIES:
                wait = (2 ** attempt) * RATE_LIMIT_BACKOFF_BASE
                time.sleep(wait)
            else:
                log_failure(ticker_str, "dividends", "exceeded max retries")
                break
        except Exception as e:
            log_failure(ticker_str, "dividends", str(e))
            break


if __name__ == "__main__":
    main()
