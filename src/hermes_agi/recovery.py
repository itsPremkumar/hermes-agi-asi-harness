"""
Self-Recovery & Fallback System — Production-Grade Resilience.

Features:
- Automatic failure detection
- Self-healing with multiple strategies
- Fallback chains
- Graceful degradation
- Checkpoint/retry mechanisms
- Health monitoring
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ──────────────────────────── Enums ────────────────────────────


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    DEGRADE = "degrade"
    RECONFIGURE = "reconfigure"
    RESTART = "restart"
    ESCALATE = "escalate"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# ──────────────────────────── Data Classes ────────────────────────────


@dataclass
class FailureEvent:
    """A failure event."""
    event_id: str
    component: str
    error: str
    timestamp: float
    severity: str = "error"
    context: dict[str, Any] = field(default_factory=dict)
    stacktrace: str = ""
    recovery_attempts: int = 0


@dataclass
class RecoveryAction:
    """A recovery action."""
    strategy: RecoveryStrategy
    component: str
    action: Callable[..., Coroutine]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    max_attempts: int = 3
    timeout: float = 30.0


@dataclass
class HealthRecord:
    """Health record for a component."""
    component: str
    status: HealthStatus
    last_check: float
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Checkpoint:
    """A system checkpoint."""
    checkpoint_id: str
    timestamp: float
    state: dict[str, Any]
    component: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Diagnosis:
    """Root-cause diagnosis and corrective action produced by DeepHealingAgent."""
    category: str
    root_cause: str
    suggested_action: str
    recoverable: bool = True
    suggested_strategy: RecoveryStrategy = RecoveryStrategy.RETRY


class DeepHealingAgent:
    """
    Autonomous Diagnostic & Self-Healing Agent.
    
    Parses stack traces, error patterns, and execution context to formulate
    root-cause diagnoses and dynamic repair strategies.
    """

    def diagnose(self, error: str, context: dict[str, Any] | None = None) -> Diagnosis:
        err_lower = error.lower()
        ctx = context or {}

        # 1. Encoding / Subprocess errors
        if "unicodedecodeerror" in err_lower or "charmap" in err_lower:
            return Diagnosis(
                category="encoding",
                root_cause="Windows ANSI / cp1252 character map collision on non-ASCII output.",
                suggested_action="Re-run subprocess with explicit encoding='utf-8' and errors='replace'.",
                suggested_strategy=RecoveryStrategy.RECONFIGURE,
            )

        # 2. File / Directory missing
        if "filenotfounderror" in err_lower or "no such file" in err_lower:
            return Diagnosis(
                category="filesystem",
                root_cause="Target path or prerequisite artifact does not exist in workspace.",
                suggested_action="Create parent directories and initialize missing fallback artifact.",
                suggested_strategy=RecoveryStrategy.FALLBACK,
            )

        # 3. Timeout / Resource exhaustion
        if "timeoutexpired" in err_lower or "timeout" in err_lower:
            return Diagnosis(
                category="timeout",
                root_cause="Execution exceeded designated budget timeout window.",
                suggested_action="Scale budget/timeout limit and batch tasks into smaller chunks.",
                suggested_strategy=RecoveryStrategy.RECONFIGURE,
            )

        # 4. Import / Missing dependency
        if "modulenotfounderror" in err_lower or "no module named" in err_lower:
            return Diagnosis(
                category="dependency",
                root_cause="Required third-party library or package not present in current environment.",
                suggested_action="Activate safe fallback mock or pip install required dependency.",
                suggested_strategy=RecoveryStrategy.FALLBACK,
            )

        # Default: General execution exception
        return Diagnosis(
            category="general_fault",
            root_cause=f"Runtime exception in component: {error[:120]}",
            suggested_action="Roll back to previous verified checkpoint and retry with defensive assertions.",
            suggested_strategy=RecoveryStrategy.RETRY,
        )


# ──────────────────────────── Self-Recovery System ────────────────────────────


class SelfRecoverySystem:
    """
    Automatic failure detection, deep diagnosis, and self-healing.
    
    Strategies:
    1. Retry — Re-execute with exponential backoff
    2. Fallback — Switch to alternative implementation
    3. Degrade — Reduce functionality gracefully
    4. Reconfigure — Adjust parameters and retry
    5. Restart — Restart the component
    6. Escalate — Notify and request human intervention
    """
    
    def __init__(self, state_dir: str = None):
        self.state_dir = state_dir or os.path.join(os.getcwd(), "state")
        self.healing_agent = DeepHealingAgent()
        self._health_records: dict[str, HealthRecord] = {}
        self._failure_log: list[FailureEvent] = []
        self._checkpoints: list[Checkpoint] = []
        self._recovery_strategies: dict[str, list[RecoveryAction]] = {}
        self._fallback_chains: dict[str, list[Callable]] = {}
        self._monitoring = False
        self._monitor_task: asyncio.Task = None
        
        os.makedirs(self.state_dir, exist_ok=True)
    
    async def start_monitoring(self, interval: float = 10.0):
        """Start health monitoring."""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Self-recovery monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("Self-recovery monitoring stopped")
    
    def register_component(
        self,
        component: str,
        health_check: Callable[..., Coroutine],
        recovery_strategies: list[RecoveryAction] = None,
        fallback_chain: list[Callable] = None,
    ):
        """Register a component for monitoring."""
        self._health_records[component] = HealthRecord(
            component=component,
            status=HealthStatus.UNKNOWN,
            last_check=0,
        )
        if recovery_strategies:
            self._recovery_strategies[component] = recovery_strategies
        if fallback_chain:
            self._fallback_chains[component] = fallback_chain
    
    async def report_failure(
        self,
        component: str,
        error: str,
        context: dict[str, Any] = None,
        severity: str = "error",
    ) -> bool:
        """Report a failure and attempt recovery."""
        event = FailureEvent(
            event_id=str(uuid.uuid4())[:8],
            component=component,
            error=error,
            timestamp=time.time(),
            severity=severity,
            context=context or {},
            stacktrace=traceback.format_exc(),
        )
        self._failure_log.append(event)
        
        # Update health record
        if component in self._health_records:
            record = self._health_records[component]
            record.status = HealthStatus.UNHEALTHY
            record.last_check = time.time()
            record.message = error
            record.history.append({
                "timestamp": event.timestamp,
                "error": error,
                "severity": severity,
            })
        
        # Attempt recovery
        return await self._attempt_recovery(component, event)
    
    async def report_success(self, component: str, message: str = ""):
        """Report successful operation."""
        if component in self._health_records:
            record = self._health_records[component]
            record.status = HealthStatus.HEALTHY
            record.last_check = time.time()
            record.message = message
    
    async def check_health(self, component: str) -> HealthStatus:
        """Check health of a component."""
        if component not in self._health_records:
            return HealthStatus.UNKNOWN
        
        record = self._health_records[component]
        
        # Check if health check is stale
        if time.time() - record.last_check > 60:
            record.status = HealthStatus.DEGRADED
            record.message = "Health check stale"
        
        return record.status
    
    async def create_checkpoint(self, component: str, state: dict[str, Any]) -> str:
        """Create a checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            state=state,
            component=component,
        )
        self._checkpoints.append(checkpoint)
        
        # Save to disk
        checkpoint_file = os.path.join(self.state_dir, f"checkpoint_{checkpoint.checkpoint_id}.json")
        with open(checkpoint_file, "w") as f:
            json.dump({
                "checkpoint_id": checkpoint.checkpoint_id,
                "timestamp": checkpoint.timestamp,
                "component": component,
                "state": state,
            }, f, indent=2)
        
        return checkpoint.checkpoint_id
    
    async def restore_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore from a checkpoint."""
        for checkpoint in self._checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                logger.info(f"Restoring checkpoint {checkpoint_id}")
                return checkpoint.state
        
        # Try loading from disk
        checkpoint_file = os.path.join(self.state_dir, f"checkpoint_{checkpoint_id}.json")
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file) as f:
                data = json.load(f)
                return data["state"]
        
        raise ValueError(f"Checkpoint {checkpoint_id} not found")
    
    def get_latest_checkpoint(self, component: str) -> Checkpoint | None:
        """Get the latest checkpoint for a component."""
        component_checkpoints = [c for c in self._checkpoints if c.component == component]
        if not component_checkpoints:
            return None
        return max(component_checkpoints, key=lambda c: c.timestamp)
    
    async def execute_with_recovery(
        self,
        component: str,
        func: Callable[..., Coroutine],
        *args,
        fallback: Callable[..., Coroutine] = None,
        max_retries: int = 3,
        **kwargs,
    ) -> Any:
        """Execute a function with automatic recovery."""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                await self.report_success(component, f"Success on attempt {attempt + 1}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"{component} attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    delay = min(2 ** attempt, 30)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        
        # All retries exhausted, try fallback
        if fallback:
            try:
                logger.info(f"Trying fallback for {component}")
                result = await fallback()
                await self.report_success(component, "Fallback succeeded")
                return result
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
        
        # Report failure
        await self.report_failure(component, str(last_error))
        raise last_error
    
    async def execute_with_fallback_chain(
        self,
        component: str,
        func: Callable[..., Coroutine],
        *args,
        **kwargs,
    ) -> Any:
        """Execute with fallback chain."""
        # Try primary function
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"{component} primary failed: {e}")
        
        # Try fallbacks
        fallbacks = self._fallback_chains.get(component, [])
        for i, fallback in enumerate(fallbacks):
            try:
                logger.info(f"Trying fallback {i + 1} for {component}")
                return await fallback()
            except Exception as e:
                logger.warning(f"Fallback {i + 1} failed: {e}")
        
        # All fallbacks exhausted
        await self.report_failure(component, "All fallbacks exhausted")
        raise RuntimeError(f"{component}: all fallbacks exhausted")
    
    def get_health_summary(self) -> dict[str, Any]:
        """Get health summary."""
        return {
            "components": {
                name: {
                    "status": record.status.value,
                    "last_check": record.last_check,
                    "message": record.message,
                }
                for name, record in self._health_records.items()
            },
            "total_failures": len(self._failure_log),
            "recent_failures": [
                {
                    "component": f.component,
                    "error": f.error,
                    "timestamp": f.timestamp,
                }
                for f in self._failure_log[-10:]
            ],
            "total_checkpoints": len(self._checkpoints),
        }
    
    async def _attempt_recovery(self, component: str, event: FailureEvent) -> bool:
        """Attempt to recover a component."""
        strategies = self._recovery_strategies.get(component, [])
        
        for strategy in strategies:
            if event.recovery_attempts >= strategy.max_attempts:
                continue
            
            event.recovery_attempts += 1
            
            try:
                logger.info(f"Recovery attempt for {component}: {strategy.strategy.value}")
                await asyncio.wait_for(
                    strategy.action(*strategy.args, **strategy.kwargs),
                    timeout=strategy.timeout,
                )
                
                # Verify recovery
                if component in self._health_records:
                    self._health_records[component].status = HealthStatus.HEALTHY
                
                logger.info(f"Recovery successful for {component}")
                return True
                
            except Exception as e:
                logger.warning(f"Recovery attempt failed: {e}")
        
        logger.error(f"All recovery strategies exhausted for {component}")
        return False
    
    async def _monitor_loop(self, interval: float):
        """Health monitoring loop."""
        while self._monitoring:
            try:
                for component, record in self._health_records.items():
                    # Check if health check is stale
                    if time.time() - record.last_check > interval * 3:
                        if record.status == HealthStatus.HEALTHY:
                            record.status = HealthStatus.DEGRADED
                            record.message = "Health check stale"
                            logger.warning(f"Component {component} degraded (stale check)")
                
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")


# ──────────────────────────── Fallback Decorator ────────────────────────────


def with_fallback(*fallbacks: Callable):
    """Decorator: execute function with fallback chain."""
    def decorator(func: Callable[..., Coroutine]):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"{func.__name__} failed: {e}")
            
            for i, fallback in enumerate(fallbacks):
                try:
                    logger.info(f"Trying fallback {i + 1} for {func.__name__}")
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback()
                    else:
                        return fallback()
                except Exception as e:
                    logger.warning(f"Fallback {i + 1} failed: {e}")
            
            raise RuntimeError(f"{func.__name__}: all fallbacks exhausted")
        
        return wrapper
    return decorator


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator: retry with exponential backoff."""
    def decorator(func: Callable[..., Coroutine]):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        wait = delay * (backoff ** attempt)
                        logger.warning(f"{func.__name__} attempt {attempt + 1} failed, retrying in {wait}s: {e}")
                        await asyncio.sleep(wait)
            raise last_error
        return wrapper
    return decorator


