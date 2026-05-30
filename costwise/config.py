"""Configuration management for CostWise."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .models import BudgetConfig, ModelPricing, Provider, TaskComplexity

# Package paths
PACKAGE_DIR = Path(__file__).parent.parent
CONFIG_DIR = PACKAGE_DIR / "config"
USER_CONFIG_DIR = Path.home() / ".costwise"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"
DEFAULT_DB_PATH = USER_CONFIG_DIR / "usage.db"


def get_config_dir() -> Path:
    """Get the user config directory, creating it if needed."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return USER_CONFIG_DIR


def get_db_path() -> Path:
    """Get the database path."""
    return DEFAULT_DB_PATH


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_pricing() -> dict[str, ModelPricing]:
    """Load model pricing data from pricing.yaml."""
    pricing_path = CONFIG_DIR / "pricing.yaml"
    data = load_yaml(pricing_path)
    models: dict[str, ModelPricing] = {}

    for provider_key, provider_data in data.get("providers", {}).items():
        try:
            provider = Provider(provider_key)
        except ValueError:
            continue

        for model_id, model_data in provider_data.get("models", {}).items():
            complexity_tiers = []
            for tier_str in model_data.get("complexity_tiers", []):
                try:
                    complexity_tiers.append(TaskComplexity(tier_str))
                except ValueError:
                    pass

            models[model_id] = ModelPricing(
                model_id=model_id,
                display_name=model_data.get("display_name", model_id),
                provider=provider,
                input_price_per_1m=model_data.get("input_price", 0),
                output_price_per_1m=model_data.get("output_price", 0),
                max_context=model_data.get("max_context", 0),
                quality_score=model_data.get("quality_score", 50),
                speed_score=model_data.get("speed_score", 50),
                complexity_tiers=complexity_tiers,
            )

    return models


def load_default_config() -> dict[str, Any]:
    """Load default configuration."""
    default_path = CONFIG_DIR / "default.yaml"
    return load_yaml(default_path)


def load_user_config() -> dict[str, Any]:
    """Load user configuration (overrides defaults)."""
    if USER_CONFIG_FILE.exists():
        return load_yaml(USER_CONFIG_FILE)
    return {}


def get_config() -> dict[str, Any]:
    """Get merged configuration (defaults + user overrides)."""
    config = load_default_config()
    user_config = load_user_config()

    # Deep merge user config into defaults
    for key, value in user_config.items():
        if isinstance(value, dict) and key in config and isinstance(config[key], dict):
            config[key].update(value)
        else:
            config[key] = value

    return config


def get_budget_config() -> BudgetConfig:
    """Get budget configuration."""
    config = get_config()
    budget = config.get("budget", {})
    return BudgetConfig(
        monthly_limit=budget.get("monthly_limit", 0),
        daily_limit=budget.get("daily_limit", 0),
        alert_thresholds=budget.get("alert_thresholds", [0.5, 0.75, 0.9]),
        enabled=budget.get("alerts_enabled", True),
    )


def save_user_config(config: dict[str, Any]) -> None:
    """Save user configuration."""
    get_config_dir()
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def init_config() -> Path:
    """Initialize user configuration directory and default config."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    if not USER_CONFIG_FILE.exists():
        save_user_config(load_default_config())

    return config_dir
