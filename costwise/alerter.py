"""Budget alerts system."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .config import get_budget_config
from .models import BudgetConfig
from .tracker import UsageTracker


class BudgetAlerter:
    """Monitors spending and triggers budget alerts."""

    def __init__(self, tracker: Optional[UsageTracker] = None) -> None:
        self.tracker = tracker or UsageTracker()
        self.config = get_budget_config()

    def check_budget(self) -> dict:
        """Check current budget status.

        Returns a dict with budget info and any triggered alerts.
        """
        result = {
            "monthly_limit": self.config.monthly_limit,
            "daily_limit": self.config.daily_limit,
            "monthly_spent": 0.0,
            "daily_spent": 0.0,
            "monthly_remaining": 0.0,
            "daily_remaining": 0.0,
            "monthly_percent": 0.0,
            "daily_percent": 0.0,
            "alerts": [],
            "status": "ok",
        }

        # Get current spending
        result["monthly_spent"] = self.tracker.get_monthly_cost()
        result["daily_spent"] = self.tracker.get_daily_cost()

        # Calculate remaining and percentages
        if self.config.monthly_limit > 0:
            result["monthly_remaining"] = max(0, self.config.monthly_limit - result["monthly_spent"])
            result["monthly_percent"] = result["monthly_spent"] / self.config.monthly_limit

        if self.config.daily_limit > 0:
            result["daily_remaining"] = max(0, self.config.daily_limit - result["daily_spent"])
            result["daily_percent"] = result["daily_spent"] / self.config.daily_limit

        # Check thresholds
        if self.config.enabled:
            # Monthly alerts
            if self.config.monthly_limit > 0:
                for threshold in self.config.alert_thresholds:
                    if result["monthly_percent"] >= threshold:
                        result["alerts"].append({
                            "type": "monthly",
                            "threshold": threshold,
                            "spent": result["monthly_spent"],
                            "limit": self.config.monthly_limit,
                            "message": (
                                f"Monthly budget at {result['monthly_percent']:.0%}: "
                                f"${result['monthly_spent']:.2f} / ${self.config.monthly_limit:.2f}"
                            ),
                        })

            # Daily alerts
            if self.config.daily_limit > 0:
                for threshold in self.config.alert_thresholds:
                    if result["daily_percent"] >= threshold:
                        result["alerts"].append({
                            "type": "daily",
                            "threshold": threshold,
                            "spent": result["daily_spent"],
                            "limit": self.config.daily_limit,
                            "message": (
                                f"Daily budget at {result['daily_percent']:.0%}: "
                                f"${result['daily_spent']:.2f} / ${self.config.daily_limit:.2f}"
                            ),
                        })

        # Set overall status
        if result["monthly_percent"] >= 1.0 or result["daily_percent"] >= 1.0:
            result["status"] = "exceeded"
        elif result["alerts"]:
            result["status"] = "warning"

        return result

    def would_exceed_budget(
        self,
        estimated_cost: float,
    ) -> dict:
        """Check if an additional cost would exceed the budget.

        Returns dict with exceed info.
        """
        monthly_spent = self.tracker.get_monthly_cost()
        daily_spent = self.tracker.get_daily_cost()

        result = {
            "would_exceed_monthly": False,
            "would_exceed_daily": False,
            "monthly_after": monthly_spent + estimated_cost,
            "daily_after": daily_spent + estimated_cost,
        }

        if self.config.monthly_limit > 0:
            result["would_exceed_monthly"] = (
                monthly_spent + estimated_cost > self.config.monthly_limit
            )

        if self.config.daily_limit > 0:
            result["would_exceed_daily"] = (
                daily_spent + estimated_cost > self.config.daily_limit
            )

        return result
