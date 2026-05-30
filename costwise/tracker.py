"""Usage and cost tracking with SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import get_db_path, get_config_dir
from .models import CostSummary, UsageRecord


class UsageTracker:
    """Tracks API usage and costs in SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        get_config_dir()  # ensure directory exists
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    task_type TEXT DEFAULT '',
                    complexity TEXT DEFAULT '',
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    input_cost REAL DEFAULT 0.0,
                    output_cost REAL DEFAULT 0.0,
                    total_cost REAL DEFAULT 0.0,
                    latency_ms REAL DEFAULT 0.0,
                    task_description TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp
                ON usage(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_model
                ON usage(model_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_provider
                ON usage(provider)
            """)
            conn.commit()

    def record_usage(self, record: UsageRecord) -> int:
        """Record a usage entry. Returns the record ID."""
        if record.timestamp is None:
            record.timestamp = datetime.now()

        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO usage (
                    timestamp, model_id, provider, task_type, complexity,
                    input_tokens, output_tokens, input_cost, output_cost,
                    total_cost, latency_ms, task_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp.isoformat(),
                record.model_id,
                record.provider,
                record.task_type,
                record.complexity,
                record.input_tokens,
                record.output_tokens,
                record.input_cost,
                record.output_cost,
                record.total_cost,
                record.latency_ms,
                record.task_description,
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def calculate_cost(
        self,
        model_pricing: object,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[float, float, float]:
        """Calculate cost for given token counts.

        Returns (input_cost, output_cost, total_cost).
        """
        input_cost = (input_tokens / 1_000_000) * model_pricing.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * model_pricing.output_price_per_1m
        return input_cost, output_cost, input_cost + output_cost

    def get_summary(
        self,
        period: str = "month",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """Get cost summary for a time period.

        Period can be: 'day', 'week', 'month', 'year', 'all', or 'custom'.
        """
        if start_date is None:
            now = datetime.now()
            if period == "day":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_date = now - timedelta(days=7)
            elif period == "month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == "year":
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:  # 'all'
                start_date = datetime(2020, 1, 1)

        if end_date is None:
            end_date = datetime.now()

        summary = CostSummary()

        with self._get_conn() as conn:
            # Total costs
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(total_cost), 0) as total_cost
                FROM usage
                WHERE timestamp >= ? AND timestamp <= ?
            """, (start_date.isoformat(), end_date.isoformat())).fetchone()

            if row:
                summary.total_requests = row["total_requests"]
                summary.total_input_tokens = row["total_input_tokens"]
                summary.total_output_tokens = row["total_output_tokens"]
                summary.total_cost = row["total_cost"]

            # By model
            rows = conn.execute("""
                SELECT model_id, SUM(total_cost) as cost
                FROM usage
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY model_id
                ORDER BY cost DESC
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()

            for row in rows:
                summary.by_model[row["model_id"]] = row["cost"]

            # By provider
            rows = conn.execute("""
                SELECT provider, SUM(total_cost) as cost
                FROM usage
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY provider
                ORDER BY cost DESC
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()

            for row in rows:
                summary.by_provider[row["provider"]] = row["cost"]

            # By complexity
            rows = conn.execute("""
                SELECT complexity, SUM(total_cost) as cost
                FROM usage
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY complexity
                ORDER BY cost DESC
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()

            for row in rows:
                summary.by_complexity[row["complexity"]] = row["cost"]

            # Daily costs
            rows = conn.execute("""
                SELECT DATE(timestamp) as day, SUM(total_cost) as cost
                FROM usage
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY DATE(timestamp)
                ORDER BY day
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()

            for row in rows:
                summary.daily_costs[row["day"]] = row["cost"]

        return summary

    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific day."""
        if date is None:
            date = datetime.now()
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(total_cost), 0) as total
                FROM usage
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat())).fetchone()
            return row["total"] if row else 0.0

    def get_monthly_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for the current month."""
        if date is None:
            date = datetime.now()
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if date.month == 12:
            end = start.replace(year=date.year + 1, month=1)
        else:
            end = start.replace(month=date.month + 1)

        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(total_cost), 0) as total
                FROM usage
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat())).fetchone()
            return row["total"] if row else 0.0

    def get_recent_records(self, limit: int = 50) -> list[UsageRecord]:
        """Get recent usage records."""
        records = []
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM usage
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()

            for row in rows:
                records.append(UsageRecord(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    model_id=row["model_id"],
                    provider=row["provider"],
                    task_type=row["task_type"],
                    complexity=row["complexity"],
                    input_tokens=row["input_tokens"],
                    output_tokens=row["output_tokens"],
                    input_cost=row["input_cost"],
                    output_cost=row["output_cost"],
                    total_cost=row["total_cost"],
                    latency_ms=row["latency_ms"],
                    task_description=row["task_description"],
                ))
        return records
