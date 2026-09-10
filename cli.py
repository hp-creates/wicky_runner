"""
Modern, beautiful CLI interface for WikiRunner AI using Rich.
Supports interactive runs, custom start/target inputs, and benchmarking.
"""

import sys
import os
import argparse
import time

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box

from wikirunner import WikiSpeedrunner, RunnerConfig

console = Console()


def display_welcome():
    console.print(Panel.fit(
        "[bold cyan]WikiSpeedrunner AI (v2.0)[/bold cyan]\n"
        "[dim]High-Performance Bidirectional Informed Graph Traversal Engine[/dim]",
        border_style="cyan"
    ))


def run_single(start: str, target: str, enable_llm: bool = True):
    config = RunnerConfig(enable_llm_advisor=enable_llm)
    runner = WikiSpeedrunner(config)

    with console.status(f"[bold yellow]Indexing '{target}' & navigating from '{start}'...[/bold yellow]"):
        result = runner.run(start, target)

    console.print()
    if result.status == "victory":
        status_color = "bold green"
        status_icon = "[VICTORY]"
    else:
        status_color = "bold red"
        status_icon = "[FAILED]"

    console.print(Panel(
        f"[{status_color}]{status_icon} Status: {result.status.upper()}[/{status_color}]\n"
        f"[bold]Steps Taken:[/bold] {result.steps}\n"
        f"[bold]Elapsed Time:[/bold] {result.elapsed_seconds:.2f}s\n"
        f"[bold]API Requests:[/bold] {result.api_calls}\n"
        f"[bold]Pages Visited:[/bold] {result.visited_count}",
        title="Speedrun Summary",
        border_style="green" if result.status == "victory" else "red"
    ))

    # Print Traversed Path Tree
    tree = Tree("[bold cyan]Traversed Path[/bold cyan]")
    current_node = tree
    for i, title in enumerate(result.path_titles):
        is_last = (i == len(result.path_titles) - 1)
        if i == 0:
            current_node = current_node.add(f"[bold yellow]Start:[/bold yellow] [underline]{title}[/underline]")
        elif is_last and result.status == "victory":
            current_node = current_node.add(f"[bold green]🎯 Target:[/bold green] [underline]{title}[/underline]")
        else:
            current_node = current_node.add(f"[white]Step {i}:[/white] [cyan]{title}[/cyan]")

    console.print(tree)
    console.print()

    # Detailed Step Table
    if result.log:
        table = Table(title="Step-by-Step Decision Log", box=box.ROUNDED)
        table.add_column("Step", style="dim", width=6)
        table.add_column("From", style="cyan")
        table.add_column("Chosen Link", style="green bold")
        table.add_column("Strategy / Reason", style="yellow")
        table.add_column("Score", justify="right", style="magenta")

        for log in result.log:
            table.add_row(
                str(log["step"]),
                log["current_title"],
                log["chosen_title"],
                log["strategy"],
                f"{log['score']:.2f}"
            )
        console.print(table)


def main():
    parser = argparse.ArgumentParser(description="WikiRunner AI - Intelligent Speedrunner")
    parser.add_argument("--start", "-s", type=str, help="Start page title (e.g., 'Apple')")
    parser.add_argument("--target", "-t", type=str, help="Target page title (e.g., 'Steve Jobs')")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM advisor fallback")
    args = parser.parse_args()

    display_welcome()

    start = args.start or console.input("[bold yellow]Enter Start Page: [/bold yellow]").strip()
    target = args.target or console.input("[bold yellow]Enter Target Page: [/bold yellow]").strip()

    if not start or not target:
        console.print("[red]Start and Target cannot be empty.[/red]")
        sys.exit(1)

    run_single(start, target, enable_llm=not args.no_llm)


if __name__ == "__main__":
    main()
