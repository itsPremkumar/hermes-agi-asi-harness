"""Production-hardened layer — circuit breaker, graceful degradation,
canary deployment, drift detection, auto-rollback."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from core.action.safety_envelope import SafetyEnvelope, SafetyEnvelopeManager
from core.action.transaction import (
    RollbackType,
    TransactionModel,
    TransactionState,
)

try:
    from plugins.circuit_breaker import (
        CircuitBreakerPlugin,
        CircuitBreakerConfig,
        CircuitState,
    )
    HAS_CB = True
except ImportError:
    HAS_CB = False

logger = logging.getLogger("hermes_production")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DRIFT_THRESHOLD = 0.15       # 15% deviation triggers alert
DEFAULT_DRIFT_WINDOW = 200           # observations
DEFAULT_CANARY_WEIGHT = 0.05         # 5% traffic to canary
DEFAULT_CANARY_MIN_OBSEVATIONS = 50  # observations before promoting
DEFAULT_AUTO_ROLLBACK_SCORE = 0.70   # safety score below which to rollback
DEFAULT_MODEL_WINDOW = 50            # recent predictions for drift


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class RollbackReason(str, Enum):
    SAFETY_VIOLATION = "safety_violation"
    DRIFT_EXCEEDED = "drift_exceeded"
    CIRCUIT_OPEN = "circuit_open"
    ERROR_RATE_SPIKE = "error_rate_spike"
    MANUAL = "manual"
    HEALTH_CHECK_FAILED = "health_check_failed"


@dataclass
class DeploymentVersion:
    version: str
    model_hash: str
    weight: float = 0.0
    active: bool = False
    deployed_at: float = 0.0
    prediction_count: int = 0
    safety_score: float = 1.0


@dataclass
class DriftObservation:
    timestamp: float
    predicted: Any
    actual: Any
    model_version: str
    error: float = 0.0


@dataclass
class CanaryResult:
    version: str
    promoted: bool
    observations: int
    avg_error: float
    safety_score: float
    message: str = ""


@dataclass
class RollbackRecord:
    version: str
    reason: RollbackReason
    timestamp: float
    detail: str = ""


# ---------------------------------------------------------------------------
# Graceful Degradation — feature-flag-driven fallbacks
# ---------------------------------------------------------------------------

class GracefulDegradationManager:
    """Feature-flag-based graceful degradation.

    Features can be enabled/disabled at runtime. When a feature is disabled
    or its circuit is open, the registered fallback is invoked automatically.
    """

    def __init__(self, circuit_breaker: Optional[CircuitBreakerPlugin] = None):
        self._features: dict[str, bool] = {}
        self._fallbacks: dict[str, Callable] = {}
        self._cb = circuit_breaker
        self._feature_log: list[dict[str, Any]] = []

    def register_feature(self, name: str, enabled: bool = True) -> None:
        self._features[name] = enabled
        logger.info("Feature registered: %s (enabled=%s)", name, enabled)

    def disable_feature(self, name: str) -> None:
        self._features[name] = False
        logger.warning("Feature DISABLED: %s", name)
        self._log_event("disable", name)

    def enable_feature(self, name: str) -> None:
        self._features[name] = True
        logger.info("Feature ENABLED: %s", name)
        self._log_event("enable", name)

    def is_enabled(self, name: str) -> bool:
        return self._features.get(name, True)

    def register_fallback(self, feature: str, fallback: Callable) -> None:
        self._fallbacks[feature] = fallback

    async def execute(
        self,
        feature: str,
        primary: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """Execute primary if feature enabled and circuit closed; else fallback."""
        if not self.is_enabled(feature):
            return await self._invoke_fallback(feature, *args, **kwargs)

        if self._cb:
            health = self._cb.get_plane_health(feature)
            if health.get("circuit_state") == "open":
                logger.warning(
                    "Circuit OPEN for %s — using fallback", feature
                )
                return await self._invoke_fallback(feature, *args, **kwargs)

        try:
            result = await primary(*args, **kwargs) if asyncio.iscoroutinefunction(primary) else primary(*args, **kwargs)
            return result, False
        except Exception as e:
            logger.warning("Primary failed for %s: %s — trying fallback", feature, e)
            return await self._invoke_fallback(feature, *args, **kwargs)

    async def _invoke_fallback(self, feature: str, *args: Any, **kwargs: Any) -> tuple[Any, bool]:
        fallback = self._fallbacks.get(feature)
        if fallback:
            result = await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
            return result, True
        return None, True

    def get_status(self) -> dict[str, Any]:
        return {
            "features": dict(self._features),
            "registered_fallbacks": list(self._fallbacks.keys()),
            "events": self._feature_log[-20:],
        }

    def _log_event(self, action: str, feature: str) -> None:
        self._feature_log.append({
            "action": action, "feature": feature, "timestamp": time.time(),
        })


# ---------------------------------------------------------------------------
# Canary Deployment
# ---------------------------------------------------------------------------

class CanaryDeploymentManager:
    """Gradual rollout with traffic weighting and safety validation."""

    def __init__(
        self,
        safety_envelope: Optional[SafetyEnvelopeManager] = None,
        min_observations: int = DEFAULT_CANARY_MIN_OBSEVATIONS,
    ):
        self._versions: dict[str, DeploymentVersion] = {}
        self._safety_env = safety_envelope
        self._min_obs = min_observations
        self._current_canary: str | None = None
        self._results: list[CanaryResult] = []

    def register_version(
        self,
        version: str,
        model_hash: str,
        weight: float = 0.0,
        safety_score: float = 1.0,
    ) -> None:
        self._versions[version] = DeploymentVersion(
            version=version,
            model_hash=model_hash,
            weight=weight,
            safety_score=safety_score,
        )
        logger.info("Version registered: %s (hash=%s, weight=%.2f)", version, model_hash[:8], weight)

    def set_traffic(self, version: str, weight: float) -> None:
        if version not in self._versions:
            raise ValueError(f"Unknown version: {version}")
        if not 0.0 <= weight <= 1.0:
            raise ValueError("Weight must be in [0, 1]")
        self._versions[version].weight = weight
        self._versions[version].active = weight > 0
        logger.info("Traffic set: %s = %.2f", version, weight)

    def select_version(self) -> str:
        """Weighted random selection among active versions."""
        import random
        total = sum(v.weight for v in self._versions.values() if v.weight > 0)
        if total == 0:
            # Return the highest-weight stable version
            stable = [v for v in self._versions.values() if v.weight == 0]
            if stable:
                return stable[0].version
            return list(self._versions.values())[0].version
        r = random.random() * total
        cumulative = 0.0
        for v in self._versions.values():
            if v.weight <= 0:
                continue
            cumulative += v.weight
            if r <= cumulative:
                return v.version
        return list(self._versions.values())[0].version

    def record_prediction(
        self, version: str, predicted: Any, actual: Any, safety_score: float = 1.0
    ) -> None:
        if version not in self._versions:
            return
        v = self._versions[version]
        v.prediction_count += 1
        v.safety_score = safety_score

    def evaluate_canary(self, version: str) -> CanaryResult:
        """Evaluate canary against safety thresholds."""
        if version not in self._versions:
            return CanaryResult(version, False, 0, 0.0, 0.0, "unknown version")

        v = self._versions[version]

        # Safety gate
        if v.safety_score < DEFAULT_AUTO_ROLLBACK_SCORE:
            return CanaryResult(
                version, False, v.prediction_count, 0.0, v.safety_score,
                f"SAFETY_GATE_FAILED (score={v.safety_score:.2f})",
            )

        # Minimum observations
        if v.prediction_count < self._min_obs:
            return CanaryResult(
                version, False, v.prediction_count, 0.0, v.safety_score,
                f"INSUFFICIENT_OBSERVATIONS ({v.prediction_count}/{self._min_obs})",
            )

        # Promote
        self._current_canary = version
        return CanaryResult(
            version, True, v.prediction_count, 0.0, v.safety_score,
            "PROMOTED",
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "versions": {
                k: {
                    "weight": v.weight,
                    "active": v.active,
                    "predictions": v.prediction_count,
                    "safety_score": v.safety_score,
                    "deployed_at": v.deployed_at,
                }
                for k, v in self._versions.items()
            },
            "current_canary": self._current_canary,
        }


# ---------------------------------------------------------------------------
# Drift Detection
# ---------------------------------------------------------------------------

class DriftDetector:
    """Monitors model predictions vs actuals for statistical drift."""

    def __init__(
        self,
        threshold: float = DEFAULT_DRIFT_THRESHOLD,
        window_size: int = DEFAULT_DRIFT_WINDOW,
        model_window: int = DEFAULT_MODEL_WINDOW,
    ):
        self._threshold = threshold
        self._window_size = window_size
        self._model_window = model_window
        self._observations: list[DriftObservation] = []
        self._baseline_stats: dict[str, dict[str, float]] = {}
        self._drift_alerts: list[dict[str, Any]] = []
        self._drift_scores: dict[str, float] = {}

    def set_baseline(self, model_version: str, mean: float, std: float) -> None:
        self._baseline_stats[model_version] = {"mean": mean, "std": std}
        logger.info("Baseline set for %s: mean=%.4f std=%.4f", model_version, mean, std)

    def record(
        self, model_version: str, predicted: float, actual: float
    ) -> float:
        error = abs(predicted - actual)
        obs = DriftObservation(
            timestamp=time.time(),
            predicted=predicted,
            actual=actual,
            model_version=model_version,
            error=error,
        )
        self._observations.append(obs)
        if len(self._observations) > self._window_size * 10:
            self._observations = self._observations[-self._window_size * 10:]

        # Compute rolling drift score for this version
        version_obs = [o for o in self._observations if o.model_version == model_version][-self._model_window:]
        if len(version_obs) >= 10:
            errors = [o.error for o in version_obs]
            mean_err = sum(errors) / len(errors)
            max_err = max(errors)
            drift_score = min(mean_err / max(1e-6, abs(predicted)), 1.0)
            self._drift_scores[model_version] = drift_score

            if drift_score > self._threshold:
                alert = {
                    "model_version": model_version,
                    "drift_score": drift_score,
                    "threshold": self._threshold,
                    "mean_error": mean_err,
                    "max_error": max_err,
                    "timestamp": time.time(),
                }
                self._drift_alerts.append(alert)
                logger.warning("DRIFT DETECTED for %s: score=%.4f threshold=%.4f", model_version, drift_score, self._threshold)

        return error

    def get_drift_score(self, model_version: str) -> float:
        return self._drift_scores.get(model_version, 0.0)

    def is_drifted(self, model_version: str) -> bool:
        return self._drift_scores.get(model_version, 0.0) > self._threshold

    def get_drift_report(self) -> dict[str, Any]:
        return {
            "threshold": self._threshold,
            "total_observations": len(self._observations),
            "drift_scores": dict(self._drift_scores),
            "recent_alerts": self._drift_alerts[-10:],
            "baselines": self._baseline_stats,
        }


# ---------------------------------------------------------------------------
# Auto-Rollback
# ---------------------------------------------------------------------------

class AutoRollbackManager:
    """Automatic rollback on safety violations or performance degradation."""

    def __init__(
        self,
        transaction_model: Optional[TransactionModel] = None,
        safety_envelope: Optional[SafetyEnvelopeManager] = None,
        drift_detector: Optional[DriftDetector] = None,
        default_score_threshold: float = DEFAULT_AUTO_ROLLBACK_SCORE,
    ):
        self._tx = transaction_model or TransactionModel()
        self._safety_env = safety_envelope
        self._drift = drift_detector
        self._threshold = default_score_threshold
        self._history: list[RollbackRecord] = []
        self._active_rollback: bool = False
        self._rollback_target: str = ""
        self._safety_hooks: list[Callable] = []

    def register_safety_hook(self, hook: Callable) -> None:
        """Register a callable that returns True when rollback is needed."""
        self._safety_hooks.append(hook)

    def check_safety_hooks(self) -> Optional[str]:
        for hook in self._safety_hooks:
            try:
                result = hook()
                if result is True or (isinstance(result, str) and result):
                    return result if isinstance(result, str) else "safety_hook_triggered"
            except Exception as e:
                logger.error("Safety hook error: %s", e)
        return None

    def should_rollback(
        self,
        version: str,
        safety_score: float,
        drift_score: float = 0.0,
        error_rate: float = 0.0,
    ) -> tuple[bool, RollbackReason]:
        if safety_score < self._threshold:
            return True, RollbackReason.SAFETY_VIOLATION
        if self._drift and self._drift.is_drifted(version):
            return True, RollbackReason.DRIFT_EXCEEDED
        if error_rate > 0.5:
            return True, RollbackReason.ERROR_RATE_SPIKE
        return False, RollbackReason.MANUAL

    async def execute_rollback(
        self,
        version: str,
        reason: RollbackReason,
        detail: str = "",
    ) -> bool:
        """Perform rollback via transaction compensation."""
        logger.warning("ROLLBACK initiated for %s: reason=%s detail=%s", version, reason.value, detail)
        self._active_rollback = True
        self._rollback_target = version

        # Record rollback
        record = RollbackRecord(
            version=version,
            reason=reason,
            timestamp=time.time(),
            detail=detail,
        )
        self._history.append(record)

        # Execute compensation via transaction model
        tx_id = self._tx.begin(transaction_id=f"rollback_{version}_{int(time.time())}")
        self._tx.add_action(
            tx_id,
            type="rollback",
            target=version,
            parameters={"reason": reason.value, "detail": detail},
            rollback_type=RollbackType.COMPENSATION,
        )
        result = self._tx.commit(tx_id)

        if self._safety_env:
            for env_id, env in self._safety_env.envelopes.items():
                env.emergency_stop = True
                logger.critical("Emergency stop triggered on envelope %s for version %s", env_id, version)

        self._active_rollback = False
        self._rollback_target = ""
        return result.success

    def get_rollback_history(self) -> list[dict[str, Any]]:
        return [
            {
                "version": r.version,
                "reason": r.reason.value,
                "timestamp": r.timestamp,
                "detail": r.detail,
            }
            for r in self._history
        ]

    @property
    def active_rollback(self) -> bool:
        return self._active_rollback


# ---------------------------------------------------------------------------
# Safety Rollback Trigger — ties safety envelope violations to rollback
# ---------------------------------------------------------------------------

class SafetyRollbackTrigger:
    """Monitors safety envelope and triggers rollback on violations."""

    def __init__(self, rollback_manager: AutoRollbackManager):
        self._rollback = rollback_manager
        self._violation_count: int = 0
        self._violation_threshold: int = 3

    def check_envelope(
        self,
        envelope_check_result: Any,  # EnvelopeCheck
        version: str,
    ) -> bool:
        """Check an envelope check result; trigger rollback if violated."""
        if hasattr(envelope_check_result, "passed") and not envelope_check_result.passed:
            self._violation_count += 1
            violations = [v.value for v in envelope_check_result.violations]
            logger.warning(
                "Safety violation #%d for %s: %s",
                self._violation_count, version, violations,
            )
            if self._violation_count >= self._violation_threshold:
                asyncio.create_task(
                    self._rollback.execute_rollback(
                        version,
                        RollbackReason.SAFETY_VIOLATION,
                        f"Violations: {violations}",
                    )
                )
                return True
        else:
            self._violation_count = max(0, self._violation_count - 1)
        return False

    @property
    def violation_count(self) -> int:
        return self._violation_count


# ---------------------------------------------------------------------------
# Orchestrator — ProductionHardenedLayer
# ---------------------------------------------------------------------------

class ProductionHardenedLayer:
    """Unified production-hardened layer combining all five patterns.

    Circuit Breaker    — failure isolation via CircuitBreakerPlugin
    Graceful Degradation — feature-flag fallbacks
    Canary Deployment  — gradual rollout with safety gates
    Drift Detection    — model prediction vs actual monitoring
    Auto-Rollback      — automatic rollback on safety/drift violations
    """

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreakerPlugin] = None,
        safety_envelope: Optional[SafetyEnvelopeManager] = None,
    ):
        self._cb = circuit_breaker
        self._safety_env = safety_envelope or SafetyEnvelopeManager()

        self.degradation = GracefulDegradationManager(circuit_breaker)
        self.canary = CanaryDeploymentManager(self._safety_env)
        self.drift = DriftDetector()
        self.rollback = AutoRollbackManager(
            safety_envelope=self._safety_env, drift_detector=self.drift,
        )
        self.safety_trigger = SafetyRollbackTrigger(self.rollback)

        self._tx = TransactionModel()
        self._initialized = False
        self._deploy_history: list[dict[str, Any]] = []

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize from configuration dict."""
        drift_cfg = config.get("drift_detection", {})
        self.drift = DriftDetector(
            threshold=drift_cfg.get("threshold", DEFAULT_DRIFT_THRESHOLD),
            window_size=drift_cfg.get("window_size", DEFAULT_DRIFT_WINDOW),
            model_window=drift_cfg.get("model_window", DEFAULT_MODEL_WINDOW),
        )

        canary_cfg = config.get("canary", {})
        self.canary = CanaryDeploymentManager(
            self._safety_env,
            min_observations=canary_cfg.get("min_observations", DEFAULT_CANARY_MIN_OBSEVATIONS),
        )

        rollback_cfg = config.get("rollback", {})
        self.rollback = AutoRollbackManager(
            safety_envelope=self._safety_env,
            drift_detector=self.drift,
            default_score_threshold=rollback_cfg.get("score_threshold", DEFAULT_AUTO_ROLLBACK_SCORE),
        )

        self.safety_trigger = SafetyRollbackTrigger(self.rollback)

        self._initialized = True
        logger.info("ProductionHardenedLayer initialized")

    async def execute_with_protection(
        self,
        feature: str,
        version: str,
        primary: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool, dict[str, Any]]:
        """Execute an operation with full production protection.

        Returns (result, used_fallback, metadata).
        """
        metadata: dict[str, Any] = {
            "feature": feature, "version": version,
            "rollback_triggered": False, "drift_detected": False,
        }

        # 1. Graceful degradation check
        result, used_fb = await self.degradation.execute(feature, primary, *args, **kwargs)
        if used_fb:
            metadata["used_fallback"] = True
            return result, True, metadata

        # 2. Drift check before accepting result
        if isinstance(result, (int, float)):
            drift_score = self.drift.get_drift_score(version)
            metadata["drift_score"] = drift_score
            if self.drift.is_drifted(version):
                metadata["drift_detected"] = True
                logger.warning("Drift detected for %s before accept", version)

        # 3. Canary tracking
        self.canary.record_prediction(version, result, result, safety_score=1.0)

        # 4. Safety hooks check
        hook_result = self.rollback.check_safety_hooks()
        if hook_result:
            await self.rollback.execute_rollback(version, RollbackReason.SAFETY_VIOLATION, hook_result)
            metadata["rollback_triggered"] = True
            return None, True, metadata

        return result, False, metadata

    def get_dashboard(self) -> dict[str, Any]:
        """Aggregate dashboard for all five subsystems."""
        return {
            "degradation": self.degradation.get_status(),
            "canary": self.canary.get_status(),
            "drift": self.drift.get_drift_report(),
            "rollback": {
                "history": self.rollback.get_rollback_history(),
                "active": self.rollback.active_rollback,
                "threshold": self.rollback._threshold,
            },
            "safety_trigger_violations": self.safety_trigger.violation_count,
            "initialized": self._initialized,
            "timestamp": time.time(),
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_instance: Optional[ProductionHardenedLayer] = None


def get_production_layer(
    circuit_breaker: Optional[CircuitBreakerPlugin] = None,
    safety_envelope: Optional[SafetyEnvelopeManager] = None,
) -> ProductionHardenedLayer:
    """Get or create the global production-hardened layer singleton."""
    global _instance
    if _instance is None:
        _instance = ProductionHardenedLayer(circuit_breaker, safety_envelope)
    return _instance