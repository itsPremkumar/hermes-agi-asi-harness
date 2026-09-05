"""
Self-Enforcing Verification Gates — Fable-5 Pattern
====================================================
Mandatory hooks that BLOCK on unverified completion.
"""

from .verification_gates import (
    VerificationGates,
    VerificationLedger,
    HookContext,
    HookResult,
    HookEventType,
    BlockReason,
    get_verification_gates,
    run_verification_gates,
    VerificationGateHookManager,
)

__all__ = [
    "VerificationGates",
    "VerificationLedger",
    "HookContext",
    "HookResult",
    "HookEventType",
    "BlockReason",
    "get_verification_gates",
    "run_verification_gates",
    "VerificationGateHookManager",
]