
"""
Recovery Engine — checkpointing, rollback, retry, resume, failure classification.

Inspired by: Hermes Agent error recovery, Harneloop harness loop.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FailureClass(str, Enum):
    TRANSIENT = "transient"
    TOOL = "tool"
    NETWORK = "network"
    AUTH = "auth"
    PERMISSION = "permission"
    MODEL = "model"
    PLANNING = "planning"
    SAFETY = "safety"
    UNKNOWN = "unknown"


@dataclass
class Checkpoint:
    checkpoint_id: str
    task_id: str
    state: Dict[str, Any]
    created_at: float


class RecoveryEngine:
    """Self-healing and recovery system."""
    
    def __init__(self):
        self.manifest = None
        self._checkpoints: Dict[str, Checkpoint] = {}
    
    async def load(self) -> bool:
        logger.info("Recovery engine loaded")
        return True
    
    async def start(self) -> bool:
        logger.info("Recovery engine started")
        return True
    
    async def stop(self) -> bool:
        return True
    
    def create_checkpoint(self, task_id: str, state: Dict[str, Any]) -> str:
        """Create a checkpoint for recovery."""
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            state=state,
            created_at=time.time()
        )
        self._checkpoints[checkpoint_id] = checkpoint
        logger.info("Checkpoint created: %s for task %s", checkpoint_id, task_id)
        return checkpoint_id
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint."""
        return self._checkpoints.get(checkpoint_id)
    
    def get_latest_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a task."""
        checkpoints = [c for c in self._checkpoints.values() if c.task_id == task_id]
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda c: c.created_at)
    
    def classify_failure(self, error: Exception) -> FailureClass:
        """Classify a failure."""
        error_str = str(error).lower()
        
        if "network" in error_str or "connection" in error_str:
            return FailureClass.NETWORK
        elif "auth" in error_str or "credential" in error_str:
            return FailureClass.AUTH
        elif "permission" in error_str or "denied" in error_str:
            return FailureClass.PERMISSION
        elif "timeout" in error_str:
            return FailureClass.TRANSIENT
        elif "model" in error_str or "provider" in error_str:
            return FailureClass.MODEL
        elif "safety" in error_str or "injection" in error_str:
            return FailureClass.SAFETY
        
        return FailureClass.UNKNOWN
    
    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "type": "recovery_engine",
            "checkpoints": len(self._checkpoints),
        }


async def create(kernel: Any) -> RecoveryEngine:
    return RecoveryEngine()
