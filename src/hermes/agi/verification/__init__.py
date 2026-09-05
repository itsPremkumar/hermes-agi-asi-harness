"""
Adversarial Verification Engine — Fable-5 / Apodex Pattern
===========================================================
Actively tries to REFUTE completed work rather than just verify it.
"""

from .adversarial_verifier import (
    AdversarialVerifier,
    AdversarialReport,
    VerificationFinding,
    VerificationVerdict,
    WorkPackage,
    verify_work_package,
)

__all__ = [
    "AdversarialVerifier",
    "AdversarialReport",
    "VerificationFinding",
    "VerificationVerdict",
    "WorkPackage",
    "verify_work_package",
]