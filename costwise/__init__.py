"""CostWise - AI cost optimizer with smart model routing.

Cut your AI API costs by 50-80% by intelligently routing tasks
to the cheapest capable model.

Usage as a library:
    from costwise import Router

    router = Router()
    decision = router.choose("summarize this text")
    print(decision.chosen_model.display_name)
    print(f"Estimated cost: ${decision.estimated_cost:.4f}")

Usage as CLI:
    costwise dashboard
    costwise budget set 50
    costwise optimize
"""

from .classifier import TaskClassifier
from .config import get_config, init_config, load_pricing
from .models import (
    BudgetConfig,
    CostSummary,
    ModelPricing,
    Provider,
    RoutingDecision,
    TaskComplexity,
    UsageRecord,
)
from .optimizer import CostOptimizer
from .router import ModelRouter as Router
from .tracker import UsageTracker
from .alerter import BudgetAlerter

__version__ = "0.1.0"

__all__ = [
    "Router",
    "TaskClassifier",
    "UsageTracker",
    "CostOptimizer",
    "BudgetAlerter",
    "TaskComplexity",
    "Provider",
    "ModelPricing",
    "UsageRecord",
    "BudgetConfig",
    "CostSummary",
    "RoutingDecision",
    "get_config",
    "init_config",
    "load_pricing",
]
