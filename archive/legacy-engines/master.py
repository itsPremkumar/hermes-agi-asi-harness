#!/usr/bin/env python
"""
Hermes AGI/ASI Harness — Master Orchestrator

THIS IS THE COMPLETE SYSTEM:
- Multi-Round Verification (3+ rounds, cross-validated)
- 24/7 Supervisor Daemon
- Daily Development Engine (idea → implement → test → verify)
- Real-Environment Validation
- Master Verification before declaring "complete"

Usage:
    python master.py                    # Run full verification suite
    python master.py --daemon          # Start 24/7 supervisor daemon
    python master.py --daily           # Run daily development cycle
    python master.py --real-env        # Run real-environment check
    python master.py --all             # Full system: daily → verify → real-env
"""

import asyncio
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Setup path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))


def run_all_phases_verification():
    """
    Run COMPLETE multi-round verification of ALL phases.
    
    This is the final check before declaring the system complete.
    Runs each test suite 3 times in isolated subprocesses,
    cross-validates results, and produces a confidence score.
    """
    print(f"\n{'#'*70}")
    print("#  MASTER VERIFICATION — COMPLETE SYSTEM VALIDATION")
    print(f"#  {datetime.now(timezone.utc).isoformat()}")
    print(f"{'#'*70}")
    
    from core.verification import MultiRoundVerifier
    
    verifier = MultiRoundVerifier(str(PROJECT_ROOT))
    
    # All test files in dependency order
    test_files = [
        "test_phase1.py",
        "test_phase2.py",
        "test_phase3_4.py",
        "test_phase5.py",
        "test_phase6.py",
        "test_phase7.py",
        "test_phase8.py",
        "test_runtime.py",
        "test_working_plugins.py",
        "test_kernel_integration.py",
    ]
    
    # Filter to existing files
    existing = [f for f in test_files if (PROJECT_ROOT / f).exists()]
    print(f"\nFound {len(existing)} test files to verify:")
    for f in existing:
        size = (PROJECT_ROOT / f).stat().st_size
        print(f"  - {f} ({size} bytes)")
    
    # Create 3-round verification plan
    plan = verifier.create_plan(existing, num_rounds=3)
    
    print("\nVerification plan:")
    print(f"  Rounds: {plan.num_rounds}")
    print(f"  Isolated runs: {plan.isolated_runs}")
    print(f"  Cross-validation: {plan.cross_validate}")
    print(f"  Timeout: {plan.timeout_seconds}s per test")
    
    # Run verification
    async def do_verify():
        result = await verifier.run_verification(plan)
        return result
    
    result = asyncio.run(do_verify())
    
    # Final verdict
    print(f"\n{'#'*70}")
    print("#  FINAL VERDICT")
    print(f"{'#'*70}")
    
    rounds_passed = sum(1 for r in result["rounds"] if r["passed"])
    total_rounds = len(result["rounds"])
    
    print(f"\n  Rounds passed: {rounds_passed}/{total_rounds}")
    print(f"  Consensus score: {result['consensus']['consensus_score']:.2f}")
    print(f"  All rounds agree: {result['consensus']['all_rounds_agree']}")
    if result.get("brier_score"):
        print(f"  Brier score: {result['brier_score']:.4f}")
    
    overall = result["overall_passed"]
    
    if overall:
        print("\n  ✓✓✓ SYSTEM FULLY VERIFIED ✓✓✓")
        print(f"  All {total_rounds} verification rounds passed")
        print("  All rounds agree — consensus achieved")
        print("  System is production-ready")
    else:
        print("\n  ✗✗✗ VERIFICATION FAILED ✗✗✗")
        print(f"  {total_rounds - rounds_passed} round(s) failed")
        if not result["consensus"]["all_rounds_agree"]:
            print("  Cross-validation: rounds disagree")
    
    # Save result
    result_file = PROJECT_ROOT / "verification_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Full results saved to: {result_file}")
    
    print(f"\n{'#'*70}\n")
    
    return overall


async def run_supervisor():
    """Start the 24/7 supervisor daemon."""
    print(f"\n{'='*60}")
    print("  STARTING 24/7 SUPERVISOR DAEMON")
    print(f"{'='*60}")
    
    from core.runtime.supervisor import SupervisorDaemon, SupervisionConfig
    
    config = SupervisionConfig(
        project_root=str(PROJECT_ROOT),
        health_check_interval=60,  # 1 minute
        verification_interval_hours=6,
        daily_dev_interval_hours=24,
        enable_daily_dev=True,
        enable_verification=True,
        enable_real_env_check=True,
    )
    
    daemon = SupervisorDaemon(config)
    await daemon.start()


