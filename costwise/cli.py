"""CLI interface for CostWise."""

from __future__ import annotations

import click
from rich.console import Console

from .alerter import BudgetAlerter
from .config import init_config, get_config, save_user_config, get_budget_config
from .dashboard import (
    console,
    show_compare,
    show_dashboard,
    show_models,
    show_optimize,
    show_savings,
)
from .optimizer import CostOptimizer
from .router import ModelRouter
from .tracker import UsageTracker

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="costwise")
def cli() -> None:
    """CostWise - AI cost optimizer with smart model routing.

    Cut your AI API costs by 50-80% by intelligently routing tasks
    to the cheapest capable model.
    """
    pass


@cli.command()
def init() -> None:
    """Initialize CostWise configuration."""
    config_dir = init_config()
    console.print(f"[green]CostWise initialized![/green]")
    console.print(f"Config directory: {config_dir}")
    console.print(f"Database: {config_dir / 'usage.db'}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Set a budget: [cyan]costwise budget set 50[/cyan]")
    console.print("  2. View models:  [cyan]costwise models[/cyan]")
    console.print("  3. Check usage:  [cyan]costwise dashboard[/cyan]")


@cli.command()
@click.option("--period", "-p", default="month",
              type=click.Choice(["day", "week", "month", "year", "all"]),
              help="Time period to display")
def dashboard(period: str) -> None:
    """Show the cost dashboard."""
    init_config()
    show_dashboard(period)


@cli.command()
@click.option("--period", "-p", default="month",
              type=click.Choice(["day", "week", "month", "year", "all"]),
              help="Time period for savings calculation")
def savings(period: str) -> None:
    """Show savings from smart routing."""
    init_config()
    show_savings(period)


@cli.command()
@click.option("--period", "-p", default="month",
              type=click.Choice(["day", "week", "month", "year", "all"]),
              help="Time period to analyze")
def optimize(period: str) -> None:
    """Get optimization recommendations."""
    init_config()
    show_optimize(period)


@cli.command()
def models() -> None:
    """List all available models with pricing."""
    init_config()
    show_models()


@cli.command()
def compare() -> None:
    """Compare provider costs."""
    init_config()
    show_compare()


@cli.group()
def budget() -> None:
    """Budget management."""
    pass


@budget.command("set")
@click.argument("amount", type=float)
@click.option("--period", "-p", default="monthly",
              type=click.Choice(["monthly", "daily"]),
              help="Budget period")
def budget_set(amount: float, period: str) -> None:
    """Set budget limit in USD."""
    init_config()
    config = get_config()

    if "budget" not in config:
        config["budget"] = {}

    if period == "monthly":
        config["budget"]["monthly_limit"] = amount
        console.print(f"[green]Monthly budget set to ${amount:.2f}[/green]")
    else:
        config["budget"]["daily_limit"] = amount
        console.print(f"[green]Daily budget set to ${amount:.2f}[/green]")

    save_user_config(config)


@budget.command("status")
def budget_status() -> None:
    """Check budget status."""
    init_config()
    alerter = BudgetAlerter()
    status = alerter.check_budget()

    console.print()
    if status["monthly_limit"] > 0:
        pct = status["monthly_percent"]
        style = "green" if pct < 0.75 else "yellow" if pct < 0.9 else "red"
        console.print(
            f"Monthly: [{style}]${status['monthly_spent']:.2f}[/{style}] "
            f"/ ${status['monthly_limit']:.2f} ({pct:.0%})"
        )
    else:
        console.print("Monthly: [dim]Not configured[/dim]")

    if status["daily_limit"] > 0:
        pct = status["daily_percent"]
        style = "green" if pct < 0.75 else "yellow" if pct < 0.9 else "red"
        console.print(
            f"Daily:   [{style}]${status['daily_spent']:.2f}[/{style}] "
            f"/ ${status['daily_limit']:.2f} ({pct:.0%})"
        )
    else:
        console.print("Daily:   [dim]Not configured[/dim]")

    if status["alerts"]:
        console.print()
        for alert in status["alerts"]:
            console.print(f"[yellow]Alert: {alert['message']}[/yellow]")

    console.print()


@cli.command()
@click.argument("task_description")
@click.option("--input-tokens", "-i", default=1000, type=int,
              help="Estimated input tokens")
@click.option("--output-tokens", "-o", default=500, type=int,
              help="Estimated output tokens")
def route(task_description: str, input_tokens: int, output_tokens: int) -> None:
    """Route a task to the optimal model."""
    init_config()
    router = ModelRouter()
    decision = router.choose(task_description, input_tokens, output_tokens)

    console.print()
    console.print(f"[bold]Task:[/bold] {task_description}")
    console.print(f"[bold]Complexity:[/bold] {decision.complexity.value}")
    console.print()
    console.print(f"[bold green]Chosen model:[/bold green] {decision.chosen_model.display_name}")
    console.print(f"  Provider: {decision.chosen_model.provider.value}")
    console.print(f"  Est. cost: ${decision.estimated_cost:.4f}")
    console.print()
    console.print(f"[dim]Cheapest option: {decision.cheapest_model.display_name} "
                  f"({decision.cheapest_model.provider.value})[/dim]")
    console.print(f"[dim]Most expensive: {decision.most_expensive_model.display_name} "
                  f"({decision.most_expensive_model.provider.value})[/dim]")
    if decision.potential_savings > 0:
        console.print(f"[green]Potential savings vs most expensive: "
                      f"${decision.potential_savings:.4f}[/green]")
    console.print()


@cli.command()
@click.option("--limit", "-l", default=20, type=int, help="Number of records to show")
def history(limit: int) -> None:
    """Show recent usage history."""
    init_config()
    tracker = UsageTracker()
    records = tracker.get_recent_records(limit)

    if not records:
        console.print("[dim]No usage records found.[/dim]")
        return

    from rich.table import Table
    from rich import box

    table = Table(
        title="Recent Usage",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Time", style="dim")
    table.add_column("Model", style="white")
    table.add_column("Complexity")
    table.add_column("In Tokens", justify="right")
    table.add_column("Out Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Task", max_width=30)

    style_map = {"simple": "green", "medium": "yellow", "complex": "red"}
    for record in records:
        ts = record.timestamp.strftime("%m-%d %H:%M") if record.timestamp else "N/A"
        cstyle = style_map.get(record.complexity, "white")
        table.add_row(
            ts,
            record.model_id,
            f"[{cstyle}]{record.complexity}[/{cstyle}]",
            str(record.input_tokens),
            str(record.output_tokens),
            f"${record.total_cost:.4f}",
            record.task_description[:30] if record.task_description else "",
        )

    console.print()
    console.print(table)
    console.print()


if __name__ == "__main__":
    cli()
