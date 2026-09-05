"""
HERMES INTELLIGENCE OS — ENVIRONMENT & GOAL DRIFT DETECTORS
==========================================================
Monitors environmental and mission state stability across long horizons:
1. Environment Drift Detector: Compares environment fingerprints before and after
   suspension/resumption to prevent stale dependencies or external modifications.
2. Goal Drift Detector: Audits ongoing step trajectories against the initial
   GoalContract invariants to prevent mission derailment and agent wandering.
"""

from __future__ import annotations

import enum
import hashlib
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.drift")


# =====================================================================
# Environment Drift Detection
# =====================================================================

class DriftSeverity(str, enum.Enum):
    """Classification of environment drift severity."""
    NONE = "none"
    LOW = "low"            # Minor non-breaking file changes or harmless env var additions
    HIGH = "high"          # Config file modified, dependencies altered
    CRITICAL = "critical"  # Git branch shifted, workspace files missing, core runtime modified


@dataclass
class EnvironmentFingerprint:
    """Snapshot of execution environment state at a given timestamp."""
    timestamp: float
    python_version: str
    platform: str
    critical_file_hashes: Dict[str, str]     # rel_path -> sha256
    env_keys_present: List[str]
    git_head: Optional[str] = None
    workspace_root: str = "."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "python_version": self.python_version,
            "platform": self.platform,
            "critical_file_hashes": self.critical_file_hashes,
            "env_keys_count": len(self.env_keys_present),
            "git_head": self.git_head,
        }


@dataclass
class DriftReport:
    """Comparison report between prior and current environment states."""
    severity: DriftSeverity
    is_safe_to_resume: bool
    modified_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    new_files: List[str] = field(default_factory=list)
    runtime_mismatch: bool = False
    git_drift: bool = False
    reconciliation_steps: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"DriftReport(severity={self.severity.value}, safe={self.is_safe_to_resume}, "
            f"modified={len(self.modified_files)}, missing={len(self.missing_files)}, "
            f"runtime_mismatch={self.runtime_mismatch})"
        )


class EnvironmentDriftDetector:
    """
    Captures and validates environment stability before resuming checkpoints
    or executing sensitive multi-step missions.
    """

    CRITICAL_FILES = [
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        ".env",
        "README.md",
    ]

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root

    def _hash_file(self, filepath: Path) -> Optional[str]:
        if not filepath.exists() or not filepath.is_file():
            return None
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()[:16]
        except Exception:
            return None

    def capture_fingerprint(self) -> EnvironmentFingerprint:
        """Capture the current runtime environment fingerprint."""
        root = Path(self.workspace_root)
        file_hashes: Dict[str, str] = {}

        for rel in self.CRITICAL_FILES:
            fp = root / rel
            if fp.exists():
                h = self._hash_file(fp)
                if h:
                    file_hashes[rel] = h

        # Git HEAD check (simple check without external process if possible)
        git_head = None
        git_head_file = root / ".git" / "HEAD"
        if git_head_file.exists():
            try:
                git_head = git_head_file.read_text(encoding="utf-8").strip()[:32]
            except Exception:
                pass

        env_keys = sorted([k for k in os.environ.keys() if not any(s in k.lower() for s in ["key", "secret", "token", "password"])])

        return EnvironmentFingerprint(
            timestamp=time.time(),
            python_version=sys.version.split()[0],
            platform=sys.platform,
            critical_file_hashes=file_hashes,
            env_keys_present=env_keys,
            git_head=git_head,
            workspace_root=str(root.resolve()),
        )

    def detect_drift(
        self,
        prior: EnvironmentFingerprint,
        current: Optional[EnvironmentFingerprint] = None,
    ) -> DriftReport:
        """Compare current environment against a prior fingerprint."""
        if current is None:
            current = self.capture_fingerprint()

        modified_files: List[str] = []
        missing_files: List[str] = []
        new_files: List[str] = []
        reconciliations: List[str] = []

        # Check critical file hashes
        for rel_file, prior_hash in prior.critical_file_hashes.items():
            curr_hash = current.critical_file_hashes.get(rel_file)
            if curr_hash is None:
                missing_files.append(rel_file)
                reconciliations.append(f"Restore missing file: {rel_file}")
            elif curr_hash != prior_hash:
                modified_files.append(rel_file)
                reconciliations.append(f"Review external changes to config: {rel_file}")

        for rel_file in current.critical_file_hashes:
            if rel_file not in prior.critical_file_hashes:
                new_files.append(rel_file)

        runtime_mismatch = (
            prior.python_version != current.python_version or
            prior.platform != current.platform
        )
        if runtime_mismatch:
            reconciliations.append(f"Python runtime mismatch: {prior.python_version} vs {current.python_version}")

        git_drift = (prior.git_head is not None and current.git_head is not None and prior.git_head != current.git_head)
        if git_drift:
            reconciliations.append("Git commit HEAD has shifted since checkpoint")

        # Determine severity
        if runtime_mismatch or len(missing_files) > 0:
            severity = DriftSeverity.CRITICAL
            safe = False
        elif git_drift or any("pyproject" in f or "requirements" in f for f in modified_files):
            severity = DriftSeverity.HIGH
            safe = True  # Can resume with caution
        elif len(modified_files) > 0 or len(new_files) > 0:
            severity = DriftSeverity.LOW
            safe = True
        else:
            severity = DriftSeverity.NONE
            safe = True

        return DriftReport(
            severity=severity,
            is_safe_to_resume=safe,
            modified_files=modified_files,
            missing_files=missing_files,
            new_files=new_files,
            runtime_mismatch=runtime_mismatch,
            git_drift=git_drift,
            reconciliation_steps=reconciliations,
        )


