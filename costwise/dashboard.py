"""Rich terminal dashboard for CostWise."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.layout import Layout
from rich import box

from .alerter import BudgetAlerter
from .config import load_pricing
from .models import CostSummary, ModelPricing
from .optimizer import CostOptimizer
from .router import ModelRouter
from .tracker import UsageTracker

console = Console()


def format_currency(amount: float) -> str:
    """Format a dollar amount."""
    if amount >= 1000:
        return f"${amount:,.2f}"
    elif amount >= 1:
        return f"${amount:.2f}"
    elif amount >= 0.01:
        return f"${amount:.3f}"
    else:
        return f"${amount:.4f}"


def format_tokens(count: int) -> str:
    """Format token count."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def show_dashboard(period: str = "month") -> None:
    """Display the cost dashboard."""
    tracker = UsageTracker()
    alerter = BudgetAlerter(tracker)
    summary = tracker.get_summary(period)
    budget_status = alerter.check_budget()

    # Title
    console.print()
    console.print(
        Panel(
            "[bold cyan]CostWise Dashboard[/bold cyan]",
            subtitle=f"Period: {period.title()} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            border_style="cyan",
        )
    )

    # Budget alerts
    if budget_status["alerts"]:
        for alert in budget_status["alerts"]:
            style = "red" if alert["threshold"] >= 0.9 else "yellow"
            console.print(f"[{style}]WARNING: {alert['message']}[/{style}]")
        console.print()

    # Overview cards
    _show_overview(summary, budget_status)

    # Breakdowns
    if summary.by_model:
        _show_model_breakdown(summary)
    if summary.by_provider:
        _show_provider_breakdown(summary)
    if summary.by_complexity:
        _show_complexity_breakdown(summary)
    if summary.daily_costs:
        _show_daily_trend(summary)

    console.print()


def _show_overview(summary: CostSummary, budget_status: dict) -> None:
    """Show overview summary cards."""
    # Total cost
    cost_text = Text(format_currency(summary.total_cost), style="bold green")
    cost_panel = Panel(
        cost_text,
        title="Total Cost",
        border_style="green",
        width=25,
    )

    # Total requests
    req_panel = Panel(
        Text(str(summary.total_requests), style="bold cyan"),
        title="Requests",
        border_style="cyan",
        width=25,
    )

    # Total tokens
    total_tokens = summary.total_input_tokens + summary.total_output_tokens
    token_panel = Panel(
        Text(format_tokens(total_tokens), style="bold yellow"),
        title="Total Tokens",
        border_style="yellow",
        width=25,
    )

    # Budget status
    if budget_status["monthly_limit"] > 0:
        pct = budget_status["monthly_percent"]
        style = "green" if pct < 0.75 else "yellow" if pct < 0.9 else "red"
        budget_text = Text(
            f"{format_currency(budget_status['monthly_spent'])} / "
            f"{format_currency(budget_status['monthly_limit'])}",
            style=style,
        )
    else:
        budget_text = Text("Not set", style="dim")

    budget_panel = Panel(
        budget_text,
        title="Monthly Budget",
        border_style="blue",
        width=25,
    )

    console.print(Columns([cost_panel, req_panel, token_panel, budget_panel]))
    console.print()


