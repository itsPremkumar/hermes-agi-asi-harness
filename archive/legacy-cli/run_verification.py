"""
Master Verification Script — Multi-Round Independent Verification

Runs ALL phase test suites 3+ times in isolated subprocesses,
cross-validates results, and produces a confidence score.
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.verification import MultiRoundVerifier


async def main():
    print("\n" + "=" * 70)
    print("  HERMES AGI/ASI HARNESS — MASTER VERIFICATION")
    print("  Multi-Round Independent Validation (3 rounds, cross-validated)")
    print("=" * 70)

    verifier = MultiRoundVerifier(project_root=os.getcwd())

    # All test files in dependency order
    candidate_files = [
        "test_phase1.py",
        "test_phase2.py",
        "test_phase3_4.py",
        "test_phase5.py",
        "test_phase6.py",
        "test_phase7.py",
        "test_phase8.py",
        # Original tests
        "test_runtime.py",
        "test_working_plugins.py",
        "test_kernel_integration.py",
    ]
    test_files = []
    for f in candidate_files:
        if Path("tests", f).exists():
            test_files.append(str(Path("tests", f)))
        elif Path(f).exists():
            test_files.append(f)

    # Filter to existing files
    existing = [f for f in test_files if Path(f).exists()]
    print(f"\nFound {len(existing)} test files:")
    for f in existing:
        size = Path(f).stat().st_size
        print(f"  - {f} ({size} bytes)")

    plan = verifier.create_plan(existing, num_rounds=3)
    result = await verifier.run_verification(plan)

    # Final report
    print(f"\n{'='*70}")
    print("  MASTER VERIFICATION COMPLETE")
    print(f"{'='*70}")
    print(f"  Overall: {'✓ PASSED' if result['overall_passed'] else '✗ FAILED'}")
    print(f"  Rounds: {sum(1 for r in result['rounds'] if r['passed'])}/{len(result['rounds'])} passed")

    if result.get("consensus"):
        print(f"  Consensus: {result['consensus']['consensus_score']:.2f}")
        print(f"  All rounds agree: {result['consensus']['all_rounds_agree']}")

    if result.get("brier_score") is not None:
        print(f"  Brier score: {result['brier_score']:.4f}")

    return result["overall_passed"]


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
