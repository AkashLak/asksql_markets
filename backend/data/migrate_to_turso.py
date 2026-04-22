"""
One-time migration: copy local markets.db → Turso

Run this once after creating your Turso database to seed it with
the data from the full local pipeline. After this, daily_refresh.py
keeps Turso up to date incrementally.

Usage:
    cd backend
    python -m data.migrate_to_turso
"""

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

TURSO_URL = os.getenv("TURSO_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
LOCAL_DB = Path(__file__).parent / "markets.db"
BATCH_SIZE = 500

# query_history is local-only — not migrated to Turso
TABLES = ["companies", "prices", "financials", "dividends"]

console = Console()


def main() -> None:
    if not TURSO_URL or not TURSO_AUTH_TOKEN:
        console.print("[red]Error:[/] TURSO_URL and TURSO_AUTH_TOKEN must be set in .env")
        raise SystemExit(1)

    if not LOCAL_DB.exists():
        console.print(f"[red]Error:[/] {LOCAL_DB} not found. Run `python -m data.run_pipeline` first.")
        raise SystemExit(1)

    import libsql_experimental as libsql

    local = sqlite3.connect(str(LOCAL_DB))
    turso = libsql.connect(TURSO_URL, auth_token=TURSO_AUTH_TOKEN)

    console.print(f"[bold blue]Migrating[/] {LOCAL_DB} → Turso\n")

    # Recreate tables in Turso using the same schema from local SQLite
    schema_rows = local.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name IN (?, ?, ?, ?) "
        "ORDER BY CASE name "
        "  WHEN 'companies' THEN 1 "
        "  WHEN 'prices'    THEN 2 "
        "  WHEN 'financials' THEN 3 "
        "  WHEN 'dividends' THEN 4 END",
        TABLES,
    ).fetchall()

    # Drop in reverse order to respect foreign keys
    for table in reversed(TABLES):
        turso.execute(f"DROP TABLE IF EXISTS {table}")
    turso.commit()

    for _, create_sql in schema_rows:
        if create_sql:
            turso.execute(create_sql)
    turso.commit()
    console.print("  Tables created in Turso\n")

    total_rows = 0
    for table in TABLES:
        count = local.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        col_names = [d[0] for d in local.execute(f"SELECT * FROM {table} LIMIT 0").description]
        placeholders = ", ".join("?" * len(col_names))
        insert_sql = f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})"

        console.print(f"  Copying [cyan]{table}[/] ({count:,} rows)...")

        with Progress(
            SpinnerColumn(),
            TextColumn(f"    {table}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("", total=count)
            offset = 0
            while True:
                batch = local.execute(f"SELECT * FROM {table} LIMIT {BATCH_SIZE} OFFSET {offset}").fetchall()
                if not batch:
                    break
                for row in batch:
                    turso.execute(insert_sql, list(row))
                turso.commit()
                progress.advance(task, len(batch))
                offset += len(batch)

        console.print(f"  [green]✓[/] {table}: {count:,} rows")
        total_rows += count

    local.close()

    console.print(f"\n[bold green]Migration complete![/] {total_rows:,} total rows → Turso")
    console.print("\nNext steps:")
    console.print("  1. Add TURSO_URL and TURSO_AUTH_TOKEN to Render environment variables")
    console.print("  2. Add them as GitHub repository secrets (for daily_refresh.yml)")
    console.print("  3. Redeploy on Render — the API will now sync from Turso on startup")


if __name__ == "__main__":
    main()
