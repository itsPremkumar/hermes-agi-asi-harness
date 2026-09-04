#!/usr/bin/env python3
"""
Hermes Intelligence OS (v8) — Unified Command Line Interface
=============================================================
Provides direct access to the 18-Plane Intelligence Operating System:
- Run missions through the 18 planes and 6 nested control loops
- Execute daily capability, curriculum, and evolution cycles
- Inspect persistent daemon checkpoints and system telemetry

Usage:
  python hermes_v8.py run "Synthesize distributed consensus caching layer"
  python hermes_v8.py daily
  python hermes_v8.py status
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure root and src on Python path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes_os import HermesIntelligenceOS


async def run_mission(request: str, risk: str = "medium", verbose: bool = True):
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    if verbose:
        print("=" * 70)
        print(f"  HERMES INTELLIGENCE OS (v8) — DISPATCHING MISSION")
        print(f"  Objective: {request}")
        print(f"  Risk Level: {risk}")
        print("=" * 70)

    result = await os_kernel.execute_mission(request=request, risk_level=risk)

    print("\n" + "=" * 70)
    print(f"  MISSION ID:    {result['mission_id']}")
    print(f"  STATUS:        {result['status'].upper()}")
    print(f"  OS STATE:      {result['os_state']}")
    print(f"  ABSTRACTION:   {result['abstraction']}")
    print(f"  VERIFIED:      {result['proof']['verified']}")
    print(f"  PROOF HASH:    {result['proof']['proof_hash']}")
    print(f"  TRAJECTORY:    {result['trajectory_id']}")
    print(f"  SUPERVISOR:    {result['supervisor_action'].upper()}")
    print("=" * 70)
    return result


def run_daily():
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    print("=" * 70)
    print("  HERMES INTELLIGENCE OS (v8) — EXECUTING DAILY CONTINUOUS CYCLE")
    print("=" * 70)

    report = os_kernel.run_daily_cycle()
    print(json.dumps(report, indent=2))
    print("\nDaily cycle completed successfully.")


def print_status():
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    print("=" * 70)
    print("  HERMES INTELLIGENCE OS (v8) — TELEMETRY STATUS")
    print("=" * 70)
    print(f"  State:                {os_kernel.executive.state.current_state}")
    print(f"  Tokens Used:          {os_kernel.executive.resources.tokens_used}")
    print(f"  Active Checkpoints:   {os_kernel.daemon.active_checkpoints_count()}")
    print(f"  Queued Missions:      {os_kernel.daemon.pending_count()}")
    print(f"  Memory Stats:         {os_kernel.memory.stats()}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Hermes Intelligence OS v8 CLI")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a mission through the 18-plane OS")
    run_p.add_argument("task", help="The mission objective or task description")
    run_p.add_argument("--risk", default="medium", choices=["low", "medium", "high", "critical"], help="Risk tier")
    run_p.add_argument("--quiet", action="store_true", help="Suppress verbose logs")

    sub.add_parser("daily", help="Run the daily capability, curriculum, and evolution cycles")
    sub.add_parser("status", help="Inspect OS telemetry and daemon status")

    args = parser.parse_args()

    if args.command == "run":
        res = asyncio.run(run_mission(args.task, risk=args.risk, verbose=not args.quiet))
        sys.exit(0 if res["status"] == "completed" else 1)
    elif args.command == "daily":
        run_daily()
    elif args.command == "status":
        print_status()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
