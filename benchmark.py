"""
Automated Benchmarking Suite for WikiRunner AI.
Tests the engine across standard Wikispeedia pairs ranging from direct hubs to cross-domain gaps.
"""

import sys
import os
import time

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rich.console import Console
from rich.table import Table
from rich import box

from wikirunner import WikiSpeedrunner, RunnerConfig

console = Console()

TEST_CASES = [
    {
        "category": "Disambiguation Trap",
        "start": "Apple",
        "target": "Steve Jobs",
        "expected_max_steps": 3,
    },
    {
        "category": "Political Hub",
        "start": "Barack Obama",
        "target": "United States",
        "expected_max_steps": 3,
    },
    {
        "category": "Technology Bridge",
        "start": "Python (programming language)",
        "target": "Guido van Rossum",
        "expected_max_steps": 2,
    },
    {
        "category": "Science to History",
        "start": "Albert Einstein",
        "target": "World War II",
        "expected_max_steps": 3,
    },
    {
        "category": "Cross-Domain Gap",
        "start": "Linux",
        "target": "Linus Torvalds",
        "expected_max_steps": 2,
    }
]


def run_benchmark():
    console.print("\n[bold cyan]=== Starting WikiSpeedrunner Benchmark Suite ===[/bold cyan]\n")

    config = RunnerConfig(enable_llm_advisor=True)
    runner = WikiSpeedrunner(config)

    table = Table(title="Benchmark Results", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Start Article", style="white")
    table.add_column("Target Article", style="yellow")
    table.add_column("Status", justify="center")
    table.add_column("Steps", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Path Taken", style="dim")

    total_time = 0.0
    passed = 0

    for tc in TEST_CASES:
        start = tc["start"]
        target = tc["target"]
        category = tc["category"]

        console.print(f"[dim]Running '{start}' -> '{target}'...[/dim]")
        t0 = time.time()
        res = runner.run(start, target)
        elapsed = time.time() - t0
        total_time += elapsed

        is_success = (res.status == "victory" and res.steps <= tc["expected_max_steps"] + 1)
        if is_success:
            passed += 1
            status_str = "[bold green]PASS[/bold green]"
        else:
            status_str = f"[bold red]{res.status.upper()}[/bold red]"

        path_str = " -> ".join(res.path_titles[:4])
        if len(res.path_titles) > 4:
            path_str += " -> ..."

        table.add_row(
            category,
            start,
            target,
            status_str,
            str(res.steps),
            f"{res.elapsed_seconds:.2f}",
            path_str
        )

    console.print()
    console.print(table)
    console.print(
        f"\n[bold green]Summary:[/bold green] {passed}/{len(TEST_CASES)} passed in {total_time:.2f}s total execution time.\n"
    )


if __name__ == "__main__":
    run_benchmark()
