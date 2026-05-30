"""Smart model routing with complexity classification."""

from __future__ import annotations

from typing import Optional

from .classifier import TaskClassifier
from .config import get_config, load_pricing
from .models import ModelPricing, RoutingDecision, TaskComplexity


class ModelRouter:
    """Routes tasks to the optimal model based on complexity and cost."""

    def __init__(self) -> None:
        self.classifier = TaskClassifier()
        self.models = load_pricing()
        self.config = get_config()

    def _get_routing_weights(self) -> dict[str, float]:
        """Get routing weights from config."""
        routing_config = self.config.get("routing", {})
        return routing_config.get("weights", {
            "cost": 0.5,
            "quality": 0.3,
            "speed": 0.2,
        })

    def _get_min_quality(self, complexity: TaskComplexity) -> float:
        """Get minimum quality score for a complexity level."""
        overrides = self.config.get("routing", {}).get("complexity_overrides", {})
        level_config = overrides.get(complexity.value, {})
        return level_config.get("min_quality_score", 60)

    def _get_max_price(self, complexity: TaskComplexity) -> Optional[float]:
        """Get max price per 1M tokens for a complexity level."""
        overrides = self.config.get("routing", {}).get("complexity_overrides", {})
        level_config = overrides.get(complexity.value, {})
        return level_config.get("max_price_per_1m")

    def _score_model(
        self,
        model: ModelPricing,
        complexity: TaskComplexity,
        weights: dict[str, float],
    ) -> float:
        """Score a model for a given task complexity.

        Higher score = better fit.
        """
        # Check if model handles this complexity level
        if complexity not in model.complexity_tiers:
            return -1.0

        min_quality = self._get_min_quality(complexity)
        if model.quality_score < min_quality:
            return -1.0

        max_price = self._get_max_price(complexity)
        if max_price is not None and model.avg_price_per_1m > max_price:
            return -1.0

        # Normalize scores (0-1 range)
        # Cost: lower is better, so invert
        price_range = max(m.avg_price_per_1m for m in self.models.values()) or 1
        cost_score = 1.0 - (model.avg_price_per_1m / price_range)

        quality_score = model.quality_score / 100.0
        speed_score = model.speed_score / 100.0

        # Weighted combination
        total = (
            weights.get("cost", 0.5) * cost_score
            + weights.get("quality", 0.3) * quality_score
            + weights.get("speed", 0.2) * speed_score
        )

        return total

    def choose(
        self,
        task_description: str,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 500,
    ) -> RoutingDecision:
        """Choose the best model for a task.

        This is the main entry point for the router.
        """
        complexity = self.classifier.classify(task_description)
        weights = self._get_routing_weights()

        # Score all models
        scored_models: list[tuple[float, ModelPricing]] = []
        for model in self.models.values():
            score = self._score_model(model, complexity, weights)
            if score > 0:
                scored_models.append((score, model))

        # Sort by score descending
        scored_models.sort(key=lambda x: x[0], reverse=True)

        if not scored_models:
            # Fallback: use cheapest model
            fallback = min(self.models.values(), key=lambda m: m.avg_price_per_1m)
            cheapest = fallback
            most_expensive = max(self.models.values(), key=lambda m: m.avg_price_per_1m)
            chosen = fallback
        else:
            chosen = scored_models[0][1]
            # Get cheapest and most expensive from viable models
            viable = [m for _, m in scored_models]
            cheapest = min(viable, key=lambda m: m.avg_price_per_1m)
            most_expensive = max(viable, key=lambda m: m.avg_price_per_1m)

        # Calculate costs
        estimated_cost = (
            (estimated_input_tokens / 1_000_000) * chosen.input_price_per_1m
            + (estimated_output_tokens / 1_000_000) * chosen.output_price_per_1m
        )

        # Calculate savings vs most expensive model
        expensive_cost = (
            (estimated_input_tokens / 1_000_000) * most_expensive.input_price_per_1m
            + (estimated_output_tokens / 1_000_000) * most_expensive.output_price_per_1m
        )
        savings = expensive_cost - estimated_cost

        return RoutingDecision(
            task_description=task_description,
            complexity=complexity,
            chosen_model=chosen,
            cheapest_model=cheapest,
            most_expensive_model=most_expensive,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost=estimated_cost,
            potential_savings=max(0, savings),
        )

    def list_models(self, complexity: Optional[TaskComplexity] = None) -> list[ModelPricing]:
        """List available models, optionally filtered by complexity."""
        models = list(self.models.values())
        if complexity:
            models = [m for m in models if complexity in m.complexity_tiers]
        return sorted(models, key=lambda m: m.avg_price_per_1m)

    def get_cheapest(self, complexity: TaskComplexity) -> Optional[ModelPricing]:
        """Get the cheapest model for a complexity level."""
        viable = [
            m for m in self.models.values()
            if complexity in m.complexity_tiers
            and m.quality_score >= self._get_min_quality(complexity)
        ]
        if not viable:
            return None
        return min(viable, key=lambda m: m.avg_price_per_1m)

    def get_best(self, complexity: TaskComplexity) -> Optional[ModelPricing]:
        """Get the highest quality model for a complexity level."""
        viable = [
            m for m in self.models.values()
            if complexity in m.complexity_tiers
        ]
        if not viable:
            return None
        return max(viable, key=lambda m: m.quality_score)
