"""
State Estimation — Fuse observations into best current state estimate.

Raw observations are not truth. Hermes fuses:
  observations + historical state + tool responses + independent checks
→ best current state estimate with confidence
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ObservationSource(str, Enum):
    API = "api"
    DOM = "dom"
    VISION = "vision"
    TOOL_RESPONSE = "tool_response"
    USER_REPORT = "user_report"
    MONITORING = "monitoring"
    INFERENCE = "inference"


class StateConfidence(str, Enum):
    HIGH = "high"       # multiple independent sources agree
    MEDIUM = "medium"   # single source or partial agreement
    LOW = "low"         # conflicting sources or stale data
    UNKNOWN = "unknown" # no data


@dataclass
class Observation:
    id: str
    source: ObservationSource
    entity_id: str
    state: Dict[str, Any]
    timestamp: float
    confidence: float = 0.5
    raw_data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateEstimate:
    entity_id: str
    state: Dict[str, Any]
    confidence: StateConfidence
    confidence_score: float  # 0.0 to 1.0
    sources: List[ObservationSource]
    timestamp: float
    freshness_seconds: float
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)


class StateEstimator:
    """
    Fuse multiple observations into a best estimate of current state.
    
    Handles:
    - Source reliability weighting
    - Freshness decay
    - Conflict detection
    - Anomaly detection
    """

    # Source reliability weights (higher = more reliable)
    SOURCE_RELIABILITY: Dict[ObservationSource, float] = {
        ObservationSource.API: 0.9,
        ObservationSource.MONITORING: 0.85,
        ObservationSource.TOOL_RESPONSE: 0.8,
        ObservationSource.DOM: 0.7,
        ObservationSource.VISION: 0.6,
        ObservationSource.USER_REPORT: 0.5,
        ObservationSource.INFERENCE: 0.3,
    }

    def __init__(self):
        self.observations: Dict[str, List[Observation]] = {}  # entity_id → observations
        self.estimates: Dict[str, StateEstimate] = {}
        self._conflict_log: List[Dict[str, Any]] = []

    # ── Observation Ingestion ──────────────────────────────────────────────

    def add_observation(
        self,
        entity_id: str,
        source: ObservationSource,
        state: Dict[str, Any],
        confidence: float = 0.5,
        raw_data: Any = None,
        metadata: Dict[str, Any] = None,
    ) -> Observation:
        import uuid
        obs = Observation(
            id=str(uuid.uuid4()),
            source=source,
            entity_id=entity_id,
            state=state,
            timestamp=time.time(),
            confidence=confidence,
            raw_data=raw_data,
            metadata=metadata or {},
        )
        if entity_id not in self.observations:
            self.observations[entity_id] = []
        self.observations[entity_id].append(obs)
        return obs

    def get_observations(self, entity_id: str, limit: int = 20) -> List[Observation]:
        return self.observations.get(entity_id, [])[-limit:]

    # ── State Estimation ───────────────────────────────────────────────────

    def estimate(self, entity_id: str) -> Optional[StateEstimate]:
        """Produce best state estimate for an entity from all observations."""
        obs_list = self.observations.get(entity_id, [])
        if not obs_list:
            return None

        # Sort by timestamp (newest first)
        sorted_obs = sorted(obs_list, key=lambda o: o.timestamp, reverse=True)

        # Take recent observations (last 5 minutes)
        recent = [o for o in sorted_obs if time.time() - o.timestamp < 300]
        if not recent:
            recent = sorted_obs[:5]  # Use last 5 if none recent

        # Detect contradictions
        contradictions = self._detect_contradictions(recent)

        # Fuse state from multiple sources
        fused_state = self._fuse_states(recent)

        # Calculate confidence
        confidence_score = self._calculate_confidence(recent, contradictions)
        confidence = self._score_to_confidence(confidence_score)

        # Detect anomalies
        anomalies = self._detect_anomalies(entity_id, fused_state)

        estimate = StateEstimate(
            entity_id=entity_id,
            state=fused_state,
            confidence=confidence,
            confidence_score=confidence_score,
            sources=list(set(o.source for o in recent)),
            timestamp=time.time(),
            freshness_seconds=time.time() - recent[0].timestamp,
            contradictions=contradictions,
            anomalies=anomalies,
        )
        self.estimates[entity_id] = estimate
        return estimate

    def get_estimate(self, entity_id: str) -> Optional[StateEstimate]:
        return self.estimates.get(entity_id)

    # ── Fusion Logic ──────────────────────────────────────────────────────

    def _fuse_states(self, observations: List[Observation]) -> Dict[str, Any]:
        """Weighted fusion of state from multiple observations."""
        fused: Dict[str, Any] = {}
        weights: Dict[str, float] = {}

        for obs in observations:
            reliability = self.SOURCE_RELIABILITY.get(obs.source, 0.5)
            freshness = self._freshness_weight(obs.timestamp)
            weight = reliability * freshness * obs.confidence

            for key, value in obs.state.items():
                if key not in fused:
                    fused[key] = value
                    weights[key] = weight
                else:
                    # Weighted average for numeric values
                    if isinstance(value, (int, float)) and isinstance(fused[key], (int, float)):
                        total_w = weights[key] + weight
                        fused[key] = (fused[key] * weights[key] + value * weight) / total_w
                        weights[key] = total_w
                    # For non-numeric, keep the higher-confidence value
                    elif weight > weights[key]:
                        fused[key] = value
                        weights[key] = weight

        return fused

    def _freshness_weight(self, timestamp: float) -> float:
        """Decay weight based on age of observation."""
        age = time.time() - timestamp
        if age < 60:  # < 1 min
            return 1.0
        elif age < 300:  # < 5 min
            return 0.8
        elif age < 900:  # < 15 min
            return 0.5
        elif age < 3600:  # < 1 hour
            return 0.3
        else:
            return 0.1

    def _calculate_confidence(self, observations: List[Observation],
                               contradictions: List[Dict]) -> float:
        """Calculate overall confidence score."""
        if not observations:
            return 0.0

        # Base confidence from source reliability and freshness
        confidences = []
        for obs in observations:
            reliability = self.SOURCE_RELIABILITY.get(obs.source, 0.5)
            freshness = self._freshness_weight(obs.timestamp)
            confidences.append(reliability * freshness * obs.confidence)

        base = sum(confidences) / len(confidences)

        # Boost for multiple independent sources
        unique_sources = len(set(o.source for o in observations))
        independence_boost = min(0.2, unique_sources * 0.05)

        # Penalty for contradictions
        contradiction_penalty = len(contradictions) * 0.15

        return max(0.0, min(1.0, base + independence_boost - contradiction_penalty))

    def _score_to_confidence(self, score: float) -> StateConfidence:
        if score >= 0.8:
            return StateConfidence.HIGH
        elif score >= 0.5:
            return StateConfidence.MEDIUM
        elif score >= 0.2:
            return StateConfidence.LOW
        return StateConfidence.UNKNOWN

    # ── Contradiction Detection ────────────────────────────────────────────

    def _detect_contradictions(self, observations: List[Observation]) -> List[Dict[str, Any]]:
        """Detect when sources disagree on state."""
        contradictions = []
        for i, obs_a in enumerate(observations):
            for obs_b in observations[i+1:]:
                if obs_a.source == obs_b.source:
                    continue
                for key in set(obs_a.state.keys()) & set(obs_b.state.keys()):
                    val_a = obs_a.state[key]
                    val_b = obs_b.state[key]
                    if val_a != val_b:
                        contradictions.append({
                            "key": key,
                            "source_a": obs_a.source.value,
                            "value_a": val_a,
                            "source_b": obs_b.source.value,
                            "value_b": val_b,
                            "severance": abs(
                                self.SOURCE_RELIABILITY.get(obs_a.source, 0.5) -
                                self.SOURCE_RELIABILITY.get(obs_b.source, 0.5)
                            ),
                        })
        return contradictions

    # ── Anomaly Detection ─────────────────────────────────────────────────

    def _detect_anomalies(self, entity_id: str, current_state: Dict[str, Any]) -> List[str]:
        """Detect anomalies by comparing with historical patterns."""
        anomalies = []
        all_obs = self.observations.get(entity_id, [])
        if len(all_obs) < 3:
            return anomalies

        # Simple anomaly: value changed dramatically
        historical = all_obs[:-1]  # All but the latest
        for key, value in current_state.items():
            if not isinstance(value, (int, float)):
                continue
            hist_values = [o.state.get(key) for o in historical if key in o.state]
            hist_values = [v for v in hist_values if isinstance(v, (int, float))]
            if not hist_values:
                continue
            avg = sum(hist_values) / len(hist_values)
            if avg != 0 and abs(value - avg) / abs(avg) > 2.0:
                anomalies.append(f"{key}: value {value} deviates >2x from avg {avg:.2f}")

        return anomalies

    # ── Query & Summary ────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        return {
            "entities_tracked": len(self.observations),
            "total_observations": sum(len(v) for v in self.observations.values()),
            "active_estimates": len(self.estimates),
            "conflicts_detected": len(self._conflict_log),
        }

    def get_low_confidence_entities(self, threshold: float = 0.5) -> List[str]:
        """Get entities with low confidence estimates."""
        return [
            eid for eid, est in self.estimates.items()
            if est.confidence_score < threshold
        ]
