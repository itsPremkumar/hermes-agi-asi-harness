"""
Performance Optimizer for cost-efficient plane execution.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import tempfile
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class OptimizationResult:
    """Result of an optimization step."""
    plane_name: str
    should_execute: bool
    reason: str
    estimated_cost: float
    confidence: float = 1.0


class ResultCache:
    """SQLite-backed cache for plane results."""

    def __init__(self, max_entries: int = 10_000, ttl_seconds: float = 300.0,
                 db_path: Optional[Path] = None, workspace_root: str = "."):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._db_path = db_path or self._get_db_path(workspace_root)
        self._init_db()

    @staticmethod
    def _get_db_path(workspace_root: str = ".") -> Path:
        cache_dir = Path(workspace_root) / ".hermes" / "optimizer_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "cache.db"

    def _init_db(self) -> None:
        import sqlite3
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS result_cache (
                    key TEXT PRIMARY KEY,
                    result BLOB,
                    tokens_used INTEGER,
                    cost REAL,
                    created_at REAL,
                    last_accessed REAL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_created ON result_cache(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_accessed ON result_cache(last_accessed)
            """)
            conn.commit()

    @staticmethod
    def make_key(plane_name: str, input_data: Any) -> str:
        input_hash = hashlib.sha256(
            json.dumps(input_data, sort_keys=True).encode()
        ).hexdigest()
        return hashlib.sha256(f"{plane_name}:{input_hash}".encode()).hexdigest()

    def get(self, plane_name: str, input_data: Any) -> Optional[dict]:
        """Retrieve cached result."""
        import sqlite3
        key = self.make_key(plane_name, input_data)

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute(
                        "SELECT result, created_at FROM result_cache WHERE key = ?",
                        (key,),
                    ).fetchone()

                    if row:
                        result_blob, created_at = row
                        if time.time() - created_at < self.ttl_seconds:
                            conn.execute(
                                """UPDATE result_cache
                                   SET last_accessed = ?, access_count = access_count + 1
                                   WHERE key = ?""",
                                (time.time(), key),
                            )
                            conn.commit()
                            return json.loads(result_blob)
                        else:
                            conn.execute("DELETE FROM result_cache WHERE key = ?", (key,))
                            conn.commit()
            except Exception:
                pass

        return None

    def put(self, plane_name: str, input_data: Any, result: Any, tokens: int, cost: float) -> None:
        """Store result in cache."""
        import sqlite3
        key = self.make_key(plane_name, input_data)

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO result_cache
                           (key, result, tokens_used, cost, created_at, last_accessed, access_count)
                           VALUES (?, ?, ?, ?, ?, ?, 0)""",
                        (key, json.dumps(result), tokens, cost, time.time(), time.time()),
                    )
                    conn.commit()
            except Exception:
                pass

    def cleanup(self) -> int:
        """Remove expired entries."""
        import sqlite3
        cutoff = time.time() - self.ttl_seconds
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM result_cache WHERE created_at < ?", (cutoff,)
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception:
                return 0

    @property
    def size(self) -> int:
        import sqlite3
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    row = conn.execute("SELECT COUNT(*) FROM result_cache").fetchone()
                    return row[0] or 0
            except Exception:
                return 0


class MemoizationCache:
    """In-memory memoization for repeated plane executions."""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._cache: dict[str, Any] = {}
        self._access_order: list[str] = []
        self._lock = threading.RLock()

    @staticmethod
    def make_key(plane_name: str, input_data: Any) -> str:
        input_hash = hashlib.sha256(
            json.dumps(input_data, sort_keys=True).encode()
        ).hexdigest()
        return f"{plane_name}:{input_hash}"

    def get(self, plane_name: str, input_data: Any) -> Optional[Any]:
        key = self.make_key(plane_name, input_data)
        with self._lock:
            return self._cache.get(key)

    def put(self, plane_name: str, input_data: Any, result: Any) -> None:
        key = self.make_key(plane_name, input_data)
        with self._lock:
            if key not in self._cache and len(self._cache) >= self.max_entries:
                # Evict oldest
                if self._access_order:
                    oldest = self._access_order.pop(0)
                    self._cache.pop(oldest, None)
            self._cache[key] = result
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class ParallelScheduler:
    """Schedules independent planes for parallel execution."""

    @staticmethod
    def group_by_dependencies(
        plane_names: list[str],
        dependencies: dict[str, list[str]],
    ) -> list[list[str]]:
        """Group planes into execution waves based on dependencies."""
        visited: set[str] = set()
        groups: list[list[str]] = []

        def visit(plane: str, path: set[str]) -> None:
            if plane in visited:
                return
            if plane in path:
                return
            path.add(plane)
            for dep in dependencies.get(plane, []):
                visit(dep, path)
            path.discard(plane)
            visited.add(plane)
            groups.append([plane])

        for plane in plane_names:
            visit(plane, set())

        # Merge independent planes into same wave
        merged: list[list[str]] = []
        for group in groups:
            if not merged:
                merged.append([])
            merged[-1].extend(group)

        return merged

    @staticmethod
    def get_independent_planes(
        plane_names: list[str],
        dependencies: dict[str, list[str]],
    ) -> list[str]:
        """Get planes with no dependencies (can run in parallel)."""
        return [
            p for p in plane_names
            if not dependencies.get(p, [])
        ]


class AdaptivePlaneSelector:
    """Selects planes adaptively based on budget and value scores."""

    @staticmethod
    def should_skip_plane(
        plane_name: str,
        budget_remaining: float,
        plane_cost: float,
        plane_value: float,
        plane_cache_hit_rate: float = 0.0,
    ) -> tuple[bool, str]:
        """Determine if a plane should be skipped."""
        if plane_cost > budget_remaining:
            return True, f"Cost {plane_cost:.4f} exceeds remaining budget {budget_remaining:.4f}"

        if plane_value < 0.1:
            return True, "Plane value too low (< 0.1)"

        if plane_cache_hit_rate > 0.9:
            return True, f"Cache hit rate high ({plane_cache_hit_rate:.0%}), result unlikely to change"

        return False, "Plane should execute"

    @staticmethod
    def select_top_planes(
        plane_names: list[str],
        plane_costs: dict[str, int],
        plane_values: dict[str, float],
        max_planes: int,
        budget_remaining: float,
    ) -> list[OptimizationResult]:
        """Select top planes by value/cost ratio within budget."""
        results = []

        for plane in plane_names:
            cost = plane_costs.get(plane, 100)
            value = plane_values.get(plane, 0.5)
            cost_dollars = cost * 0.003 / 1000

            should_skip, reason = AdaptivePlaneSelector.should_skip_plane(
                plane, budget_remaining, cost_dollars, value,
            )

            results.append(OptimizationResult(
                plane_name=plane,
                should_execute=not should_skip,
                reason=reason,
                estimated_cost=cost_dollars,
                confidence=value,
            ))

        # Sort by value/cost ratio
        executable = [r for r in results if r.should_execute]
        executable.sort(
            key=lambda r: r.confidence / max(r.estimated_cost, 0.0001),
            reverse=True,
        )

        selected = executable[:max_planes]
        skipped = [r for r in results if not r.should_execute]

        return selected + skipped


class PerformanceOptimizer:
    """Main performance optimizer combining all optimization strategies."""

    def __init__(
        self,
        cache_max_entries: int = 10_000,
        cache_ttl: float = 300.0,
        memo_max_entries: int = 1000,
    ):
        self.result_cache = ResultCache(cache_max_entries, cache_ttl)
        self.memo_cache = MemoizationCache(memo_max_entries)
        self.scheduler = ParallelScheduler()
        self.plane_selector = AdaptivePlaneSelector()

    def check_cache(self, plane_name: str, input_data: Any) -> Optional[Any]:
        """Check all cache layers for a result."""
        # Check in-memory memo first (fastest)
        result = self.memo_cache.get(plane_name, input_data)
        if result is not None:
            return result

        # Check SQLite cache
        result = self.result_cache.get(plane_name, input_data)
        if result is not None:
            # Promote to memo
            self.memo_cache.put(plane_name, input_data, result)
            return result

        return None

    def store_result(
        self,
        plane_name: str,
        input_data: Any,
        result: Any,
        tokens_used: int,
        cost: float,
    ) -> None:
        """Store result in all cache layers."""
        self.memo_cache.put(plane_name, input_data, result)
        self.result_cache.put(plane_name, input_data, result, tokens_used, cost)

    def select_planes(
        self,
        plane_names: list[str],
        plane_costs: dict[str, int],
        plane_values: dict[str, float],
        budget_remaining: float,
        max_planes: int = 7,
    ) -> list[OptimizationResult]:
        """Select planes to execute."""
        return self.plane_selector.select_top_planes(
            plane_names, plane_costs, plane_values, max_planes, budget_remaining,
        )

    def get_parallel_groups(
        self,
        plane_names: list[str],
        dependencies: dict[str, list[str]],
    ) -> list[list[str]]:
        """Get execution groups for parallel scheduling."""
        return self.scheduler.group_by_dependencies(plane_names, dependencies)

    def cleanup(self) -> dict[str, int]:
        """Clean up expired cache entries."""
        return {
            "result_cache_removed": self.result_cache.cleanup(),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "result_cache_size": self.result_cache.size,
            "memo_cache_size": self.memo_cache.size,
        }
