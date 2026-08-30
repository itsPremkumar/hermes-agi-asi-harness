"""
Action Plane — Transaction, Compensation, Safety Envelope.
"""

from .safety_envelope import EnvelopeCheck, EnvelopeViolation, SafetyEnvelope, SafetyEnvelopeManager
from .transaction import (
    RollbackType,
    TransactionAction,
    TransactionModel,
    TransactionResult,
    TransactionState,
)

__all__ = [
    "EnvelopeCheck",
    "EnvelopeViolation",
    "RollbackType",
    "SafetyEnvelope",
    "SafetyEnvelopeManager",
    "TransactionAction",
    "TransactionModel",
    "TransactionResult",
    "TransactionState",
]