def _show_model_breakdown(summary: CostSummary) -> None:
    """Show cost breakdown by model."""
    table = Table(
        title="Cost by Model",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Model", style="white")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("% of Total", justify="right")
    table.add_column("Bar", width=20)

    max_cost = max(summary.by_model.values()) if summary.by_model else 1
    for model_id, cost in sorted(summary.by_model.items(), key=lambda x: x[1], reverse=True):
        pct = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
        bar_len = int((cost / max_cost) * 20) if max_cost > 0 else 0
        bar = "[green]" + "#" * bar_len + "[/green]" + "[dim]" + "-" * (20 - bar_len) + "[/dim]"
        table.add_row(model_id, format_currency(cost), f"{pct:.1f}%", bar)

    console.print(table)
    console.print()


def _show_provider_breakdown(summary: CostSummary) -> None:
    """Show cost breakdown by provider."""
    table = Table(
        title="Cost by Provider",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Provider", style="white")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("% of Total", justify="right")
    table.add_column("Bar", width=20)

    max_cost = max(summary.by_provider.values()) if summary.by_provider else 1
    for provider, cost in sorted(summary.by_provider.items(), key=lambda x: x[1], reverse=True):
        pct = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
        bar_len = int((cost / max_cost) * 20) if max_cost > 0 else 0
        bar = "[blue]" + "#" * bar_len + "[/blue]" + "[dim]" + "-" * (20 - bar_len) + "[/dim]"
        table.add_row(provider, format_currency(cost), f"{pct:.1f}%", bar)

    console.print(table)
    console.print()


def _show_complexity_breakdown(summary: CostSummary) -> None:
    """Show cost breakdown by task complexity."""
    table = Table(
        title="Cost by Complexity",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Complexity", style="white")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("% of Total", justify="right")

    style_map = {"simple": "green", "medium": "yellow", "complex": "red"}
    for complexity, cost in sorted(summary.by_complexity.items()):
        pct = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
        style = style_map.get(complexity, "white")
        table.add_row(
            f"[{style}]{complexity.title()}[/{style}]",
            format_currency(cost),
            f"{pct:.1f}%",
        )

    console.print(table)
    console.print()


def _show_daily_trend(summary: CostSummary) -> None:
    """Show daily cost trend."""
    if not summary.daily_costs:
        return

    table = Table(
        title="Daily Costs",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Date", style="white")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Bar", width=30)

    max_cost = max(summary.daily_costs.values()) if summary.daily_costs else 1
    for day, cost in sorted(summary.daily_costs.items()):
        bar_len = int((cost / max_cost) * 30) if max_cost > 0 else 0
        bar = "[yellow]" + "#" * bar_len + "[/yellow]" + "[dim]" + "-" * (30 - bar_len) + "[/dim]"
        table.add_row(day, format_currency(cost), bar)

    console.print(table)


def show_models() -> None:
    """Display all available models with pricing."""
    models = load_pricing()

    table = Table(
        title="Available Models",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Model", style="white", max_width=25)
    table.add_column("Provider", style="cyan", max_width=12)
    table.add_column("Input $/1M", justify="right", style="green")
    table.add_column("Output $/1M", justify="right", style="green")
    table.add_column("Context", justify="right")
    table.add_column("Quality", justify="right")
    table.add_column("Speed", justify="right")
    table.add_column("Tiers", style="yellow")

    for model in sorted(models.values(), key=lambda m: m.avg_price_per_1m):
        tiers = ", ".join(t.value for t in model.complexity_tiers)
        table.add_row(
            model.display_name,
            model.provider.value,
            f"${model.input_price_per_1m:.2f}",
            f"${model.output_price_per_1m:.2f}",
            format_tokens(model.max_context),
            f"{model.quality_score}/100",
            f"{model.speed_score}/100",
            tiers,
        )

    console.print()
    console.print(table)
    console.print()


def show_savings(period: str = "month") -> None:
    """Display savings report."""
    optimizer = CostOptimizer()
    savings = optimizer.calculate_savings(period)

    console.print()
    console.print(
        Panel(
            "[bold cyan]CostWise Savings Report[/bold cyan]",
            subtitle=f"Period: {period.title()}",
            border_style="cyan",
        )
    )

    # Summary table
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Actual Cost", format_currency(savings["actual_cost"]))
    table.add_row(
        f"Worst Case ({savings.get('worst_case_model', 'N/A')})",
        format_currency(savings["worst_case_cost"]),
    )
    table.add_row(
        "[bold green]Total Savings[/bold green]",
        f"[bold green]{format_currency(savings['total_savings'])}[/bold green]",
    )
    table.add_row(
        "Savings Percentage",
        f"{savings['savings_percent']:.1f}%",
    )
    table.add_row("Input Tokens", format_tokens(savings["total_input_tokens"]))
    table.add_row("Output Tokens", format_tokens(savings["total_output_tokens"]))

    console.print(Panel(table, title="Savings Summary", border_style="green"))
    console.print()


def show_optimize(period: str = "month") -> None:
    """Display optimization recommendations."""
    optimizer = CostOptimizer()
    analysis = optimizer.analyze(period)

    console.print()
    console.print(
        Panel(
            "[bold cyan]CostWise Optimization Report[/bold cyan]",
            subtitle=f"Period: {period.title()}",
            border_style="cyan",
        )
    )

    if analysis["total_requests"] == 0:
        console.print("[dim]No usage data to analyze. Start making API calls to get recommendations.[/dim]")
        console.print()
        return

    console.print(f"Current cost: {format_currency(analysis['current_cost'])}")
    console.print(f"Total requests: {analysis['total_requests']}")
    console.print()

    for rec in analysis["recommendations"]:
        console.print(f"[bold yellow]{rec['title']}[/bold yellow]")
        console.print(f"  {rec['description']}")
        console.print()

        for suggestion in rec.get("suggestions", []):
            if isinstance(suggestion, dict):
                console.print(
                    f"  - {suggestion['current_model']} -> {suggestion['suggested_model']}: "
                    f"save {format_currency(suggestion['potential_savings'])} "
                    f"({suggestion['savings_percent']:.0f}%)"
                )
            else:
                console.print(f"  - {suggestion}")
        console.print()

    # Total potential savings
    savings = analysis["total_potential_savings"]
    pct = analysis["savings_percent"]
    if savings > 0:
        console.print(
            Panel(
                f"[bold green]Potential savings: {format_currency(savings)} "
                f"({pct:.1f}% of current spend)[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print("[dim]Your usage is already well optimized![/dim]")

    console.print()


def show_compare() -> None:
    """Compare provider costs."""
    models = load_pricing()

    # Group by provider
    providers: dict[str, list[ModelPricing]] = {}
    for model in models.values():
        provider = model.provider.value
        if provider not in providers:
            providers[provider] = []
        providers[provider].append(model)

    console.print()
    console.print(
        Panel(
            "[bold cyan]Provider Cost Comparison[/bold cyan]",
            border_style="cyan",
        )
    )

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Provider", style="bold white")
    table.add_column("Cheapest Model", style="green")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Best Model", style="yellow")
    table.add_column("Price", justify="right", style="yellow")
    table.add_column("Models", justify="right")

    for provider, provider_models in sorted(providers.items()):
        cheapest = min(provider_models, key=lambda m: m.avg_price_per_1m)
        best = max(provider_models, key=lambda m: m.quality_score)
        table.add_row(
            provider,
            cheapest.display_name,
            format_currency(cheapest.avg_price_per_1m),
            best.display_name,
            format_currency(best.avg_price_per_1m),
            str(len(provider_models)),
        )

    console.print(table)

    # Price range comparison
    console.print()
    all_models = list(models.values())
    cheapest_overall = min(all_models, key=lambda m: m.avg_price_per_1m)
    most_expensive = max(all_models, key=lambda m: m.avg_price_per_1m)
    ratio = most_expensive.avg_price_per_1m / cheapest_overall.avg_price_per_1m

    console.print(
        f"Price range: {cheapest_overall.display_name} "
        f"({format_currency(cheapest_overall.avg_price_per_1m)}) to "
        f"{most_expensive.display_name} "
        f"({format_currency(most_expensive.avg_price_per_1m)})"
    )
    console.print(f"Price ratio: {ratio:.0f}x difference between cheapest and most expensive")
    console.print()
