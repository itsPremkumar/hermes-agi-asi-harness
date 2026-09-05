#!/usr/bin/env python3
"""
Recovery Engine Plugin — failure classification & recovery strategies.

Upgrade from the legacy recovery engine: the engine now classifies failures
into seven canonical failure classes and applies one of four recovery
strategies to each.

Failure classes (``FailureClass``):
    TRANSIENT, TOOL, PLANNING, REASONING, ENVIRONMENT, DEPENDENCY, SAFETY
    (plus ``UNKNOWN`` as a last-resort fallback for unclassifiable errors).

Recovery strategies (``RecoveryStrategy``):
    RETRY    — re-attempt a transient/tool failure with exponential backoff.
    REPLAN   — signal that the plan/reasoning chain must be regenerated.
    SUBSTITUTE— swap a failed tool/resource for an alternative.
    ESCALATE — surface the failure to a human / higher authority.

The mapping from failure class to strategy is configurable (see
``RecoveryEngine.default_strategy``).

PluginBase contract:
    * ``create(kernel)`` async factory (used by HermesKernel core-loader).
    * Lifecycle: ``load / start / stop / pause / resume / unload``.
    * ``health()`` returns a dict containing a ``status`` key
      (``healthy`` / ``degraded`` / ``error``).
    * ``get_capabilities()`` for tool registration by the kernel.

Loaded by ``core/runtime/kernel.py`` as a core plugin via
``plugins.recovery_engine.create``.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("hermes.recovery_engine")


# ---------------------------------------------------------------------------
# PluginBase — imported from the trusted core, with a defensive fallback so the
# plugin can still be imported in isolation (mirrors plugins/audit_logger).
# ---------------------------------------------------------------------------
try:
    from core.runtime.plugin_base import (
        PluginBase,
        PluginManifest,
        PluginPermissions,
        PluginState,
    )
except ImportError:  # pragma: no cover - exercised only without core on path
    from dataclasses import dataclass as _dc
    from enum import Enum as _Enum

    class PluginState(_Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"

    @_dc
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: int = 512
        max_cpu_percent: int = 50

    @_dc
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "unknown"
        source: str = "internal"
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None

    class PluginBase:  # minimal duck-typed stand-in
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED

        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True

        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True

        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True


# ===========================================================================
# ENUMS
# ===========================================================================

class FailureClass(str, Enum):
    """Canonical failure categories the recovery engine can classify.

    The seven required classes plus ``UNKNOWN`` as a safe fallback.
    """
    TRANSIENT = "transient"      # timeouts, rate limits, transient network/5xx
    TOOL = "tool"                # tool invocation/argument/execution failures
    PLANNING = "planning"        # plan generation / step sequencing failures
    REASONING = "reasoning"      # inference, deduction, logic contradictions
    ENVIRONMENT = "environment"  # missing env vars, paths, disk, memory, config
    DEPENDENCY = "dependency"    # import errors, missing packages, version lock
    SAFETY = "safety"            # guardrail/content-policy/injection violations
    UNKNOWN = "unknown"          # unclassifiable -> escalate by default


class RecoveryStrategy(str, Enum):
    """Recovery strategies selectable per failure class."""
    RETRY = "retry"
    REPLAN = "replan"
    SUBSTITUTE = "substitute"
    ESCALATE = "escalate"


class StrategyOutcome(str, Enum):
    """Outcome of an applied recovery strategy."""
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"
    NO_RECOVERY = "no_recovery"


# ===========================================================================
# DATA MODELS
# ===========================================================================

@dataclass
class Checkpoint:
    """A recovery checkpoint — captures task state for rollback/resume."""
    checkpoint_id: str
    task_id: str
    state: dict[str, Any]
    created_at: float
    failure_class: str = ""
    strategy: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "state": self.state,
            "created_at": self.created_at,
            "failure_class": self.failure_class,
            "strategy": self.strategy,
        }


@dataclass
class RecoveryRecord:
    """A single recovery attempt — its classification, chosen strategy & outcome."""
    record_id: str
    task_id: str
    failure_class: FailureClass
    error: str
    strategy: RecoveryStrategy
    status: str = "attempting"        # attempting | resolved | failed | escalated
    context: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    error_detail: str = ""
    result: StrategyResult | None = None
    resolution: bool = False

    @property
    def outcome(self) -> str:
        if self.result is not None:
            return self.result.outcome.value
        return StrategyOutcome.NO_RECOVERY.value


@dataclass
class StrategyResult:
    """Result returned by an individual recovery-strategy method."""
    strategy: RecoveryStrategy
    outcome: StrategyOutcome
    task_id: str = ""
    attempts: int = 1
    error: str = ""
    recommendation: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "outcome": self.outcome.value,
            "task_id": self.task_id,
            "attempts": self.attempts,
            "error": self.error,
            "recommendation": self.recommendation,
            "details": dict(self.details),
        }


@dataclass
class RecoveryContext:
    """Structured context handed to ``recover()``."""
    task_id: str
    error: str | Exception
    operation: Callable[..., Any] | None = None
    alternatives: list[str] = field(default_factory=list)
    severity: str = "medium"          # low | medium | high
    max_retries: int = 3
    backoff_base: float = 1.0
    context: dict[str, Any] = field(default_factory=dict)
    strategies: list[str] | None = None  # explicit allow-list override


# ===========================================================================
# CLASSIFICATION TABLES
# ===========================================================================

# (compiled regex, FailureClass) — evaluated in order; first match wins.
_FAILURE_PATTERNS: list[tuple] = [
    # SAFETY must be checked early: a blocked tool is a safety issue, not a tool error.
    (re.compile(r"\b(injection|prompt.?injection|safety|guardrail|policy|content.?filter|"
                r"prohibited|blocked|sanitizer|tamper|unauthorized|forbidden|violation)\b", re.IGNORECASE),
     FailureClass.SAFETY),
    # DEPENDENCY — module/import/package problems.
    (re.compile(r"\b(import|module not found|no module|dependency|package|requires?|version "
                r"conflict|dependencyerror)\b", re.IGNORECASE), FailureClass.DEPENDENCY),
    # PLANNING — plan/step/goal generation.
    (re.compile(r"\b(plan|no plan|planning|steps|goal is empty|unable to plan|replan|trajectory)\b",
                re.IGNORECASE), FailureClass.PLANNING),
    # REASONING — inference/logic contradictions.
    (re.compile(r"\b(reason|reasoning|contradiction|inference|deduction|logical|inconsistent|"
                r"paradox|invalid deduction)\b", re.IGNORECASE), FailureClass.REASONING),
    # ENVIRONMENT — infra/filesystem/config/resource.
    (re.compile(r"\b(environment|env var|disk (full|space)|memory|oom|out of memory|"
                r"no such file|file not found|fileNotFoundError|path|directory|config "
                r"file|missing configuration|resource)\b", re.IGNORECASE), FailureClass.ENVIRONMENT),
    # TOOL — tool invocation/argument/execution problems.
    (re.compile(r"\b(tool|toolkit|invalid tool|tool not found|tool execution|tool call|"
                r"invalid argument|argument error|toolerror)\b", re.IGNORECASE), FailureClass.TOOL),
    # TRANSIENT — retryable infrastructure errors.
    (re.compile(r"\b(timeout|timed out|rate limit|429|too many requests|temporarily "
                r"unavailable|connection (reset|refused|aborted|closed)|deadlock|"
                r"retry-after|5\d\d|transient|service unavailable|temporarily)\b", re.IGNORECASE),
     FailureClass.TRANSIENT),
]

# Default strategy per failure class. Safety & env are never auto-substituted.
_DEFAULT_STRATEGY: dict[FailureClass, RecoveryStrategy] = {
    FailureClass.TRANSIENT: RecoveryStrategy.RETRY,
    FailureClass.TOOL: RecoveryStrategy.SUBSTITUTE,
    FailureClass.PLANNING: RecoveryStrategy.REPLAN,
    FailureClass.REASONING: RecoveryStrategy.REPLAN,
    FailureClass.ENVIRONMENT: RecoveryStrategy.ESCALATE,
    FailureClass.DEPENDENCY: RecoveryStrategy.SUBSTITUTE,
    FailureClass.SAFETY: RecoveryStrategy.ESCALATE,
    FailureClass.UNKNOWN: RecoveryStrategy.ESCALATE,
}


# ===========================================================================
# Recovery Engine
# ===========================================================================

class RecoveryEngine(PluginBase):
    """Self-healing recovery engine: classify failures & apply recovery strategies.

    Implements the Hermes ``PluginBase`` lifecycle. Constructed via the
    ``create()`` async factory (kernel contract) and also directly as
    ``Plugin()`` (PluginManager contract).
    """

    def __init__(self, kernel: Any = None, manifest: PluginManifest | None = None):
        if manifest is None:
            manifest = self._default_manifest()
        super().__init__(manifest, kernel)

        # recovery state
        self._checkpoints: dict[str, Checkpoint] = {}
        self._records: dict[str, RecoveryRecord] = {}
        self._escalation_log: list[dict[str, Any]] = []
        self._strategy_counts: dict[str, int] = {s.value: 0 for s in RecoveryStrategy}
        self._recovery_attempts: int = 0
        # configurable classification / strategy tables (instance-level so callers
        # can tune without touching the module globals).
        self.classification_rules: list[tuple] = list(_FAILURE_PATTERNS)
        self.default_strategy: dict[FailureClass, RecoveryStrategy] = dict(_DEFAULT_STRATEGY)

    # -- manifest -----------------------------------------------------------
    @staticmethod
    def _default_manifest() -> PluginManifest:
        """Build the manifest, preferring plugin.yaml (single source of truth)."""
        yaml_path = Path(__file__).resolve().parent / "plugin.yaml"
        try:
            if yaml_path.exists():
                return PluginManifest.from_yaml(yaml_path)
        except Exception as e:  # pragma: no cover - never fatal at construction
            logger.debug("Falling back to inline manifest: %s", e)
        return PluginManifest(
            name="recovery_engine",
            version="2.0.0",
            description="Failure classification & recovery strategies (retry/replan/"
                        "substitute/escalate)",
            license="MIT",
            source="internal",
            capabilities=["recovery", "checkpoint", "rollback", "retry",
                          "replan", "substitute", "escalate", "failure_classification"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=256,
                max_cpu_percent=10,
            ),
        )

    # -- lifecycle ----------------------------------------------------------
    async def load(self) -> bool:
        await super().load()
        logger.info("Recovery engine loaded (kernel=%s)",
                    "<set>" if self.kernel is not None else "<none>")
        return True

    async def start(self) -> bool:
        await super().start()
        logger.info("Recovery engine started")
        return True

    async def stop(self) -> bool:
        await self.flush()
        await super().stop()
        logger.info("Recovery engine stopped")
        return True

    async def pause(self) -> bool:
        self.state = PluginState.PAUSED
        return True

    async def resume(self) -> bool:
        self.state = PluginState.RUNNING
        return True

    async def unload(self) -> bool:
        await self.flush()
        self.state = PluginState.UNLOADED
        return True

    # -- checkpoints (kept API-compatible with the legacy engine) -----------
    def create_checkpoint(self, task_id: str, state: dict[str, Any],
                          failure_class: str = "", strategy: str = "") -> str:
        """Create a checkpoint for a task. Returns the checkpoint id."""
        checkpoint_id = str(uuid.uuid4())
        self._checkpoints[checkpoint_id] = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            state=state,
            created_at=time.time(),
            failure_class=failure_class,
            strategy=strategy,
        )
        logger.debug("Checkpoint %s created for task %s", checkpoint_id, task_id)
        return checkpoint_id

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        return self._checkpoints.get(checkpoint_id)

    def get_latest_checkpoint(self, task_id: str) -> Checkpoint | None:
        """Get the most recent checkpoint for a task."""
        checkpoints = [c for c in self._checkpoints.values() if c.task_id == task_id]
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda c: c.created_at)

    def rollback(self, task_id: str) -> dict[str, Any] | None:
        """Return the state of the latest checkpoint for a task (rollback target)."""
        cp = self.get_latest_checkpoint(task_id)
        return cp.state if cp else None

    def resume_from_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """Resume from the latest checkpoint, clearing newer checkpoints."""
        cp = self.get_latest_checkpoint(task_id)
        if cp is None:
            return None
        # drop checkpoints strictly newer than the resume point for this task
        resume_ts = cp.created_at
        stale = [cid for cid, c in self._checkpoints.items()
                 if c.task_id == task_id and c.created_at > resume_ts]
        for cid in stale:
            del self._checkpoints[cid]
        logger.info("Resumed task %s from checkpoint %s", task_id, cp.checkpoint_id)
        return cp.state

    # -- failure classification --------------------------------------------
    def classify_failure(self, error: Exception | str) -> FailureClass:
        """Classify a failure into one of the seven canonical failure classes.

        Order matters: safety is checked first (a blocked tool is a safety
        issue, not a generic tool error). Unclassifiable errors fall back to
        ``UNKNOWN``.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # exception-type hints
        if error_type == "ImportError" or error_type == "ModuleNotFoundError":
            return FailureClass.DEPENDENCY
        if error_type == "FileNotFoundError":
            return FailureClass.ENVIRONMENT
        if error_type == "TimeoutError":
            return FailureClass.TRANSIENT

        for pattern, fclass in self.classification_rules:
            if pattern.search(error_str) or pattern.search(error_type):
                return fclass
        return FailureClass.UNKNOWN

    def select_strategy(self, failure_class: FailureClass | str) -> RecoveryStrategy:
        """Pick the default recovery strategy for a given failure class."""
        if isinstance(failure_class, str):
            try:
                failure_class = FailureClass(failure_class)
            except ValueError:
                return RecoveryStrategy.ESCALATE
        return self.default_strategy.get(failure_class, RecoveryStrategy.ESCALATE)

    # -- recovery strategies ------------------------------------------------
    async def _invoke(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """Call fn (sync or async), awaiting coroutines transparently."""
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    async def retry(self, operation: Callable[..., Any], *,
                    max_attempts: int = 3, backoff_base: float = 1.0,
                    backoff_factor: float = 2.0,
                    on_retry: Callable[[int, Exception], Any] | None = None,
                    **op_kwargs) -> StrategyResult:
        """Re-attempt ``operation`` with exponential backoff.

        ``operation`` may be sync or async and receives ``attempt`` (1-based)
        plus ``op_kwargs``. Returns a ``StrategyResult`` describing the outcome.
        """
        self._strategy_counts[RecoveryStrategy.RETRY.value] += 1
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                await self._invoke(operation, attempt=attempt, **op_kwargs)
                return StrategyResult(
                    strategy=RecoveryStrategy.RETRY,
                    outcome=StrategyOutcome.SUCCESS,
                    attempts=attempt,
                    recommendation="operation succeeded after retry",
                    details={"max_attempts": max_attempts, "attempt": attempt},
                )
            except Exception as e:
                last_error = e
                if on_retry is not None:
                    try:
                        cb = on_retry(attempt, e)
                        if asyncio.iscoroutine(cb):
                            await cb
                    except Exception:
                        logger.debug("on_retry callback raised: %s", e, exc_info=True)
                if attempt < max_attempts:
                    delay = backoff_base * (backoff_factor ** (attempt - 1))
                    logger.debug("retry %d/%d in %.2fs after %s", attempt, max_attempts, delay, e)
                    await asyncio.sleep(delay)
        return StrategyResult(
            strategy=RecoveryStrategy.RETRY,
            outcome=StrategyOutcome.FAILED,
            attempts=max_attempts,
            error=str(last_error),
            recommendation="exhausted retries",
            details={"max_attempts": max_attempts},
        )

    def replan(self, task_id: str, context: dict[str, Any] | None = None,
               suggested_plan: str | None = None) -> StrategyResult:
        """Request a fresh plan/reasoning chain for the task.

        In a full system this would invoke the planning/reasoning engine; here
        we record the request and return a recommendation the orchestrator can
        act on.
        """
        self._strategy_counts[RecoveryStrategy.REPLAN.value] += 1
        context = context or {}
        recommendation = suggested_plan or context.get("suggested_plan") or "regenerate_plan"
        logger.info("Recovery replan requested for task %s", task_id)
        return StrategyResult(
            strategy=RecoveryStrategy.REPLAN,
            outcome=StrategyOutcome.SUCCESS,
            task_id=task_id,
            recommendation=recommendation,
            details={"context_keys": list(context.keys()), "suggested_plan": suggested_plan},
        )

    def substitute(self, task_id: str, alternatives: list[str],
                   preference: str | None = None) -> StrategyResult:
        """Swap a failed tool/resource for an alternative from ``alternatives``."""
        self._strategy_counts[RecoveryStrategy.SUBSTITUTE.value] += 1
        alternatives = list(alternatives or [])
        if not alternatives:
            return StrategyResult(
                strategy=RecoveryStrategy.SUBSTITUTE,
                outcome=StrategyOutcome.FAILED,
                task_id=task_id,
                error="no alternatives available",
                recommendation="manually select alternative",
            )
        chosen = preference if preference in alternatives else alternatives[0]
        logger.info("Recovery substitute for task %s -> %s", task_id, chosen)
        return StrategyResult(
            strategy=RecoveryStrategy.SUBSTITUTE,
            outcome=StrategyOutcome.SUCCESS,
            task_id=task_id,
            recommendation=chosen,
            details={"alternatives": alternatives, "chosen": chosen},
        )

    def escalate(self, task_id: str, reason: str, severity: str = "medium") -> StrategyResult:
        """Escalate a failure to a human / higher authority."""
        self._strategy_counts[RecoveryStrategy.ESCALATE.value] += 1
        self._escalation_log.append({
            "task_id": task_id, "reason": reason, "severity": severity,
            "timestamp": time.time(),
        })
        logger.warning("Escalating task %s [%s]: %s", task_id, severity, reason)
        return StrategyResult(
            strategy=RecoveryStrategy.ESCALATE,
            outcome=StrategyOutcome.ESCALATED,
            task_id=task_id,
            recommendation="await_human_review",
            details={"severity": severity, "reason": reason},
        )

    # -- orchestrator -------------------------------------------------------
    async def recover(self, task_id: str,
                      error: Exception | str,
                      *, operation: Callable[..., Any] | None = None,
                      context: dict[str, Any] | None = None,
                      alternatives: list[str] | None = None,
                      severity: str = "medium",
                      strategies: list[str] | None = None,
                      max_retries: int = 3, backoff_base: float = 1.0,
                      checkpoint_state: dict[str, Any] | None = None) -> RecoveryRecord:
        """Classify a failure and apply the appropriate recovery strategy.

        Returns a ``RecoveryRecord`` describing what was tried and the outcome.
        """
        failure_class = self.classify_failure(error)
        strategy = self.select_strategy(failure_class)

        # Optional allow-list: if a strategy is disallowed, fall back to escalate.
        strategy_names = {s.value for s in RecoveryStrategy}
        if strategies is not None:
            allowed = {s.lower() for s in strategies} & strategy_names
            if strategy.value not in allowed:
                strategy = RecoveryStrategy.ESCALATE

        # persist a checkpoint capturing the failure context for rollback
        if checkpoint_state is not None:
            self.create_checkpoint(
                task_id, checkpoint_state,
                failure_class=failure_class.value, strategy=strategy.value,
            )

        record = RecoveryRecord(
            record_id=str(uuid.uuid4()),
            task_id=task_id,
            failure_class=failure_class,
            error=str(error),
            strategy=strategy,
            context=context or {},
        )
        self._records[record.record_id] = record
        self._recovery_attempts += 1

        try:
            if strategy == RecoveryStrategy.RETRY and operation is not None:
                record.result = await self.retry(
                    operation, max_attempts=max_retries, backoff_base=backoff_base,
                )
            elif strategy == RecoveryStrategy.SUBSTITUTE:
                record.result = self.substitute(task_id, alternatives or [])
            elif strategy == RecoveryStrategy.REPLAN:
                record.result = self.replan(task_id, context)
            elif strategy == RecoveryStrategy.ESCALATE:
                record.result = self.escalate(task_id, str(error), severity=severity)
            else:
                record.result = self.escalate(
                    task_id, str(error), severity="high",
                )
        except Exception as e:
            record.error_detail = str(e)
            record.result = self.escalate(
                task_id, f"{error} | recovery raised: {e}", severity="high",
            )

        outcome = record.result.outcome
        record.outcome_value = outcome  # alias kept simple
        record.resolution = outcome == StrategyOutcome.SUCCESS.value
        if outcome == StrategyOutcome.ESCALATED.value:
            record.status = "escalated"
        elif record.resolution:
            record.status = "resolved"
        else:
            record.status = "failed"
        record.completed_at = time.time()
        logger.info("Recovery %s -> %s (%s)",
                    task_id, strategy.value, record.status)
        return record

    def get_record(self, record_id: str) -> RecoveryRecord | None:
        return self._records.get(record_id)

    def recovery_history(self, task_id: str | None = None) -> list[RecoveryRecord]:
        records = self._records.values()
        if task_id:
            records = [r for r in records if r.task_id == task_id]
        return sorted(records, key=lambda r: r.started_at, reverse=True)

    def get_escalations(self) -> list[dict[str, Any]]:
        return list(self._escalation_log)

    async def flush(self):
        """Persist in-memory recovery artifacts (no-op when no durable sink)."""
        # Checkpoints & records are kept in-memory; subclasses/kernels may wire
        # a state_manager for durability. Here we simply ensure buffers are empty.
        logger.debug("Recovery engine flush: %d checkpoints, %d records",
                      len(self._checkpoints), len(self._records))

    # -- capabilities & health ---------------------------------------------
    def get_capabilities(self) -> list[str]:
        return list(getattr(self.manifest, "capabilities", []))

    async def health(self) -> dict[str, Any]:
        """Return health status. Contains a ``status`` key for the kernel."""
        healthy = self.state in (PluginState.LOADED, PluginState.RUNNING)
        status = "healthy" if healthy else "degraded"
        return {
            "status": status,
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "checkpoints": len(self._checkpoints),
            "recovery_attempts": self._recovery_attempts,
            "escalations": len(self._escalation_log),
            "strategy_counts": dict(self._strategy_counts),
            "capabilities": self.get_capabilities(),
        }


# ===========================================================================
# Factory
# ===========================================================================

async def create(kernel: Any = None) -> RecoveryEngine:
    """Async factory — creates, loads and starts the recovery engine.

    Contract used by ``HermesKernel._load_core_plugins`` (``module.create(self)``).
    """
    engine = RecoveryEngine(kernel=kernel)
    await engine.load()
    await engine.start()
    return engine


# Alias honoring the PluginManager ``Plugin`` class contract too.
Plugin = RecoveryEngine
