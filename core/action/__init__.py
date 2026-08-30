"""
Action Plane — Transaction, Compensation, Safety Envelope.
"""

from .transaction import TransactionModel, TransactionAction, TransactionResult, TransactionState, RollbackType
from .safety_envelope import SafetyEnvelopeManager, SafetyEnvelope, EnvelopeCheck, EnvelopeViolation

__all__ = [
    "TransactionModel",
    "TransactionAction",
    "TransactionResult",
    "TransactionState",
    "RollbackType",
    "SafetyEnvelopeManager",
    "SafetyEnvelope",
    "EnvelopeCheck",
    "EnvelopeViolation",
]
