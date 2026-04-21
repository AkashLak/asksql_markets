"""
AskSQL Markets - Evaluation runner

Usage:
    cd backend
    python -m eval.run_eval                     #run all 25 cases
    python -m eval.run_eval --ids 1 5 11        #run specific cases
    python -m eval.run_eval --category join     #run a category

Scoring:
    PASS: SQL ran, all structural checks pass
    PARTIAL: SQL ran but columns/rows/value check failed
    FAIL: SQL error OR wrong CANNOT_ANSWER behaviour
"""

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.table import Table
from rich import box

from agent.sql_agent import ask
from data.models import get_engine
from eval.suite import EVAL_SUITE, EvalCase

console = Console()

RESULTS_PATH = Path(__file__).parent / "eval_results.json"


#--- Scoring ---

def score_case(case: EvalCase, response: dict) -> tuple[str, list[str]]:
    """
    Returns (verdict, [failure reasons]).
    verdict: 'PASS' | 'PARTIAL' | 'FAIL'
    """
    failures = []
    sql = response.get("sql")
    success = response.get("success", False)
    columns = [c.lower() for c in response.get("columns", [])]
    results = response.get("results", [])

    #Strip sentinel row from results for counting
    data_rows = [
        r for r in results
        if not (r and isinstance(r[0], str) and r[0].startswith("…"))
    ]

    #--- CANNOT_ANSWER cases ---
    if not case.should_answer:
        if sql is None and success:
            return "PASS", []
        failures.append("Expected CANNOT_ANSWER but agent returned SQL")
        return "FAIL", failures

    #--- Cases that should produce SQL ---
    if not success:
        failures.append(f"Query failed: {response.get('error', 'unknown error')}")
        return "FAIL", failures

    if sql is None:
        failures.append("Agent returned CANNOT_ANSWER but a valid answer was expected")
        return "FAIL", failures

    #Table references
    sql_lower = sql.lower()
    for table in case.expected_tables:
        if table.lower() not in sql_lower:
            failures.append(f"SQL missing expected table '{table}'")

    #Column presence in results
    for col in case.expected_columns:
        #Accept partial column name match (Ex: "count" matches "count(*)" or "total_count")
        if not any(col.lower() in c for c in columns):
            failures.append(f"Result missing expected column '{col}' (got: {list(columns)})")

    #Row count
    n = len(data_rows)
    if n < case.min_rows:
        failures.append(f"Too few rows: got {n}, expected >= {case.min_rows}")
    if case.max_rows != -1 and n > case.max_rows:
        failures.append(f"Too many rows: got {n}, expected <= {case.max_rows}")

    #Value check
    if case.value_check and data_rows:
        try:
            orig_cols = [c for c in response.get("columns", [])]
            ok = case.value_check(orig_cols, data_rows)
            if not ok:
                first = data_rows[0] if data_rows else []
                failures.append(f"Value check failed — first row: {first}")
        except Exception as e:
            failures.append(f"Value check error: {e}")

    if not failures:
        return "PASS", []
    #Distinguish PARTIAL (ran but wrong shape) from FAIL (didn't run)
    return "PARTIAL", failures


#--- Runner ---

def run_eval(cases: list[EvalCase]) -> list[dict]:
    engine = get_engine()
    records = []

    console.print(f"\n[bold]Running {len(cases)} eval cases[/] against live agent…\n")

    for case in cases:
        start = time.time()
        try:
            response = ask(case.question, engine)
        except Exception as e:
            response = {"sql": None, "success": False, "columns": [], "results": [], "error": str(e), "explanation": ""}
        elapsed = time.time() - start

        verdict, failures = score_case(case, response)

        color = {"PASS": "green", "PARTIAL": "yellow", "FAIL": "red"}[verdict]
        console.print(
            f"  [{color}]{verdict:7}[/{color}] "
            f"[dim]#{case.id:02}[/dim] "
            f"[cyan]{case.category:15}[/cyan] "
            f"{case.question[:65]}"
            f"  [dim]{elapsed:.1f}s[/dim]"
        )
        if failures:
            for f in failures:
                console.print(f"           [yellow]↳ {f}[/yellow]")

        records.append({
            "id": case.id,
            "category": case.category,
            "question": case.question,
            "verdict": verdict,
            "failures": failures,
            "sql": response.get("sql"),
            "row_count": len([r for r in response.get("results", []) if not (r and isinstance(r[0], str) and r[0].startswith("…"))]),
            "elapsed_s": round(elapsed, 2),
        })

    return records


#--- Summary ---

def print_summary(records: list[dict]) -> None:
    total = len(records)
    by_verdict = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    by_category: dict[str, dict] = {}

    for r in records:
        by_verdict[r["verdict"]] += 1
        cat = r["category"]
        by_category.setdefault(cat, {"PASS": 0, "PARTIAL": 0, "FAIL": 0})
        by_category[cat][r["verdict"]] += 1

    pass_rate = by_verdict["PASS"] / total * 100
    partial_rate = by_verdict["PARTIAL"] / total * 100

    console.print()
    table = Table(title="Evaluation Summary", box=box.ROUNDED, show_lines=True)
    table.add_column("Category", style="cyan")
    table.add_column("PASS", justify="center", style="green")
    table.add_column("PARTIAL", justify="center", style="yellow")
    table.add_column("FAIL", justify="center", style="red")
    table.add_column("Total", justify="center")

    for cat, counts in sorted(by_category.items()):
        table.add_row(
            cat,
            str(counts["PASS"]),
            str(counts["PARTIAL"]),
            str(counts["FAIL"]),
            str(sum(counts.values())),
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold green]{by_verdict['PASS']}[/bold green]",
        f"[bold yellow]{by_verdict['PARTIAL']}[/bold yellow]",
        f"[bold red]{by_verdict['FAIL']}[/bold red]",
        f"[bold]{total}[/bold]",
    )
    console.print(table)

    console.print(
        f"\n[bold]Pass rate:[/bold]  [green]{pass_rate:.1f}%[/green] "
        f"({by_verdict['PASS']}/{total} PASS)"
    )
    console.print(
        f"[bold]Usable rate:[/bold] [cyan]{pass_rate + partial_rate:.1f}%[/cyan] "
        f"(PASS + PARTIAL — SQL ran, results returned)"
    )

    avg_time = sum(r["elapsed_s"] for r in records) / total
    console.print(f"[bold]Avg latency:[/bold] {avg_time:.1f}s per question\n")


#--- Entry point ---

def main() -> None:
    parser = argparse.ArgumentParser(description="AskSQL Markets eval runner")
    parser.add_argument("--ids", nargs="+", type=int, help="Run specific case IDs")
    parser.add_argument("--category", type=str, help="Run a specific category")
    args = parser.parse_args()

    cases = EVAL_SUITE
    if args.ids:
        cases = [c for c in cases if c.id in args.ids]
    if args.category:
        cases = [c for c in cases if c.category == args.category]

    if not cases:
        console.print("[red]No cases matched the filter.[/red]")
        sys.exit(1)

    records = run_eval(cases)
    print_summary(records)

    with open(RESULTS_PATH, "w") as f:
        json.dump(records, f, indent=2)
    console.print(f"Results saved to [bold]{RESULTS_PATH}[/bold]")


if __name__ == "__main__":
    main()
