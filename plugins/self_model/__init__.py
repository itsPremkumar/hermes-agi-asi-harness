"""
Self-Model Plugin — v7 §50

Empirical capability measurement, calibration tracking, success/latency/error
stats per task class, model, and provider. Feeds planner, model router,
curriculum engine, risk policy, and evolution engine.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class TaskClass(str, Enum):
    CODING = "coding"
    RESEARCH = "research"
    REASONING = "reasoning"
    VERIFICATION = "verification"
    CREATION = "creation"
    ANALYSIS = "analysis"
    WRITING = "writing"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    GENERATION = "generation"
    CLASSIFICATION = "classification"
    TOOL_USE = "tool_use"
    PLANNING = "planning"
    OTHER = "other"
    GENERAL = "general"


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    UNKNOWN = "unknown"


class CalibrationStatus(str, Enum):
    WELL_CALIBRATED = "well_calibrated"
    OKAY_CALIBRATED = "okay_calibrated"
    POORLY_CALIBRATED = "poorly_calibrated"
    UNCALIBRATED = "uncalibrated"


@dataclass(frozen=True)
class CapabilityMeasurement:
    task_class: TaskClass
    model: str
    provider: str
    success: bool
    latency_ms: float
    confidence: float
    actual_correct: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_type: str = ""
    prompt_hash: str = ""


@dataclass(frozen=True)
class CalibrationPoint:
    predicted_confidence: float
    actual_accuracy: float
    sample_count: int
    brier_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LatencyStats:
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    mean: float = 0.0
    stddev: float = 0.0
    min: float = 0.0
    max: float = 0.0
    n: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "p50": round(self.p50, 4),
            "p90": round(self.p90, 4),
            "p95": round(self.p95, 4),
            "p99": round(self.p99, 4),
            "mean": round(self.mean, 4),
            "stddev": round(self.stddev, 4),
            "min": round(self.min, 4),
            "max": round(self.max, 4),
            "n": self.n,
        }


@dataclass
class ErrorPattern:
    error_type: str
    count: int
    task_classes: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "count": self.count,
            "task_classes": list(self.task_classes),
            "models": list(self.models),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class CapabilityRecord:
    task_class: TaskClass
    model: str
    provider: str
    success_rate: float = 0.0
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_latency_ms: float = 0.0
    latency_distribution: LatencyStats = field(default_factory=LatencyStats)
    calibration_brier: float = 0.0
    calibration_error: float = 0.0
    error_patterns: dict[str, int] = field(default_factory=dict)
    confidence_mean: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_class": self.task_class.value,
            "model": self.model,
            "provider": self.provider.value,
            "success_rate": round(self.success_rate, 4),
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_latency_ms": round(self.avg_latency_ms, 4),
            "latency_distribution": self.latency_distribution.to_dict(),
            "calibration_brier": round(self.calibration_brier, 4),
            "calibration_error": round(self.calibration_error, 4),
            "error_patterns": dict(self.error_patterns),
            "confidence_mean": round(self.confidence_mean, 4),
            "last_updated": self.last_updated.isoformat(),
        }


def _percentile(sorted_data: list[float], p: int) -> float:
    """Nearest-rank percentile on pre-sorted data."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    k = max(0, min(int(round(p / 100 * n)) - 1, n - 1))
    return sorted_data[k]