# =====================================================================
# Goal Drift Detection
# =====================================================================

@dataclass
class GoalDriftAlert:
    """Audit evaluation of whether active actions adhere to goal contract invariants."""
    drift_score: float                       # 0.0 = fully aligned, 1.0 = completely derailed
    alert_level: str                         # "NOMINAL", "WARNING", "INTERVENTION_REQUIRED"
    violated_invariants: List[str] = field(default_factory=list)
    off_target_actions: List[str] = field(default_factory=list)
    recommendation: str = "Proceed nominally"


class GoalDriftDetector:
    """
    Monitors long-horizon execution to prevent mission creep,
    infinite tangential loops, and invariant violations.
    """

    def __init__(self, warning_threshold: float = 0.35, critical_threshold: float = 0.65):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def evaluate(
        self,
        objective: str,
        invariants: List[str],
        completed_steps: List[Dict[str, Any]],
        pending_steps: List[Dict[str, Any]],
    ) -> GoalDriftAlert:
        """
        Evaluate goal adherence by comparing action descriptions against
        the original objective and verifying invariant mentions.
        """
        obj_tokens = set(re.findall(r"\w+", objective.lower()))
        violated_invariants: List[str] = []
        off_target_actions: List[str] = []

        all_steps = completed_steps + pending_steps
        if not all_steps:
            return GoalDriftAlert(drift_score=0.0, alert_level="NOMINAL")

        off_target_count = 0
        for step in all_steps:
            desc = str(step.get("description", "") or step.get("action", "")).lower()
            step_tokens = set(re.findall(r"\w+", desc))

            # Check overlap with objective
            overlap = len(obj_tokens.intersection(step_tokens))
            if overlap == 0 and len(step_tokens) > 3:
                off_target_count += 1
                off_target_actions.append(desc[:80])

        # Check invariants against completed step actions (e.g. "no deletion", "preserve tests")
        for inv in invariants:
            inv_lower = inv.lower()
            if "no deletion" in inv_lower or "zero deletion" in inv_lower:
                for step in completed_steps:
                    action_name = str(step.get("action", "")).lower()
                    if "delete" in action_name or "rm" in str(step.get("args", "")).lower():
                        violated_invariants.append(f"Invariant '{inv}' potentially breached by action: {action_name}")

        # Compute composite drift score
        action_drift_ratio = off_target_count / max(1, len(all_steps))
        invariant_penalty = min(0.6, len(violated_invariants) * 0.3)
        drift_score = round(min(1.0, (action_drift_ratio * 0.5) + invariant_penalty), 3)

        if drift_score >= self.critical_threshold or len(violated_invariants) > 0:
            level = "INTERVENTION_REQUIRED"
            rec = "Pause execution and re-align action graph with original objective."
        elif drift_score >= self.warning_threshold:
            level = "WARNING"
            rec = "Agent is pursuing adjacent tasks; request supervisory steering."
        else:
            level = "NOMINAL"
            rec = "Execution is aligned with primary goal invariants."

        return GoalDriftAlert(
            drift_score=drift_score,
            alert_level=level,
            violated_invariants=violated_invariants,
            off_target_actions=off_target_actions,
            recommendation=rec,
        )