def with_circuit_breaker(threshold: int = 5, timeout: float = 30.0):
    """Decorator: circuit breaker pattern."""
    def decorator(func: Callable[..., Coroutine]):
        failure_count = 0
        last_failure = 0
        state = "closed"
        
        async def wrapper(*args, **kwargs):
            nonlocal failure_count, last_failure, state
            
            if state == "open":
                if time.time() - last_failure > timeout:
                    state = "half_open"
                else:
                    raise RuntimeError(f"Circuit breaker open for {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                failure_count = 0
                state = "closed"
                return result
            except Exception:
                failure_count += 1
                last_failure = time.time()
                if failure_count >= threshold:
                    state = "open"
                raise
        
        return wrapper
    return decorator


# ──────────────────────────── Graceful Degradation ────────────────────────────


class DegradationManager:
    """Manages graceful degradation of services."""
    
    def __init__(self):
        self._service_levels: dict[str, int] = {}
        self._max_levels: dict[str, int] = {}
    
    def register_service(self, name: str, max_level: int = 3):
        """Register a service with degradation levels."""
        self._service_levels[name] = 0
        self._max_levels[name] = max_level
    
    def degrade(self, name: str) -> bool:
        """Degrade a service by one level."""
        if name not in self._service_levels:
            return False
        
        current = self._service_levels[name]
        if current < self._max_levels[name]:
            self._service_levels[name] = current + 1
            logger.warning(f"Service {name} degraded to level {current + 1}")
            return True
        return False
    
    def restore(self, name: str) -> bool:
        """Restore a service by one level."""
        if name not in self._service_levels:
            return False
        
        current = self._service_levels[name]
        if current > 0:
            self._service_levels[name] = current - 1
            logger.info(f"Service {name} restored to level {current - 1}")
            return True
        return False
    
    def get_level(self, name: str) -> int:
        """Get current degradation level."""
        return self._service_levels.get(name, 0)
    
    def is_available(self, name: str) -> bool:
        """Check if service is available."""
        return self._service_levels.get(name, 0) < self._max_levels.get(name, 3)
