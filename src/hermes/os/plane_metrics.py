"""
Performance Metrics Collector for the 20-plane cognitive architecture.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class PlaneMetric:
    """Metrics for a single plane."""

    plane_name: str
    total_invocations: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    last_executed: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.total_latency_ms / self.total_invocations

    @property
    def avg_tokens(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.total_tokens / self.total_invocations

    @property
    def avg_cost(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.total_cost / self.total_invocations

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> dict:
        return {
            "plane_name": self.plane_name,
            "total_invocations": self.total_invocations,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_tokens": self.avg_tokens,
            "avg_cost": self.avg_cost,
            "cache_hit_rate": self.cache_hit_rate,
            "errors": self.errors,
            "last_executed": self.last_executed,
        }


class MetricsCollector:
    """Collects and queries performance metrics."""

    def __init__(self, db_path: Optional[Path] = None, workspace_root: str = "."):
        if db_path is not None:
            self._db_path = db_path
        else:
            store = Path(workspace_root) / ".hermes"
            store.mkdir(parents=True, exist_ok=True)
            self._db_path = store / "plane_metrics.sqlite"
        self._lock = threading.RLock()
        self._init_db()

    @classmethod
    def for_workspace(cls, workspace_root: str = ".") -> "MetricsCollector":
        return cls(workspace_root=workspace_root)

    def _init_db(self) -> None:
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plane_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id TEXT,
                    plane_name TEXT,
                    tokens_used INTEGER,
                    cost REAL,
                    latency_ms REAL,
                    cached BOOLEAN,
                    timestamp REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_metrics (
                    query_id TEXT PRIMARY KEY,
                    total_tokens INTEGER,
                    total_cost REAL,
                    total_latency_ms REAL,
                    planes_executed INTEGER,
                    planes_skipped INTEGER,
                    status TEXT,
                    timestamp REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_plane_name ON plane_metrics(plane_name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_status ON query_metrics(status)
            """)
            conn.commit()

    def record_plane(
        self,
        query_id: str,
        plane_name: str,
        tokens_used: int,
        cost: float,
        latency_ms: float,
        cached: bool = False,
        error: bool = False,
    ) -> None:
        """Record a plane execution."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute(
                        """INSERT INTO plane_metrics
                           (query_id, plane_name, tokens_used, cost, latency_ms, cached)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (query_id, plane_name, tokens_used, cost, latency_ms, cached),
                    )
                    conn.commit()
            except Exception:
                pass

    def record_query(
        self,
        query_id: str,
        total_tokens: int,
        total_cost: float,
        total_latency_ms: float,
        planes_executed: int,
        planes_skipped: int,
        status: str,
    ) -> None:
        """Record query completion."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO query_metrics
                           (query_id, total_tokens, total_cost, total_latency_ms,
                            planes_executed, planes_skipped, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            query_id,
                            total_tokens,
                            total_cost,
                            total_latency_ms,
                            planes_executed,
                            planes_skipped,
                            status,
                        ),
                    )
                    conn.commit()
            except Exception:
                pass

    def get_plane_latency(self, plane_name: str) -> dict[str, float]:
        """Get latency percentiles for a plane."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    rows = conn.execute(
                        "SELECT latency_ms FROM plane_metrics WHERE plane_name = ? ORDER BY latency_ms",
                        (plane_name,),
                    ).fetchall()

                if not rows:
                    return {"p50": 0, "p95": 0, "p99": 0, "count": 0}

                latencies = [r[0] for r in rows]
                n = len(latencies)
                return {
                    "p50": latencies[min(int(n * 0.5), n - 1)],
                    "p95": latencies[min(int(n * 0.95), n - 1)],
                    "p99": latencies[min(int(n * 0.99), n - 1)],
                    "count": n,
                }
            except Exception:
                return {"p50": 0, "p95": 0, "p99": 0, "count": 0}

    def get_plane_tokens(self, plane_name: str) -> dict[str, Any]:
        """Get token usage stats for a plane."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT SUM(tokens_used), AVG(tokens_used), COUNT(*) FROM plane_metrics WHERE plane_name = ?",
                        (plane_name,),
                    ).fetchone()

                return {
                    "total_tokens": row[0] or 0,
                    "avg_tokens": row[1] or 0,
                    "invocations": row[2] or 0,
                }
            except Exception:
                return {"total_tokens": 0, "avg_tokens": 0, "invocations": 0}

    def get_query_costs(self) -> dict[str, float]:
        """Get cost statistics across all queries."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT AVG(total_cost), SUM(total_cost), COUNT(*) FROM query_metrics"
                    ).fetchone()

                return {
                    "avg_cost_per_query": row[0] or 0,
                    "total_cost": row[1] or 0,
                    "total_queries": row[2] or 0,
                }
            except Exception:
                return {"avg_cost_per_query": 0, "total_cost": 0, "total_queries": 0}

    def get_cache_hit_rate(self) -> float:
        """Get overall cache hit rate."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT SUM(CASE WHEN cached THEN 1 ELSE 0 END), COUNT(*) FROM plane_metrics"
                    ).fetchone()

                if not row or not row[1]:
                    return 0.0
                return (row[0] or 0) / row[1]
            except Exception:
                return 0.0

    def get_plane_invocations(self) -> dict[str, int]:
        """Get invocation frequency per plane."""
        import sqlite3

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    rows = conn.execute(
                        "SELECT plane_name, COUNT(*) FROM plane_metrics GROUP BY plane_name"
                    ).fetchall()

                return {row[0]: row[1] for row in rows}
            except Exception:
                return {}

    def get_all_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        return {
            "query_cost": self.get_query_costs(),
            "cache_hit_rate": self.get_cache_hit_rate(),
            "plane_invocations": self.get_plane_invocations(),
        }

    def get_plane_summary(self, plane_name: str) -> dict[str, Any]:
        """Get summary for a specific plane."""
        latency = self.get_plane_latency(plane_name)
        tokens = self.get_plane_tokens(plane_name)
        return {
            "plane_name": plane_name,
            "latency": latency,
            "tokens": tokens,
        }

    def get_health_metrics(self) -> dict[str, Any]:
        """Get metrics formatted for health endpoint."""
        costs = self.get_query_costs()
        cache_rate = self.get_cache_hit_rate()
        invocations = self.get_plane_invocations()

        return {
            "timestamp": datetime.now().isoformat(),
            "total_queries": costs["total_queries"],
            "total_cost": costs["total_cost"],
            "avg_cost_per_query": costs["avg_cost_per_query"],
            "cache_hit_rate": cache_rate,
            "plane_invocations": invocations,
            "status": "healthy" if costs["total_queries"] > 0 else "no_data",
        }
