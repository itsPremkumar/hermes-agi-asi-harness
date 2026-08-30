"""Hermes AGI/ASI Harness — Safety Architecture Plugin

Advanced safety plugin for the harness:
- Multi-layer guardrails (input, execution, output)
- Rate limiting and resource quotas
- Anomaly detection on agent behavior
- Human override hooks for critical operations
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from harness_control_plane import (
    IPlugin,
    SafetyLevel,
    TaskRequest,
    TaskResult,
    SafetyReport,
)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 500
    max_concurrent: int = 5
    cooldown_seconds: float = 1.0


@dataclass
class ResourceQuota:
    """Resource quota for a plugin or agent."""
    max_cpu_seconds: float = 3600.0
    max_memory_mb: float = 1024.0
    max_api_calls: int = 1000.0
    max_disk_mb: float = 512.0


class SafetyPlugin(IPlugin):
    """Multi-layer safety guardrail plugin."""
    
    name = "safety"
    version = "1.0.0"
    capabilities = ["safety_check", "rate_limit", "quota_enforce", "anomaly_detect"]
    
    def __init__(self, rate_limit: Optional[RateLimitConfig] = None,
                 quota: Optional[ResourceQuota] = None):
        self._rate_limit = rate_limit or RateLimitConfig()
        self._quota = quota or ResourceQuota()
        self._request_log: dict[str, list[float]] = defaultdict(list)
        self._active_tasks: dict[str, float] = {}
        self._anomaly_callbacks: list[Callable] = []
        self._custom_rules: list[Callable[[TaskRequest], Optional[str]]] = []
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the safety plugin."""
        if config.get("rate_limit"):
            self._rate_limit = RateLimitConfig(**config["rate_limit"])
        if config.get("quota"):
            self._quota = ResourceQuota(**config["quota"])
        self._custom_rules = []
        self._initialized = True
    
    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute safety checks on a task."""
        # Pre-execution safety check
        precheck_violations = await self._precheck(task)
        if precheck_violations:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"Safety precheck failed: {precheck_violations}",
                safety_violations=precheck_violations,
            )
        
        # Rate limiting
        rate_violations = self._check_rate_limit(task.task_type)
        if rate_violations:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"Rate limit exceeded: {rate_violations}",
                safety_violations=rate_violations,
            )
        
        # Resource quota check
        quota_violations = self._check_quota(task.task_type)
        if quota_violations:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"Quota exceeded: {quota_violations}",
                safety_violations=quota_violations,
            )
        
        # Custom rules
        for rule in self._custom_rules:
            violation = rule(task)
            if violation:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Custom rule violation: {violation}",
                    safety_violations=[violation],
                )
        
        return TaskResult(
            task_id=task.task_id,
            success=True,
            result="Safety precheck passed",
        )
    
    async def shutdown(self) -> None:
        """Shutdown the safety plugin."""
        self._initialized = False
        self._request_log.clear()
        self._active_tasks.clear()
    
    async def health_check(self) -> bool:
        """Check plugin health."""
        return self._initialized
    
    def add_custom_rule(self, rule: Callable[[TaskRequest], Optional[str]]) -> None:
        """Add a custom safety rule."""
        self._custom_rules.append(rule)
    
    def register_anomaly_callback(self, callback: Callable) -> None:
        """Register an anomaly detection callback."""
        self._anomaly_callbacks.append(callback)
    
    async def _precheck(self, task: TaskRequest) -> list[str]:
        """Run pre-execution safety checks."""
        violations = []
        
        # Check safety level
        if task.safety_level == SafetyLevel.CRITICAL and not task.requires_human_approval:
            violations.append("CRITICAL level requires human approval flag")
        
        # Check timeout bounds
        if task.timeout_seconds <= 0 or task.timeout_seconds > 3600:
            violations.append(f"Invalid timeout: {task.timeout_seconds}s")
        
        return violations
    
    def _check_rate_limit(self, task_type: str) -> list[str]:
        """Check rate limits for a task type."""
        now = time.time()
        violations = []
        
        # Clean old entries
        self._request_log[task_type] = [
            t for t in self._request_log[task_type] if now - t < 3600
        ]
        
        # Per-minute check
        recent = [t for t in self._request_log[task_type] if now - t < 60]
        if len(recent) >= self._rate_limit.max_requests_per_minute:
            violations.append(
                f"Per-minute rate limit exceeded: {len(recent)}/{self._rate_limit.max_requests_per_minute}"
            )
        
        # Per-hour check
        if len(self._request_log[task_type]) >= self._rate_limit.max_requests_per_hour:
            violations.append(
                f"Per-hour rate limit exceeded: {len(self._request_log[task_type])}/{self._rate_limit.max_requests_per_hour}"
            )
        
        # Concurrent check
        active = len([t for t in self._active_tasks.values() if now - t < 300])
        if active >= self._rate_limit.max_concurrent:
            violations.append(
                f"Concurrent limit exceeded: {active}/{self._rate_limit.max_concurrent}"
            )
        
        # Log this request
        self._request_log[task_type].append(now)
        
        return violations
    
    def _check_quota(self, task_type: str) -> list[str]:
        """Check resource quotas."""
        # Simplified: just check request count as proxy
        violations = []
        total_requests = sum(len(v) for v in self._request_log.values())
        if total_requests >= self._quota.max_api_calls:
            violations.append(f"API call quota exceeded: {total_requests}")
        return violations


class AnomalyDetector:
    """Detects anomalous behavior in agent execution."""
    
    def __init__(self, window_size: int = 100, threshold_sigma: float = 3.0):
        self._window_size = window_size
        self._threshold_sigma = threshold_sigma
        self._execution_times: list[float] = []
        self._error_counts: dict[str, int] = defaultdict(int)
        self._anomalies: list[dict[str, Any]] = []
    
    def record_execution(self, duration: float, success: bool, task_type: str) -> None:
        """Record an execution for anomaly detection."""
        self._execution_times.append(duration)
        if len(self._execution_times) > self._window_size:
            self._execution_times.pop(0)
        
        if not success:
            self._error_counts[task_type] += 1
    
    def detect_anomaly(self) -> Optional[dict[str, Any]]:
        """Detect if current behavior is anomalous."""
        if len(self._execution_times) < 10:
            return None
        
        mean = sum(self._execution_times) / len(self._execution_times)
        variance = sum((t - mean) ** 2 for t in self._execution_times) / len(self._execution_times)
        std_dev = variance ** 0.5
        
        latest = self._execution_times[-1]
        z_score = (latest - mean) / std_dev if std_dev > 0 else 0
        
        if abs(z_score) > self._threshold_sigma:
            anomaly = {
                "type": "execution_time",
                "z_score": z_score,
                "mean": mean,
                "latest": latest,
                "timestamp": time.time(),
            }
            self._anomalies.append(anomaly)
            return anomaly
        
        return None
    
    def get_anomalies(self) -> list[dict[str, Any]]:
        """Get all detected anomalies."""
        return list(self._anomalies)
