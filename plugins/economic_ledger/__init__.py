"""
Economic Ledger Plugin — Resource Tracking & Budget Management

Tracks: tokens, CPU, RAM, GPU, API cost, cloud cost, time, storage,
agent capacity, tool usage. Mission budgets with token_limit, time_limit,
monetary_limit, compute_limit. Expected benefit/cost analysis.
"""

import time
import psutil
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import defaultdict


@dataclass
class ResourceUsage:
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    network_bytes: int = 0
    tokens_used: int = 0
    token_cost: float = 0.0
    api_calls: int = 0
    api_cost: float = 0.0
    agent_hours: float = 0.0
    tool_calls: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "network_bytes": self.network_bytes,
            "tokens_used": self.tokens_used,
            "token_cost": self.token_cost,
            "api_calls": self.api_calls,
            "api_cost": self.api_cost,
            "agent_hours": self.agent_hours,
            "tool_calls": self.tool_calls,
            "timestamp": self.timestamp,
        }


@dataclass
class MissionBudget:
    token_limit: int = 100000
    time_limit_seconds: int = 3600
    monetary_limit: float = 0.0
    compute_limit: float = 0.0  # CPU hours

    used_tokens: int = 0
    elapsed_seconds: float = 0
    spent_amount: float = 0.0
    used_compute: float = 0.0

    def remaining_tokens(self) -> int:
        return max(0, self.token_limit - self.used_tokens)

    def remaining_time(self) -> float:
        return max(0, self.time_limit_seconds - self.elapsed_seconds)

    def is_exhausted(self) -> bool:
        return (self.used_tokens >= self.token_limit or
                self.elapsed_seconds >= self.time_limit_seconds or
                (self.monetary_limit > 0 and self.spent_amount >= self.monetary_limit))

    def utilization(self) -> Dict[str, float]:
        return {
            "tokens": self.used_tokens / max(1, self.token_limit),
            "time": self.elapsed_seconds / max(1, self.time_limit_seconds),
            "money": self.spent_amount / max(0.001, self.monetary_limit) if self.monetary_limit > 0 else 0,
            "compute": self.used_compute / max(0.001, self.compute_limit) if self.compute_limit > 0 else 0,
        }


class EconomicLedger:
    """Track resource usage and enforce budgets."""

    def __init__(self):
        self._usage: List[ResourceUsage] = []
        self._budgets: Dict[str, MissionBudget] = {}
        self._total_cost: float = 0.0
        self._total_tokens: int = 0

    def snapshot(self) -> ResourceUsage:
        """Take a resource snapshot."""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()
        except Exception:
            cpu = 0.0
            mem = None
            disk = None
            net = None

        usage = ResourceUsage(
            cpu_percent=cpu,
            memory_mb=mem.used / 1024 / 1024 if mem else 0,
            disk_mb=(disk.used / 1024 / 1024) if disk else 0,
            network_bytes=net.bytes_sent + net.bytes_recv if net else 0,
        )
        self._usage.append(usage)
        return usage

    def set_budget(self, mission_id: str, budget: MissionBudget):
        self._budgets[mission_id] = budget

    def record_token_usage(self, mission_id: str, tokens: int, cost: float = 0.0):
        """Record token usage for a mission."""
        if mission_id in self._budgets:
            self._budgets[mission_id].used_tokens += tokens
            self._budgets[mission_id].spent_amount += cost
        self._total_tokens += tokens
        self._total_cost += cost

    def record_time(self, mission_id: str, seconds: float):
        """Record elapsed time for a mission."""
        if mission_id in self._budgets:
            self._budgets[mission_id].elapsed_seconds += seconds

    def record_compute(self, mission_id: str, cpu_hours: float):
        """Record compute usage for a mission."""
        if mission_id in self._budgets:
            self._budgets[mission_id].used_compute += cpu_hours

    def record_tool_call(self, mission_id: str):
        """Record a tool call."""
        snapshot = self.snapshot()
        snapshot.tool_calls = 1
        self._usage.append(snapshot)
        if mission_id in self._budgets:
            self._budgets[mission_id].used_compute += 0.001  # Approximate

    def check_budget(self, mission_id: str) -> Dict[str, Any]:
        """Check if a mission is within budget."""
        budget = self._budgets.get(mission_id)
        if not budget:
            return {"within_budget": True, "message": "No budget set"}

        util = budget.utilization()
        alerts = []
        if budget.used_tokens >= budget.token_limit * 0.9:
            alerts.append("token_budget_90_percent")
        if budget.elapsed_seconds >= budget.time_limit_seconds * 0.9:
            alerts.append("time_budget_90_percent")
        if budget.monetary_limit > 0 and budget.spent_amount >= budget.monetary_limit * 0.9:
            alerts.append("monetary_budget_90_percent")

        return {
            "within_budget": not budget.is_exhausted() and not alerts,
            "utilization": util,
            "alerts": alerts,
            "budget": {
                "token_limit": budget.token_limit,
                "time_limit_seconds": budget.time_limit_seconds,
                "monetary_limit": budget.monetary_limit,
            },
        }

    def expected_value(self, expected_benefit: float, cost: float, probability: float = 1.0) -> float:
        """Calculate expected value: probability * benefit - cost."""
        return probability * expected_benefit - cost

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_tokens": self._total_tokens,
            "total_cost": round(self._total_cost, 6),
            "active_budgets": len(self._budgets),
            "budgets": {mid: {"utilization": b.utilization(), "exhausted": b.is_exhausted()}
                       for mid, b in self._budgets.items()},
            "recent_snapshots": len(self._usage),
        }


class EconomicLedgerPlugin:
    def __init__(self):
        self.engine = EconomicLedger()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        summary = self.engine.get_summary()
        return {"status": "healthy", "summary": summary}


async def create(kernel=None):
    plugin = EconomicLedgerPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
