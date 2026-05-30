"""Data models for CostWise."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class Provider(Enum):
    """AI model providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    GOOGLE = "google"


@dataclass
class ModelPricing:
    """Pricing information for an AI model."""
    model_id: str
    display_name: str
    provider: Provider
    input_price_per_1m: float   # USD per 1M input tokens
    output_price_per_1m: float  # USD per 1M output tokens
    max_context: int            # max context window in tokens
    quality_score: float        # 0-100 quality rating
    speed_score: float          # 0-100 speed rating
    complexity_tiers: list[TaskComplexity] = field(default_factory=list)

    @property
    def avg_price_per_1m(self) -> float:
        """Average price per 1M tokens (input + output / 2)."""
        return (self.input_price_per_1m + self.output_price_per_1m) / 2


@dataclass
class UsageRecord:
    """A single API usage record."""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    model_id: str = ""
    provider: str = ""
    task_type: str = ""
    complexity: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    latency_ms: float = 0.0
    task_description: str = ""


@dataclass
class BudgetConfig:
    """Budget configuration."""
    monthly_limit: float = 0.0
    daily_limit: float = 0.0
    alert_thresholds: list[float] = field(default_factory=lambda: [0.5, 0.75, 0.9])
    enabled: bool = True


@dataclass
class RoutingDecision:
    """Record of a routing decision."""
    task_description: str
    complexity: TaskComplexity
    chosen_model: ModelPricing
    cheapest_model: ModelPricing
    most_expensive_model: ModelPricing
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    potential_savings: float


@dataclass
class CostSummary:
    """Cost summary for a time period."""
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    by_model: dict[str, float] = field(default_factory=dict)
    by_provider: dict[str, float] = field(default_factory=dict)
    by_complexity: dict[str, float] = field(default_factory=dict)
    daily_costs: dict[str, float] = field(default_factory=dict)
