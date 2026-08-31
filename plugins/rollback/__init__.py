"""
Rollback Infrastructure — Sections 112, 113 of v7 spec

Rollback must be tested in reality, not only documented.
Canary deployment, drift detection, automatic freeze and rollback.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemVersion:
    """A version of the system configuration."""
    version_id: str
    parent: str | None
    components: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    promoted: bool = False
    rolled_back: bool = False


@dataclass
class CanaryDeployment:
    """A staged deployment."""
    id: str
    version: str
    stage: str  # "5%", "25%", "50%", "100%"
    status: str  # "running", "passed", "failed", "frozen"
    metrics: dict[str, float] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)


@dataclass
class DriftAlert:
    """A drift detection alert."""
    id: str
    metric: str
    baseline: float
    current: float
    drift_pct: float
    timestamp: float = field(default_factory=time.time)


class RollbackEngine:
    """Canary deployment and rollback infrastructure."""

    def __init__(self, state_dir: str | None = None):
        self._versions: dict[str, SystemVersion] = {}
        self._current_version: str | None = None
        self._canaries: list[CanaryDeployment] = []
        self._drift_alerts: list[DriftAlert] = []
        self._state_dir = Path(state_dir) if state_dir else Path("state")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._stages = ["5%", "25%", "50%", "100%"]

    def create_version(self, components: dict[str, Any], parent: str | None = None) -> SystemVersion:
        """Create a new system version."""
        version = SystemVersion(
            version_id=f"v{len(self._versions) + 1}-{uuid.uuid4().hex[:6]}",
            parent=parent or self._current_version,
            components=components,
        )
        self._versions[version.version_id] = version
        logger.info(f"Created version: {version.version_id}")
        return version

    def promote_version(self, version_id: str) -> bool:
        """Promote a version to current."""
        if version_id not in self._versions:
            return False
        self._current_version = version_id
        self._versions[version_id].promoted = True
        logger.info(f"Promoted version: {version_id}")
        return True

    def rollback(self) -> str | None:
        """Rollback to parent version."""
        if not self._current_version:
            return None
        current = self._versions[self._current_version]
        if not current.parent:
            logger.warning("No parent version to rollback to")
            return None
        
        current.rolled_back = True
        self._current_version = current.parent
        self._versions[current.parent].promoted = True
        logger.info(f"Rolled back to: {current.parent}")
        return current.parent

    def start_canary(self, version: str) -> CanaryDeployment:
        """Start a staged canary deployment."""
        canary = CanaryDeployment(
            id=str(uuid.uuid4()),
            version=version,
            stage="5%",
            status="running",
        )
        self._canaries.append(canary)
        return canary

    def advance_canary(self, canary_id: str) -> bool:
        """Advance canary to next stage."""
        canary = next((c for c in self._canaries if c.id == canary_id), None)
        if not canary or canary.status != "running":
            return False
        
        idx = self._stages.index(canary.stage)
        if idx < len(self._stages) - 1:
            canary.stage = self._stages[idx + 1]
            if canary.stage == "100%":
                canary.status = "passed"
                self.promote_version(canary.version)
            return True
        return False

    def detect_drift(self, metric: str, baseline: float, current: float, threshold: float = 0.1) -> DriftAlert | None:
        """Detect metric drift."""
        if baseline == 0:
            return None
        drift_pct = abs(current - baseline) / max(abs(baseline), 0.001)
        if drift_pct > threshold:
            alert = DriftAlert(
                id=str(uuid.uuid4()),
                metric=metric,
                baseline=baseline,
                current=current,
                drift_pct=drift_pct,
            )
            self._drift_alerts.append(alert)
            return alert
        return None

    def get_current_version(self) -> SystemVersion | None:
        if self._current_version:
            return self._versions.get(self._current_version)
        return None

    def get_version_history(self) -> list[SystemVersion]:
        return list(self._versions.values())

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_versions": len(self._versions),
            "current_version": self._current_version,
            "canaries": len(self._canaries),
            "drift_alerts": len(self._drift_alerts),
        }


class RollbackPlugin:
    def __init__(self):
        self.engine = RollbackEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.engine.get_stats()}

    async def create_version(self, components: dict[str, Any]):
        return self.engine.create_version(components)

    async def rollback(self):
        return self.engine.rollback()


async def create(kernel=None):
    plugin = RollbackPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
