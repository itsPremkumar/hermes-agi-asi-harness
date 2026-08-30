"""
Universal Observation Protocol (UOP) + Perception Fusion.

Every driver produces normalized observations with:
id, action_id, timestamp, source, state_before, raw_observation,
normalized_state, confidence, evidence, anomalies
"""

from __future__ import annotations

import time
import uuid
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


@dataclass
class Observation:
    id: str
    action_id: str
    timestamp: float
    source: ObservationSource
    state_before: Dict[str, Any]
    raw_observation: Any
    normalized_state: Dict[str, Any]
    confidence: float
    evidence: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusedObservation:
    """Result of fusing multiple observations of the same entity."""
    id: str
    entity_id: str
    timestamp: float
    fused_state: Dict[str, Any]
    confidence: float
    sources: List[ObservationSource]
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    evidence_chain: List[str] = field(default_factory=list)


class PerceptionFusion:
    """
    Fuse multiple sensor streams into unified state estimates.
    
    API + DOM + Vision → SENSOR FUSION → STATE ESTIMATE
    
    When sources disagree:
    1. Detect conflict
    2. Weight by source reliability
    3. Weight by freshness
    4. Check independence
    5. Reconcile
    """

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
        self.fused: Dict[str, FusedObservation] = {}

    def add_observation(self, entity_id: str, source: ObservationSource,
                        state_before: Dict[str, Any], raw_observation: Any,
                        normalized_state: Dict[str, Any], confidence: float = 0.5,
                        action_id: str = "", evidence: List[str] = None,
                        anomalies: List[str] = None) -> Observation:
        obs = Observation(
            id=str(uuid.uuid4()),
            action_id=action_id,
            timestamp=time.time(),
            source=source,
            state_before=state_before,
            raw_observation=raw_observation,
            normalized_state=normalized_state,
            confidence=confidence,
            evidence=evidence or [],
            anomalies=anomalies or [],
        )
        if entity_id not in self.observations:
            self.observations[entity_id] = []
        self.observations[entity_id].append(obs)
        return obs

    def fuse(self, entity_id: str) -> Optional[FusedObservation]:
        """Fuse all observations for an entity into a single estimate."""
        obs_list = self.observations.get(entity_id, [])
        if not obs_list:
            return None

        # Sort by timestamp (newest first)
        sorted_obs = sorted(obs_list, key=lambda o: o.timestamp, reverse=True)
        recent = [o for o in sorted_obs if time.time() - o.timestamp < 300]
        if not recent:
            recent = sorted_obs[:5]

        # Detect conflicts
        conflicts = self._detect_conflicts(recent)

        # Fuse states
        fused_state = self._weighted_fusion(recent)

        # Calculate confidence
        confidence = self._calculate_confidence(recent, conflicts)

        fused_obs = FusedObservation(
            id=str(uuid.uuid4()),
            entity_id=entity_id,
            timestamp=time.time(),
            fused_state=fused_state,
            confidence=confidence,
            sources=list(set(o.source for o in recent)),
            conflicts=conflicts,
            anomalies=[a for o in recent for a in o.anomalies],
            evidence_chain=[e for o in recent for e in o.evidence],
        )
        self.fused[entity_id] = fused_obs
        return fused_obs

    def _weighted_fusion(self, observations: List[Observation]) -> Dict[str, Any]:
        """Weighted fusion of normalized states."""
        fused: Dict[str, Any] = {}
        weights: Dict[str, float] = {}

        for obs in observations:
            reliability = self.SOURCE_RELIABILITY.get(obs.source, 0.5)
            freshness = self._freshness_weight(obs.timestamp)
            weight = reliability * freshness * obs.confidence

            for key, value in obs.normalized_state.items():
                if key not in fused:
                    fused[key] = value
                    weights[key] = weight
                else:
                    if isinstance(value, (int, float)) and isinstance(fused[key], (int, float)):
                        total_w = weights[key] + weight
                        fused[key] = (fused[key] * weights[key] + value * weight) / total_w
                        weights[key] = total_w
                    elif weight > weights[key]:
                        fused[key] = value
                        weights[key] = weight

        return fused

    def _freshness_weight(self, timestamp: float) -> float:
        age = time.time() - timestamp
        if age < 60:
            return 1.0
        elif age < 300:
            return 0.8
        elif age < 900:
            return 0.5
        elif age < 3600:
            return 0.3
        return 0.1

    def _detect_conflicts(self, observations: List[Observation]) -> List[Dict[str, Any]]:
        """Detect when sources disagree."""
        conflicts = []
        for i, obs_a in enumerate(observations):
            for obs_b in observations[i+1:]:
                if obs_a.source == obs_b.source:
                    continue
                for key in set(obs_a.normalized_state.keys()) & set(obs_b.normalized_state.keys()):
                    val_a = obs_a.normalized_state[key]
                    val_b = obs_b.normalized_state[key]
                    if val_a != val_b:
                        conflicts.append({
                            "key": key,
                            "source_a": obs_a.source.value,
                            "value_a": val_a,
                            "source_b": obs_b.source.value,
                            "value_b": val_b,
                        })
        return conflicts

    def _calculate_confidence(self, observations: List[Observation],
                               conflicts: List[Dict]) -> float:
        if not observations:
            return 0.0

        confidences = []
        for obs in observations:
            reliability = self.SOURCE_RELIABILITY.get(obs.source, 0.5)
            freshness = self._freshness_weight(obs.timestamp)
            confidences.append(reliability * freshness * obs.confidence)

        base = sum(confidences) / len(confidences)
        unique_sources = len(set(o.source for o in observations))
        boost = min(0.2, unique_sources * 0.05)
        penalty = len(conflicts) * 0.15

        return max(0.0, min(1.0, base + boost - penalty))

    def get_state(self) -> Dict[str, Any]:
        return {
            "entities_tracked": len(self.observations),
            "total_observations": sum(len(v) for v in self.observations.values()),
            "fused_estimates": len(self.fused),
        }
