"""
Transaction & Compensation Model — Some actions behave like transactions.

PREPARE → VALIDATE → COMMIT → VERIFY

When true rollback is impossible (e.g., sending an email),
model: forward action + compensation action
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TransactionState(str, Enum):
    PREPARING = "preparing"
    VALIDATED = "validated"
    COMMITTED = "committed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    COMPENSATED = "compensated"


class RollbackType(str, Enum):
    HARD = "hard"          # true undo (delete what was created)
    SOFT = "soft"          # mark as reverted but keep record
    COMPENSATION = "compensation"  # run compensating action
    IMPOSSIBLE = "impossible"      # cannot undo at all


@dataclass
class TransactionAction:
    id: str
    type: str
    target: str
    parameters: Dict[str, Any]
    rollback_type: RollbackType
    compensation_action: Optional[Dict[str, Any]] = None
    status: TransactionState = TransactionState.PREPARING
    result: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    rollback_at: Optional[float] = None


@dataclass
class TransactionResult:
    transaction_id: str
    success: bool
    state: TransactionState
    actions_completed: int
    actions_total: int
    compensation_triggered: bool = False
    error: Optional[str] = None
    rollback_performed: bool = False


class TransactionModel:
    """
    Transaction-based action execution with rollback and compensation.
    
    PREPARE → VALIDATE → COMMIT → VERIFY
    On failure: ROLLBACK or COMPENSATE
    """

    def __init__(self):
        self.transactions: Dict[str, List[TransactionAction]] = {}
        self.results: Dict[str, TransactionResult] = {}

    def begin(self, transaction_id: str = None) -> str:
        tid = transaction_id or str(uuid.uuid4())
        self.transactions[tid] = []
        return tid

    def add_action(self, transaction_id: str, type: str, target: str,
                   parameters: Dict[str, Any], rollback_type: RollbackType,
                   compensation_action: Dict[str, Any] = None) -> TransactionAction:
        action = TransactionAction(
            id=str(uuid.uuid4()),
            type=type,
            target=target,
            parameters=parameters,
            rollback_type=rollback_type,
            compensation_action=compensation_action,
        )
        if transaction_id not in self.transactions:
            self.transactions[transaction_id] = []
        self.transactions[transaction_id].append(action)
        return action

    def commit(self, transaction_id: str, executor: callable = None) -> TransactionResult:
        """Commit a transaction, executing all actions."""
        actions = self.transactions.get(transaction_id, [])
        if not actions:
            return TransactionResult(
                transaction_id=transaction_id,
                success=False,
                state=TransactionState.FAILED,
                actions_completed=0,
                actions_total=0,
                error="No actions in transaction",
            )

        completed = 0
        for action in actions:
            action.status = TransactionState.PREPARING
            if executor:
                try:
                    action.result = executor(action)
                    action.status = TransactionState.COMMITTED
                    completed += 1
                except Exception as e:
                    action.status = TransactionState.FAILED
                    action.error = str(e)
                    # Attempt rollback/compensation
                    result = self._rollback(transaction_id, completed)
                    result.error = str(e)
                    return result
            else:
                action.status = TransactionState.COMMITTED
                completed += 1

        result = TransactionResult(
            transaction_id=transaction_id,
            success=True,
            state=TransactionState.COMMITTED,
            actions_completed=completed,
            actions_total=len(actions),
        )
        self.results[transaction_id] = result
        return result

    def _rollback(self, transaction_id: str, last_completed: int) -> TransactionResult:
        """Rollback or compensate failed transaction."""
        actions = self.transactions.get(transaction_id, [])
        compensated = False
        rollback_performed = False

        for i in range(last_completed - 1, -1, -1):
            action = actions[i]
            if action.rollback_type == RollbackType.HARD:
                action.status = TransactionState.ROLLED_BACK
                rollback_performed = True
            elif action.rollback_type == RollbackType.COMPENSATION and action.compensation_action:
                action.status = TransactionState.COMPENSATED
                compensated = True
            elif action.rollback_type == RollbackType.IMPOSSIBLE:
                pass  # Nothing we can do

        result = TransactionResult(
            transaction_id=transaction_id,
            success=False,
            state=TransactionState.FAILED,
            actions_completed=last_completed,
            actions_total=len(actions),
            compensation_triggered=compensated,
            rollback_performed=rollback_performed,
        )
        self.results[transaction_id] = result
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "total_transactions": len(self.transactions),
            "results": len(self.results),
            "committed": sum(1 for r in self.results.values() if r.success),
            "failed": sum(1 for r in self.results.values() if not r.success),
        }
