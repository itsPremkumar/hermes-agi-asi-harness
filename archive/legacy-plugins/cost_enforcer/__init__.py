"""
Cost Budget Enforcer & Performance Optimization Layer
for the 20-plane cognitive architecture.

Provides budget enforcement, cost tracking, performance optimization,
and comprehensive metrics collection.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import statistics
import tempfile
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class CostConfig:
    """Configuration for cost budget enforcement."""
    max_tokens_per_query: int = 10_000
    max_wall_clock_seconds: float = 30.0
    max_cost_per_query: float = 0.50
    cost_per_1k_tokens: float = 0.003  # Average cost per 1K tokens
    cache_ttl_seconds: float = 300.0
    cache_max_entries: int = 10_000
    min_planes_per_query: int = 3
    max_planes_per_query: int = 7
    budget_warning_threshold: float = 0.8
    enable_parallel_execution: bool = True
    enable_adaptive_selection: bool = True
    enable_caching: bool = True


# ============================================================================
# Budget Tracker
# ============================================================================

@dataclass
class PlaneBudget:
    """Budget allocation for a single plane."""
    plane_name: str
    token_budget: int
    tokens_used: int = 0
    cost_incurred: float = 0.0
    invocations: int = 0
    avg_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.token_budget - self.tokens_used)

    @property
    def budget_utilization(self) -> float:
        if self.token_budget == 0:
            return 1.0
        return self.tokens_used / self.token_budget

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


@dataclass
class QueryBudget:
    """Budget for a single query across all planes."""
    query_id: str
    total_token_budget: int
    total_cost_budget: float
    start_time: float
    max_wall_clock: float
    plane_budgets: dict[str, PlaneBudget] = field(default_factory=dict)
    status: str = "active"  # active, completed, budget_exceeded, timeout
    total_tokens_used: int = 0
    total_cost: float = 0.0
    planes_executed: list[str] = field(default_factory=list)
    planes_skipped: list[str] = field(default_factory=list)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.total_token_budget - self.total_tokens_used)

    @property
    def remaining_cost(self) -> float:
        return max(0.0, self.total_cost_budget - self.total_cost)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def is_expired(self) -> bool:
        return self.elapsed_seconds >= self.max_wall_clock

    @property
    def budget_exceeded(self) -> bool:
        return (self.total_tokens_used >= self.total_token_budget or
                self.total_cost >= self.total_cost_budget)

    def get_affordable_planes(self, plane_costs: dict[str, int]) -> list[str]:
        """Determine which planes can be executed within remaining budget."""
        affordable = []
        for plane_name, estimated_cost in plane_costs.items():
            if (self.remaining_tokens >= estimated_cost and
                self.remaining_cost >= estimated_cost * 0.003 / 1000):
                affordable.append(plane_name)
        return affordable


# ============================================================================
# Cost Enforcer
# ============================================================================

class CostEnforcer:
    """Enforces cost budgets across planes and queries."""

    def __init__(self, config: Optional[CostConfig] = None):
        self.config = config or CostConfig()
        self._active_queries: dict[str, QueryBudget] = {}
        self._lock = threading.RLock()

    def create_query_budget(
        self,
        plane_names: list[str],
        token_budget: Optional[int] = None,
        cost_budget: Optional[float] = None,
        wall_clock: Optional[float] = None,
    ) -> QueryBudget:
        """Create a new budget for a query."""
        with self._lock:
            query_id = str(uuid.uuid4().hex[:12])
            total_tokens = token_budget or self.config.max_tokens_per_query
            total_cost = cost_budget or self.config.max_cost_per_query
            max_clock = wall_clock or self.config.max_wall_clock_seconds

            # Allocate per-plane budget (distribute evenly with priority weighting)
            per_plane_tokens = total_tokens // max(len(plane_names), 1)
            plane_budgets = {}
            for name in plane_names:
                plane_budgets[name] = PlaneBudget(
                    plane_name=name,
                    token_budget=per_plane_tokens,
                )

            query = QueryBudget(
                query_id=query_id,
                total_token_budget=total_tokens,
                total_cost_budget=total_cost,
                start_time=time.time(),
                max_wall_clock=max_clock,
                plane_budgets=plane_budgets,
            )
            self._active_queries[query_id] = query
            return query

    def record_usage(
        self,
        query_id: str,
        plane_name: str,
        tokens_used: int,
        cost: float,
        latency_ms: float,
        cached: bool = False,
    ) -> bool:
        """Record usage for a plane. Returns False if budget exceeded."""
        with self._lock:
            query = self._active_queries.get(query_id)
            if not query:
                return False

            if query.status != "active":
                return False

            # Check time budget
            if query.is_expired:
                query.status = "timeout"
                return False

            # Update plane budget
            plane = query.plane_budgets.get(plane_name)
            if plane:
                plane.tokens_used += tokens_used
                plane.cost_incurred += cost
                plane.invocations += 1
                plane.total_latency_ms += latency_ms
                plane.avg_latency_ms = plane.total_latency_ms / plane.invocations
                if cached:
                    plane.cache_hits += 1
                else:
                    plane.cache_misses += 1

            # Update totals
            query.total_tokens_used += tokens_used
            query.total_cost += cost
            if plane_name not in query.planes_executed:
                query.planes_executed.append(plane_name)

            # Check budget exhaustion
            if query.budget_exceeded:
                query.status = "budget_exceeded"
                return False

            return True

    def check_budget(self, query_id: str, plane_name: str, estimated_tokens: int) -> bool:
        """Check if a plane can be executed within remaining budget."""
        with self._lock:
            query = self._active_queries.get(query_id)
            if not query:
                return False

            if query.status != "active":
                return False

            if query.is_expired:
                return False

            if query.remaining_tokens < estimated_tokens:
                return False

            estimated_cost = estimated_tokens * self.config.cost_per_1k_tokens / 1000
            if query.remaining_cost < estimated_cost:
                return False

            return True

    def get_affordable_planes(
        self, query_id: str, plane_costs: dict[str, int],
    ) -> list[str]:
        """Get list of planes that can be executed within budget."""
        with self._lock:
            query = self._active_queries.get(query_id)
            if not query:
                return []
            return query.get_affordable_planes(plane_costs)

    def get_lowest_cost_planes(
        self, query_id: str, plane_costs: dict[str, int], max_planes: int,
    ) -> list[str]:
        """Select the lowest cost planes within budget."""
        affordable = self.get_affordable_planes(query_id, plane_costs)
        # Sort by estimated cost (ascending)
        affordable.sort(key=lambda p: plane_costs.get(p, float('inf')))
        return affordable[:max_planes]

    def complete_query(self, query_id: str) -> Optional[QueryBudget]:
        """Mark a query as completed."""
        with self._lock:
            query = self._active_queries.get(query_id)
            if query and query.status == "active":
                query.status = "completed"
            return query

    def get_query(self, query_id: str) -> Optional[QueryBudget]:
        """Get query budget by ID."""
        return self._active_queries.get(query_id)

    def cleanup_expired(self) -> int:
        """Remove expired queries. Returns count removed."""
        with self._lock:
            expired = [
                qid for qid, q in self._active_queries.items()
                if q.is_expired or q.status in ("completed", "budget_exceeded", "timeout")
            ]
            for qid in expired:
                del self._active_queries[qid]
            return len(expired)

    def get_global_stats(self) -> dict[str, Any]:
        """Get global statistics across all queries."""
        with self._lock:
            total_queries = len(self._active_queries)
            active = sum(1 for q in self._active_queries.values() if q.status == "active")
            completed = sum(1 for q in self._active_queries.values() if q.status == "completed")
            exceeded = sum(1 for q in self._active_queries.values() if q.status == "budget_exceeded")
            timed_out = sum(1 for q in self._active_queries.values() if q.status == "timeout")
            total_tokens = sum(q.total_tokens_used for q in self._active_queries.values())
            total_cost = sum(q.total_cost for q in self._active_queries.values())

            return {
                "total_queries": total_queries,
                "active": active,
                "completed": completed,
                "budget_exceeded": exceeded,
                "timed_out": timed_out,
                "total_tokens_used": total_tokens,
                "total_cost": total_cost,
                "avg_tokens_per_query": total_tokens / total_queries if total_queries else 0,
                "avg_cost_per_query": total_cost / total_queries if total_queries else 0,
            }


# ============================================================================
# Semantic Cache
# ============================================================================

class SemanticCache:
    """SQLite-backed semantic cache for plane results."""

    def __init__(self, config: CostConfig):
        self.config = config
        self._lock = threading.RLock()
        self._db_path = self._get_db_path()
        self._init_db()

    def _get_db_path(self) -> Path:
        cache_dir = Path(tempfile.gettempdir()) / "hermes_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "semantic_cache.db"

    def _init_db(self) -> None:
        import sqlite3
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    result BLOB,
                    tokens_used INTEGER,
                    created_at REAL,
                    last_accessed REAL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON cache(created_at)
            """)
            conn.commit()

    def _make_key(self, plane_name: str, input_hash: str) -> str:
        return hashlib.sha256(f"{plane_name}:{input_hash}".encode()).hexdigest()

    def get(self, plane_name: str, input_data: Any) -> Optional[Any]:
        """Retrieve cached result for a plane."""
        import sqlite3
        input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()
        key = self._make_key(plane_name, input_hash)

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT result, created_at FROM cache WHERE key = ?", (key,)
                    ).fetchone()

                    if row:
                        result_blob, created_at = row
                        # Check TTL
                        if time.time() - created_at < self.config.cache_ttl_seconds:
                            # Update access stats
                            conn.execute(
                                "UPDATE cache SET last_accessed = ?, access_count = access_count + 1 WHERE key = ?",
                                (time.time(), key),
                            )
                            conn.commit()
                            return json.loads(result_blob)
                        else:
                            # Expired
                            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                            conn.commit()
            except Exception:
                pass

        return None

    def put(self, plane_name: str, input_data: Any, result: Any, tokens_used: int) -> None:
        """Store result in cache."""
        import sqlite3
        input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()
        key = self._make_key(plane_name, input_hash)

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO cache
                           (key, result, tokens_used, created_at, last_accessed, access_count)
                           VALUES (?, ?, ?, ?, ?, 0)""",
                        (key, json.dumps(result), tokens_used, time.time(), time.time()),
                    )
                    conn.commit()
            except Exception:
                pass

    def cleanup(self) -> int:
        """Remove expired entries. Returns count removed."""
        import sqlite3
        cutoff = time.time() - self.config.cache_ttl_seconds
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute("DELETE FROM cache WHERE created_at < ?", (cutoff,))
                    conn.commit()
                    return cursor.rowcount
            except Exception:
                return 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        import sqlite3
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT COUNT(*), SUM(tokens_used) FROM cache"
                    ).fetchone()
                    return {
                        "entries": row[0] or 0,
                        "total_cached_tokens": row[1] or 0,
                    }
            except Exception:
                return {"entries": 0, "total_cached_tokens": 0}


# ============================================================================
# Performance Optimizer
# ============================================================================

class PerformanceOptimizer:
    """Optimizes plane execution with caching, memoization, and scheduling."""

    def __init__(self, config: CostConfig, enforcer: CostEnforcer):
        self.config = config
        self.enforcer = enforcer
        self.cache = SemanticCache(config) if config.enable_caching else None
        self._memo: dict[str, Any] = {}  # In-memory memoization
        self._lock = threading.RLock()

    def get_memo_key(self, plane_name: str, input_data: Any) -> str:
        input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()
        return f"{plane_name}:{input_hash}"

    def get_memoized(self, plane_name: str, input_data: Any) -> Optional[Any]:
        """Get memoized result for a plane."""
        key = self.get_memo_key(plane_name, input_data)
        with self._lock:
            return self._memo.get(key)

    def memoize(self, plane_name: str, input_data: Any, result: Any) -> None:
        """Store result in memoization cache."""
        key = self.get_memo_key(plane_name, input_data)
        with self._lock:
            self._memo[key] = result

    def get_cached(self, plane_name: str, input_data: Any) -> Optional[Any]:
        """Get cached result from semantic cache."""
        if self.cache:
            return self.cache.get(plane_name, input_data)
        return None

    def store_cached(self, plane_name: str, input_data: Any, result: Any, tokens_used: int) -> None:
        """Store result in semantic cache."""
        if self.cache:
            self.cache.put(plane_name, input_data, result, tokens_used)

    def select_planes_adaptive(
        self,
        query_id: str,
        plane_names: list[str],
        plane_costs: dict[str, int],
        plane_value_scores: dict[str, float],
    ) -> list[str]:
        """Select planes adaptively based on budget and value scores."""
        if not self.config.enable_adaptive_selection:
            return plane_names[: self.config.max_planes_per_query]

        query = self.enforcer.get_query(query_id)
        if not query:
            return []

        affordable = self.enforcer.get_affordable_planes(query_id, plane_costs)
        if not affordable:
            return []

        # Score planes by value/cost ratio
        scored = []
        for plane in affordable:
            cost = plane_costs.get(plane, 100)
            value = plane_value_scores.get(plane, 0.5)
            scored.append((plane, value / max(cost, 1)))

        # Sort by value/cost ratio (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Select top planes within count limits
        max_planes = min(self.config.max_planes_per_query, len(scored))
        min_planes = min(self.config.min_planes_per_query, max_planes)
        selected = [p[0] for p in scored[:max(max_planes, min_planes)]]

        return selected

    def get_parallel_groups(
        self, plane_names: list[str], dependencies: dict[str, list[str]],
    ) -> list[list[str]]:
        """Group independent planes for parallel execution."""
        if not self.config.enable_parallel_execution:
            return [[p] for p in plane_names]

        # Topological sort for dependency ordering
        visited: set[str] = set()
        groups: list[list[str]] = []

        def visit(plane: str, path: set[str]) -> None:
            if plane in visited:
                return
            if plane in path:
                return  # Circular dependency
            path.add(plane)
            for dep in dependencies.get(plane, []):
                visit(dep, path)
            path.discard(plane)
            visited.add(plane)
            # Add to current group or create new
            if not groups:
                groups.append([])
            groups[-1].append(plane)

        for plane in plane_names:
            visit(plane, set())

        return groups


# ============================================================================
# Metrics Collector
# ============================================================================

class MetricsCollector:
    """Collects performance metrics for planes and queries."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or Path(tempfile.gettempdir()) / "hermes_metrics.db"
        self._lock = threading.RLock()
        self._init_db()

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
            conn.commit()

    def record_plane_execution(
        self,
        query_id: str,
        plane_name: str,
        tokens_used: int,
        cost: float,
        latency_ms: float,
        cached: bool = False,
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

    def record_query_completion(
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
                        (query_id, total_tokens, total_cost, total_latency_ms,
                         planes_executed, planes_skipped, status),
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
                    "p50": latencies[int(n * 0.5)],
                    "p95": latencies[int(n * 0.95)],
                    "p99": latencies[int(n * 0.99)],
                    "count": n,
                }
            except Exception:
                return {"p50": 0, "p95": 0, "p99": 0, "count": 0}

    def get_plane_token_usage(self, plane_name: str) -> dict[str, Any]:
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

    def get_query_cost_stats(self) -> dict[str, float]:
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

    def get_plane_invocation_frequency(self) -> dict[str, int]:
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
            "query_cost": self.get_query_cost_stats(),
            "cache_hit_rate": self.get_cache_hit_rate(),
            "plane_invocations": self.get_plane_invocation_frequency(),
        }