async def run_daily_dev():
    """Run a daily development cycle."""
    from core.runtime.daily_dev import DailyDevEngine, DailyDevConfig
    
    config = DailyDevConfig(project_root=str(PROJECT_ROOT))
    engine = DailyDevEngine(config)
    
    result = await engine.run_daily_cycle()
    
    print("\nDaily dev cycle complete:")
    print(f"  Ideas generated: {result['ideas_generated']}")
    print(f"  Ideas implemented: {result['ideas_implemented']}")
    print(f"  Tests passed: {result['tests_passed']}/{result['tests_total']}")
    print(f"  Verification: {'PASSED' if result['verification_passed'] else 'FAILED'}")
    
    return result


async def run_real_env():
    """Run real-environment validation."""
    from core.runtime.daily_dev import DailyDevEngine, DailyDevConfig
    
    config = DailyDevConfig(project_root=str(PROJECT_ROOT))
    engine = DailyDevEngine(config)
    
    result = await engine.run_real_env_check()
    
    return result


async def run_all():
    """Run everything: daily dev → verification → real-env."""
    print(f"\n{'#'*70}")
    print("#  MASTER ORCHESTRATOR — FULL SYSTEM RUN")
    print(f"#  {datetime.now(timezone.utc).isoformat()}")
    print(f"{'#'*70}\n")
    
    results = {}
    
    # Step 1: Daily Development
    print(f"\n{'='*60}")
    print("  STEP 1/3: Daily Development Cycle")
    print(f"{'='*60}")
    results["daily_dev"] = await run_daily_dev()
    
    # Step 2: Multi-Round Verification
    print(f"\n{'='*60}")
    print("  STEP 2/3: Multi-Round Verification")
    print(f"{'='*60}")
    results["verification"] = run_all_phases_verification()
    
    # Step 3: Real-Environment Validation
    print(f"\n{'='*60}")
    print("  STEP 3/3: Real-Environment Validation")
    print(f"{'='*60}")
    results["real_env"] = await run_real_env()
    
    # Final summary
    print(f"\n{'#'*70}")
    print("#  MASTER ORCHESTRATOR — FINAL SUMMARY")
    print(f"{'#'*70}")
    
    print(f"\n  Daily Dev:   {results['daily_dev']['ideas_implemented']} ideas implemented, {results['daily_dev']['tests_passed']}/{results['daily_dev']['tests_total']} tests passed")
    print(f"  Verification: {'✓ PASSED' if results['verification'] else '✗ FAILED'}")
    print(f"  Real-Env:     {'✓ PASSED' if results['real_env']['passed'] else '✗ FAILED'}")
    
    all_passed = (
        results['verification'] and
        results['real_env']['passed'] and
        results['daily_dev']['verification_passed']
    )
    
    if all_passed:
        print("\n  🚀 SYSTEM FULLY OPERATIONAL — ALL CHECKS PASSED 🚀")
    else:
        print("\n  ⚠️  Some checks failed — review results above")
    
    print(f"\n{'#'*70}\n")
    
    # Save final result
    final_result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "all_passed": all_passed,
        "daily_dev": results["daily_dev"],
        "verification_passed": results["verification"],
        "real_env": results["real_env"],
    }
    
    result_file = PROJECT_ROOT / "master_result.json"
    with open(result_file, "w") as f:
        json.dump(final_result, f, indent=2, default=str)
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Hermes AGI/ASI Harness — Master Orchestrator"
    )
    parser.add_argument("--daemon", action="store_true", help="Start 24/7 supervisor daemon")
    parser.add_argument("--daily", action="store_true", help="Run daily development cycle")
    parser.add_argument("--real-env", action="store_true", help="Run real-environment check")
    parser.add_argument("--all", action="store_true", help="Run full system: daily → verify → real-env")
    parser.add_argument("--verify", action="store_true", help="Run multi-round verification only")
    
    args = parser.parse_args()
    
    if args.all:
        success = asyncio.run(run_all())
        sys.exit(0 if success else 1)
    elif args.daemon:
        asyncio.run(run_supervisor())
    elif args.daily:
        asyncio.run(run_daily_dev())
    elif args.real_env:
        asyncio.run(run_real_env())
    elif args.verify:
        success = run_all_phases_verification()
        sys.exit(0 if success else 1)
    else:
        # Default: run full verification
        success = run_all_phases_verification()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
