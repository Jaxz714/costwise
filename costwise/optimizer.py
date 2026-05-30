"""Optimization recommendations engine."""

from __future__ import annotations

from typing import Optional

from .config import load_pricing
from .models import CostSummary, ModelPricing, TaskComplexity
from .router import ModelRouter
from .tracker import UsageTracker


class CostOptimizer:
    """Analyzes usage patterns and provides cost optimization recommendations."""

    def __init__(self, tracker: Optional[UsageTracker] = None) -> None:
        self.tracker = tracker or UsageTracker()
        self.router = ModelRouter()
        self.models = load_pricing()

    def analyze(self, period: str = "month") -> dict:
        """Analyze usage and generate recommendations.

        Returns dict with analysis results and recommendations.
        """
        summary = self.tracker.get_summary(period)
        recommendations = []

        # 1. Check if cheaper models could handle current tasks
        model_rec = self._analyze_model_usage(summary)
        if model_rec:
            recommendations.append(model_rec)

        # 2. Check complexity distribution
        complexity_rec = self._analyze_complexity_distribution(summary)
        if complexity_rec:
            recommendations.append(complexity_rec)

        # 3. Check provider concentration
        provider_rec = self._analyze_provider_concentration(summary)
        if provider_rec:
            recommendations.append(provider_rec)

        # 4. Calculate total potential savings
        total_savings = sum(r.get("potential_savings", 0) for r in recommendations)

        return {
            "period": period,
            "current_cost": summary.total_cost,
            "total_requests": summary.total_requests,
            "recommendations": recommendations,
            "total_potential_savings": total_savings,
            "savings_percent": (
                (total_savings / summary.total_cost * 100)
                if summary.total_cost > 0
                else 0
            ),
        }

    def _analyze_model_usage(self, summary: CostSummary) -> Optional[dict]:
        """Check if cheaper models could handle current workloads."""
        if not summary.by_model:
            return None

        total_savings = 0.0
        suggestions = []

        for model_id, cost in summary.by_model.items():
            if cost < 0.01:  # skip negligible costs
                continue

            model = self.models.get(model_id)
            if not model:
                continue

            # Find cheapest alternative for same complexity
            for complexity in model.complexity_tiers:
                cheapest = self.router.get_cheapest(complexity)
                if cheapest and cheapest.model_id != model_id:
                    # Estimate savings (simplified)
                    price_ratio = cheapest.avg_price_per_1m / model.avg_price_per_1m
                    potential_savings = cost * (1 - price_ratio)

                    if potential_savings > 0.01:
                        total_savings += potential_savings
                        suggestions.append({
                            "current_model": model.display_name,
                            "suggested_model": cheapest.display_name,
                            "current_cost": cost,
                            "potential_savings": potential_savings,
                            "savings_percent": (1 - price_ratio) * 100,
                        })
                    break  # only check first complexity tier

        if not suggestions:
            return None

        return {
            "type": "model_optimization",
            "title": "Model Selection Optimization",
            "description": "Switch to cheaper models for tasks that don't require top-tier capabilities.",
            "suggestions": suggestions[:5],  # top 5
            "potential_savings": total_savings,
        }

    def _analyze_complexity_distribution(self, summary: CostSummary) -> Optional[dict]:
        """Analyze if tasks are being routed to appropriate complexity levels."""
        if not summary.by_complexity:
            return None

        total = sum(summary.by_complexity.values())
        if total == 0:
            return None

        complex_pct = summary.by_complexity.get("complex", 0) / total
        medium_pct = summary.by_complexity.get("medium", 0) / total
        simple_pct = summary.by_complexity.get("simple", 0) / total

        suggestions = []
        potential_savings = 0.0

        # If too many tasks classified as complex
        if complex_pct > 0.5:
            savings = summary.by_complexity.get("complex", 0) * 0.3
            potential_savings += savings
            suggestions.append(
                f"{complex_pct:.0%} of spending is on complex tasks. "
                f"Review if some could be simplified to save ~${savings:.2f}."
            )

        # If simple tasks are using expensive models
        simple_cost = summary.by_complexity.get("simple", 0)
        if simple_cost > 0:
            cheapest_simple = self.router.get_cheapest(TaskComplexity.SIMPLE)
            if cheapest_simple:
                savings = simple_cost * 0.5  # estimate 50% savings possible
                potential_savings += savings
                suggestions.append(
                    f"Simple tasks cost ${simple_cost:.2f}. "
                    f"Using {cheapest_simple.display_name} could save ~${savings:.2f}."
                )

        if not suggestions:
            return None

        return {
            "type": "complexity_optimization",
            "title": "Task Complexity Analysis",
            "description": "Optimize how tasks are classified and routed.",
            "suggestions": suggestions,
            "potential_savings": potential_savings,
            "distribution": {
                "simple": f"{simple_pct:.0%}",
                "medium": f"{medium_pct:.0%}",
                "complex": f"{complex_pct:.0%}",
            },
        }

    def _analyze_provider_concentration(self, summary: CostSummary) -> Optional[dict]:
        """Check if switching providers could save money."""
        if len(summary.by_provider) < 2:
            return None

        total = sum(summary.by_provider.values())
        if total == 0:
            return None

        # Find most expensive provider
        most_expensive_provider = max(summary.by_provider, key=summary.by_provider.get)
        most_expensive_cost = summary.by_provider[most_expensive_provider]

        # Find cheapest provider
        cheapest_provider = min(summary.by_provider, key=summary.by_provider.get)
        cheapest_cost = summary.by_provider[cheapest_provider]

        if most_expensive_cost <= cheapest_cost * 1.5:
            return None  # not enough difference

        # Calculate potential savings
        # Estimate: shift 30% of expensive provider usage to cheaper
        shift_amount = most_expensive_cost * 0.3
        savings = shift_amount * 0.5  # estimate 50% cheaper

        return {
            "type": "provider_diversification",
            "title": "Provider Cost Optimization",
            "description": "Diversify across providers to reduce costs.",
            "suggestions": [
                f"Your top provider ({most_expensive_provider}) accounts for "
                f"${most_expensive_cost:.2f}. Consider shifting some tasks to "
                f"{cheapest_provider} to save ~${savings:.2f}.",
            ],
            "potential_savings": savings,
        }

    def calculate_savings(self, period: str = "month") -> dict:
        """Calculate how much was saved by using smart routing.

        Compares actual costs vs what it would have cost using the most
        expensive model for everything.
        """
        summary = self.tracker.get_summary(period)

        if summary.total_requests == 0:
            return {
                "actual_cost": 0.0,
                "worst_case_cost": 0.0,
                "total_savings": 0.0,
                "savings_percent": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
            }

        # Find most expensive model
        most_expensive = max(self.models.values(), key=lambda m: m.avg_price_per_1m)

        # Calculate what it would have cost with the most expensive model
        worst_case_cost = (
            (summary.total_input_tokens / 1_000_000) * most_expensive.input_price_per_1m
            + (summary.total_output_tokens / 1_000_000) * most_expensive.output_price_per_1m
        )

        savings = worst_case_cost - summary.total_cost

        return {
            "actual_cost": summary.total_cost,
            "worst_case_cost": worst_case_cost,
            "worst_case_model": most_expensive.display_name,
            "total_savings": max(0, savings),
            "savings_percent": (savings / worst_case_cost * 100) if worst_case_cost > 0 else 0,
            "total_input_tokens": summary.total_input_tokens,
            "total_output_tokens": summary.total_output_tokens,
        }