class SelfModel:
    """Empirical self-model tracking capability measurements with calibration.

    Records outcomes per (task_class, model, provider) and computes:
      - Success rates
      - Latency distributions (p50/p90/p95/p99, mean, stddev)
      - Calibration (Brier score, calibration error, status)
      - Error pattern frequencies
    """

    def __init__(self, history_size: int = 10_000):
        self.measurements: deque[CapabilityMeasurement] = deque(maxlen=history_size)
        self.calibration_history: deque[CalibrationPoint] = deque(maxlen=1000)
        self._by_task_class: dict[TaskClass, list[CapabilityMeasurement]] = defaultdict(list)
        self._by_model: dict[str, list[CapabilityMeasurement]] = defaultdict(list)
        self._by_provider: dict[str, list[CapabilityMeasurement]] = defaultdict(list)
        self._by_error: dict[str, list[CapabilityMeasurement]] = defaultdict(list)
        self._error_patterns: dict[str, ErrorPattern] = {}

    def record(
        self,
        task_class: TaskClass | str,
        model: str,
        provider: Provider | str,
        success: bool,
        latency_ms: float,
        confidence: float = 0.5,
        actual_correct: bool | None = None,
        error_type: str = "",
        prompt_hash: str = "",
    ) -> CapabilityMeasurement:
        """Record a single task execution outcome."""
        tc = TaskClass(task_class) if isinstance(task_class, str) else task_class
        pr = Provider(provider) if isinstance(provider, str) else provider
        actual = actual_correct if actual_correct is not None else success

        m = CapabilityMeasurement(
            task_class=tc,
            model=model,
            provider=pr.value,
            success=success,
            latency_ms=latency_ms,
            confidence=confidence,
            actual_correct=actual,
            error_type=error_type,
            prompt_hash=prompt_hash,
        )

        self.measurements.append(m)
        self._by_task_class[tc].append(m)
        self._by_model[model].append(m)
        self._by_provider[pr.value].append(m)
        if error_type:
            self._by_error[error_type].append(m)
            self._record_error_pattern(error_type, tc, model)

        return m

    def _record_error_pattern(self, error_type: str, task_class: TaskClass, model: str) -> None:
        now = datetime.utcnow()
        if error_type not in self._error_patterns:
            self._error_patterns[error_type] = ErrorPattern(
                error_type=error_type, count=0, first_seen=now,
            )
        ep = self._error_patterns[error_type]
        ep.count += 1
        ep.last_seen = now
        if task_class.value not in ep.task_classes:
            ep.task_classes.append(task_class.value)
        if model not in ep.models:
            ep.models.append(model)

    # --- Success rates ---------------------------------------------------

    def success_rate(
        self, task_class: TaskClass | str | None = None, model: str | None = None,
        provider: Provider | str | None = None,
    ) -> float:
        measurements = self._filter(task_class, model, provider)
        if not measurements:
            return 0.0
        return sum(1 for m in measurements if m.success) / len(measurements)

    def success_rate_by_task_class(self) -> dict[str, float]:
        return {tc.value: self.success_rate(task_class=tc) for tc in TaskClass}

    def success_rate_by_model(self) -> dict[str, float]:
        return {m: self.success_rate(model=m) for m in sorted(self._by_model)}

    # --- Latency distributions --------------------------------------------

    def _percentile(sorted_data: list[float], p: int) -> float:
        if not sorted_data:
            return 0.0
        n = len(sorted_data)
        k = max(0, min(int(round(p / 100 * n)) - 1, n - 1))
        return sorted_data[k]

    def latency_distribution(
        self,
        task_class: TaskClass | str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
    ) -> LatencyStats:
        measurements = self._filter(task_class, model, provider)
        if not measurements:
            return LatencyStats()
        latencies = sorted(m.latency_ms for m in measurements)
        n = len(latencies)
        mean = sum(latencies) / n
        variance = sum((x - mean) ** 2 for x in latencies) / max(1, n - 1)
        return LatencyStats(
            p50=_percentile(latencies, 50),
            p90=_percentile(latencies, 90),
            p95=_percentile(latencies, 95),
            p99=_percentile(latencies, 99),
            mean=mean,
            stddev=math.sqrt(variance),
            min=latencies[0],
            max=latencies[-1],
            n=n,
        )

    def latency_by_task_class(self) -> dict[str, LatencyStats]:
        return {tc.value: self.latency_distribution(task_class=tc) for tc in TaskClass}

    # --- Calibration tracking ---------------------------------------------

    def brier_score(
        self,
        task_class: TaskClass | str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
    ) -> float:
        """Brier score: mean((predicted - actual)^2). Lower = better calibration."""
        measurements = self._filter(task_class, model, provider)
        if not measurements:
            return 0.0
        return sum(
            (m.confidence - (1.0 if m.actual_correct else 0.0)) ** 2
            for m in measurements
        ) / len(measurements)

    def calibration_error(
        self,
        task_class: TaskClass | str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
        n_bins: int = 10,
    ) -> float:
        """Expected Calibration Error (ECE): weighted |predicted - actual| per bin."""
        measurements = self._filter(task_class, model, provider)
        if not measurements:
            return 0.0
        bins: dict[int, list[CapabilityMeasurement]] = defaultdict(list)
        for m in measurements:
            idx = min(int(m.confidence * n_bins), n_bins - 1)
            bins[idx].append(m)
        ece = 0.0
        total = len(measurements)
        for idx, bin_m in bins.items():
            weight = len(bin_m) / total
            avg_pred = (idx + 0.5) / n_bins
            acc = sum(1 for m in bin_m if m.actual_correct) / len(bin_m)
            ece += weight * abs(avg_pred - acc)
        return ece

    def calibration_curve(
        self,
        task_class: TaskClass | str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
        n_bins: int = 10,
    ) -> list[dict[str, Any]]:
        """Per-bin predicted vs actual accuracy for plotting the calibration curve."""
        measurements = self._filter(task_class, model, provider)
        if not measurements:
            return []
        bins: dict[int, list[CapabilityMeasurement]] = defaultdict(list)
        for m in measurements:
            idx = min(int(m.confidence * n_bins), n_bins - 1)
            bins[idx].append(m)
        curve = []
        for i in range(n_bins):
            bin_m = bins.get(i, [])
            if bin_m:
                avg_pred = (i + 0.5) / n_bins
                acc = sum(1 for m in bin_m if m.actual_correct) / len(bin_m)
                curve.append({
                    "bin_lower": i / n_bins,
                    "bin_upper": (i + 1) / n_bins,
                    "predicted": round(avg_pred, 4),
                    "actual": round(acc, 4),
                    "count": len(bin_m),
                })
        return curve

    def calibration_status(
        self, model: str | None = None,
    ) -> CalibrationStatus:
        cp = self.calibration(model=model)
        if cp.sample_count < 10:
            return CalibrationStatus.UNCALIBRATED
        if cp.brier_score < 0.15:
            return CalibrationStatus.WELL_CALIBRATED
        if cp.brier_score < 0.25:
            return CalibrationStatus.OKAY_CALIBRATED
        return CalibrationStatus.POORLY_CALIBRATED

    def calibration(
        self, model: str | None = None,
    ) -> CalibrationPoint:
        """Aggregate calibration point for a model (or all)."""
        measurements = self._filter(model=model)
        if len(measurements) < 10:
            return CalibrationPoint(
                predicted_confidence=0.0, actual_accuracy=0.0,
                sample_count=len(measurements), brier_score=float("inf"),
            )
        bins: dict[int, list[bool]] = defaultdict(list)
        for m in measurements:
            bin_idx = min(int(m.confidence * 10), 9)
            bins[bin_idx].append(m.actual_correct)
        total_brier = 0.0
        total_samples = 0
        for bin_idx, outcomes in bins.items():
            predicted = (bin_idx + 0.5) / 10.0
            actual = sum(outcomes) / len(outcomes)
            brier = (predicted - actual) ** 2
            total_brier += brier * len(outcomes)
            total_samples += len(outcomes)
        avg_brier = total_brier / total_samples if total_samples > 0 else float("inf")
        avg_accuracy = sum(1 for m in measurements if m.actual_correct) / len(measurements)
        return CalibrationPoint(
            predicted_confidence=avg_accuracy,
            actual_accuracy=avg_accuracy,
            sample_count=len(measurements),
            brier_score=avg_brier,
        )

    # --- Error patterns ---------------------------------------------------

    def top_errors(
        self,
        task_class: TaskClass | str | None = None,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        measurements = self._filter(task_class)
        error_counts: dict[str, int] = defaultdict(int)
        for m in measurements:
            if m.error_type:
                error_counts[m.error_type] += 1
        return sorted(error_counts.items(), key=lambda x: -x[1])[:limit]

    def error_patterns(
        self,
        task_class: TaskClass | str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Top error patterns by frequency, optionally filtered."""
        patterns = list(self._error_patterns.values())
        if task_class or model or provider:
            filtered = []
            for ep in patterns:
                outcomes = self._filter(task_class, model, provider, ep.error_type)
                if outcomes:
                    filtered.append(ErrorPattern(
                        error_type=ep.error_type,
                        count=len(outcomes),
                        task_classes=ep.task_classes,
                        models=ep.models,
                        first_seen=ep.first_seen,
                        last_seen=ep.last_seen,
                    ))
            patterns = filtered
        patterns.sort(key=lambda p: p.count, reverse=True)
        return [p.to_dict() for p in patterns[:limit]]

    # --- Aggregate capability records -------------------------------------

    def measure(
        self,
        task_class: TaskClass | str,
        model: str,
        provider: Provider | str = Provider.UNKNOWN,
    ) -> CapabilityRecord:
        """Compute full capability measurement for a specific (task_class, model, provider)."""
        pr = Provider(provider) if isinstance(provider, str) else provider
        measurements = self._filter(task_class, model, pr)
        if not measurements:
            raise ValueError(f"No outcomes recorded for ({task_class}, {model}, {pr})")

        successes = [m for m in measurements if m.success]
        latencies = [m.latency_ms for m in measurements]
        confidences = [m.confidence for m in measurements]
        error_counts: dict[str, int] = defaultdict(int)
        for m in measurements:
            if m.error_type:
                error_counts[m.error_type] += 1

        return CapabilityRecord(
            task_class=measurements[0].task_class,
            model=model,
            provider=pr,
            success_rate=len(successes) / len(measurements),
            total_tasks=len(measurements),
            successful_tasks=len(successes),
            failed_tasks=len(measurements) - len(successes),
            avg_latency_ms=sum(latencies) / len(latencies),
            latency_distribution=self.latency_distribution(task_class=measurements[0].task_class, model=model, provider=pr),
            calibration_brier=self.brier_score(task_class=measurements[0].task_class, model=model, provider=pr),
            calibration_error=self.calibration_error(task_class=measurements[0].task_class, model=model, provider=pr),
            error_patterns=dict(error_counts),
            confidence_mean=sum(confidences) / len(confidences) if confidences else 0.0,
            last_updated=datetime.utcnow(),
        )

    def all_measurements(self) -> list[CapabilityRecord]:
        keys = set((m.task_class, m.model, m.provider) for m in self.measurements)
        return [
            self.measure(task_class=k[0], model=k[1], provider=k[2])
            for k in sorted(keys, key=lambda x: (x[0].value, x[1], x[2]))
        ]

    # --- Summary ----------------------------------------------------------

    def capability_summary(self) -> dict[str, Any]:
        """Top-level summary across all tracked metrics."""
        cal = self.calibration()
        by_tc: dict[str, dict[str, Any]] = {}
        for tc in TaskClass:
            ms = self._filter(tc)
            if ms:
                by_tc[tc.value] = {
                    "count": len(ms),
                    "success_rate": self.success_rate(task_class=tc),
                    "avg_latency_ms": sum(m.latency_ms for m in ms) / len(ms),
                    "p95_latency_ms": _percentile(
                        sorted(m.latency_ms for m in ms), 95),
                }
        by_model: dict[str, dict[str, Any]] = {}
        for model in self._by_model:
            ms = self._by_model[model]
            by_model[model] = {
                "count": len(ms),
                "success_rate": self.success_rate(model=model),
                "avg_latency_ms": sum(m.latency_ms for m in ms) / len(ms),
            }
        return {
            "total_measurements": len(self.measurements),
            "overall_success_rate": self.success_rate(),
            "overall_avg_latency_ms": (
                sum(m.latency_ms for m in self.measurements) / len(self.measurements)
                if self.measurements else 0.0
            ),
            "overall_p95_latency_ms": (
                _percentile(sorted(m.latency_ms for m in self.measurements), 95)
                if self.measurements else 0.0
            ),
            "calibration_brier": cal.brier_score,
            "calibration_status": self.calibration_status().value,
            "by_task_class": by_tc,
            "by_model": by_model,
            "top_errors": self.top_errors(limit=5),
            "unique_error_patterns": len(self._error_patterns),
            "calibration_history_points": len(self.calibration_history),
        }

    def model_recommendation(self, task_class: TaskClass | str) -> dict[str, Any]:
        """Recommend the best model for a task class based on measured success rate."""
        tc = TaskClass(task_class) if isinstance(task_class, str) else task_class
        candidates: dict[str, dict[str, Any]] = {}
        for model, measurements in self._by_model.items():
            relevant = [m for m in measurements if m.task_class == tc]
            if len(relevant) >= 3:
                sr = sum(1 for m in relevant if m.success) / len(relevant)
                al = sum(m.latency_ms for m in relevant) / len(relevant)
                candidates[model] = {"success_rate": sr, "avg_latency_ms": al, "samples": len(relevant)}
        if not candidates:
            return {"recommendation": "no_data", "reason": "Insufficient history for this task class"}
        best = max(candidates.items(), key=lambda x: x[1]["success_rate"])
        return {
            "recommendation": best[0],
            "success_rate": best[1]["success_rate"],
            "avg_latency_ms": best[1]["avg_latency_ms"],
            "samples": best[1]["samples"],
            "all_candidates": candidates,
        }

    # --- Internal ---------------------------------------------------------

    def _filter(
        self,
        task_class: TaskClass | str | None = None,
        model: str | None = None,
        provider: Provider | str | None = None,
        error_type: str | None = None,
    ) -> list[CapabilityMeasurement]:
        result = list(self.measurements)
        if task_class is not None:
            tc = TaskClass(task_class) if isinstance(task_class, str) else task_class
            result = [m for m in result if m.task_class == tc]
        if model is not None:
            result = [m for m in result if m.model == model]
        if provider is not None:
            pr = Provider(provider) if isinstance(provider, str) else provider
            result = [m for m in result if m.provider == pr.value]
        if error_type is not None:
            result = [m for m in result if m.error_type == error_type]
        return result