# ============================================================================
# Plugin Interface
# ============================================================================

class CostEnforcerPlugin:
    """Main plugin interface for the cost enforcement system."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        cfg_dict = config or {}
        self.config = CostConfig(
            max_tokens_per_query=cfg_dict.get("max_tokens_per_query", 10_000),
            max_wall_clock_seconds=cfg_dict.get("max_wall_clock_seconds", 30.0),
            max_cost_per_query=cfg_dict.get("max_cost_per_query", 0.50),
            cost_per_1k_tokens=cfg_dict.get("cost_per_1k_tokens", 0.003),
            cache_ttl_seconds=cfg_dict.get("cache_ttl_seconds", 300.0),
            min_planes_per_query=cfg_dict.get("min_planes_per_query", 3),
            max_planes_per_query=cfg_dict.get("max_planes_per_query", 7),
            enable_parallel_execution=cfg_dict.get("enable_parallel_execution", True),
            enable_adaptive_selection=cfg_dict.get("enable_adaptive_selection", True),
            enable_caching=cfg_dict.get("enable_caching", True),
        )
        self.enforcer = CostEnforcer(self.config)
        self.optimizer = PerformanceOptimizer(self.config, self.enforcer)
        self.metrics = MetricsCollector()

    def start_query(
        self, plane_names: list[str], **kwargs,
    ) -> QueryBudget:
        """Start a new query with budget tracking."""
        return self.enforcer.create_query_budget(plane_names, **kwargs)

    def record(
        self, query_id: str, plane_name: str, tokens: int, cost: float,
        latency_ms: float, cached: bool = False,
    ) -> bool:
        """Record plane execution."""
        # Record in enforcer
        ok = self.enforcer.record_usage(query_id, plane_name, tokens, cost, latency_ms, cached)
        # Record in metrics
        self.metrics.record_plane_execution(query_id, plane_name, tokens, cost, latency_ms, cached)
        return ok

    def select_planes(
        self, query_id: str, plane_costs: dict[str, int], plane_values: dict[str, float],
    ) -> list[str]:
        """Select planes to execute."""
        return self.optimizer.select_planes_adaptive(
            query_id, list(plane_costs.keys()), plane_costs, plane_values,
        )

    def get_cached(self, plane_name: str, input_data: Any) -> Optional[Any]:
        """Get cached result."""
        return self.optimizer.get_cached(plane_name, input_data)

    def store_cached(self, plane_name: str, input_data: Any, result: Any, tokens: int) -> None:
        """Store result in cache."""
        self.optimizer.store_cached(plane_name, input_data, result, tokens)

    def finish_query(self, query_id: str) -> Optional[dict[str, Any]]:
        """Finish a query and return summary."""
        query = self.enforcer.complete_query(query_id)
        if not query:
            return None

        self.metrics.record_query_completion(
            query_id, query.total_tokens_used, query.total_cost,
            query.elapsed_seconds * 1000, len(query.planes_executed),
            len(query.planes_skipped), query.status,
        )

        return {
            "query_id": query_id,
            "status": query.status,
            "total_tokens": query.total_tokens_used,
            "total_cost": query.total_cost,
            "elapsed_ms": query.elapsed_seconds * 1000,
            "planes_executed": query.planes_executed,
            "planes_skipped": query.planes_skipped,
        }

    def health(self) -> dict[str, Any]:
        """Get health and metrics."""
        return {
            "enforcer": self.enforcer.get_global_stats(),
            "metrics": self.metrics.get_all_metrics(),
            "cache": self.optimizer.cache.get_stats() if self.optimizer.cache else {},
            "config": {
                "max_tokens": self.config.max_tokens_per_query,
                "max_cost": self.config.max_cost_per_query,
                "max_wall_clock": self.config.max_wall_clock_seconds,
            },
        }
