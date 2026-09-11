"""
Self-Enforcing Verification Gates — Fable-5 Pattern
====================================================
Mandatory hooks that BLOCK on unverified completion.
"""

from .verification_gates import (
    BlockReason,
    HookContext,
    HookEventType,
    HookResult,
    VerificationGateHookManager,
    VerificationGates,
    VerificationLedger,
    get_verification_gates,
    run_verification_gates,
)

# Backwards-compatible aliases — the 18-plane __init__.py expects these
# names to exist. HookAction and LifecycleHook are simple enum/flag
# aliases for HookEventType so the broader import surface stays stable
# while the verification_gates module uses its own enum.
HookAction = HookEventType
LifecycleHook = HookContext
HookManager = VerificationGateHookManager


__all__ = [
    "VerificationGates",
    "VerificationLedger",
    "HookContext",
    "HookResult",
    "HookEventType",
    "HookAction",
    "LifecycleHook",
    "HookManager",
    "BlockReason",
    "get_verification_gates",
    "run_verification_gates",
    "VerificationGateHookManager",
]