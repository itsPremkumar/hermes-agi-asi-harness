#!/usr/bin/env python3
"""
Hermes ASI-Master (v9) — Cognitive Planning & Autonomous Execution CLI
======================================================================
Provides direct interface to the Pre-Execution Intelligence Layer:
- compile: Compiles request into Mission IR across 22 planning phases (P0 to P21)
- run: Compiles and executes plan with provenance, verification, and recovery
- recon: Runs active empirical environment discovery (Hardware, OS, Git, Packages)
- capabilities: Lists Capability Registry manifests, skills, plugins, and commands

Usage:
  python hermes_v9.py compile "Build microservices telemetry bridge"
  python hermes_v9.py run "Build microservices telemetry bridge"
  python hermes_v9.py recon
  python hermes_v9.py capabilities
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


def compile_mission(request: str, risk: str = "medium"):
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    print("=" * 75)
    print(f"  HERMES ASI-MASTER (v9) — COGNITIVE COMPILER")
    print(f"  Objective:  {request}")
    print(f"  Risk Level: {risk}")
    print("=" * 75)

    plan_ir = os_kernel.compile_mission(request=request, risk_level=risk)

    print("\n" + "=" * 75)
    print(f"  PLAN ID:          {plan_ir.plan_id}")
    print(f"  MISSION ID:       {plan_ir.mission_id}")
    print(f"  STATUS:           {plan_ir.status}")
    print(f"  VALIDITY SCORE:   {plan_ir.plan_validity_score:.2f}")
    print(f"  EXECUTION WAVES:  {len(plan_ir.execution_waves)}")
    print(f"  TOTAL TASKS:      {len(plan_ir.task_graph.list_goals())}")
    print(f"  CRITICAL PATH:    {' -> '.join(plan_ir.task_graph.extract_critical_path())}")
    print("-" * 75)
    print("  EXECUTION WAVES BREAKDOWN:")
    for w in plan_ir.execution_waves:
        print(f"    - Wave {w.wave_number} (Parallel={w.can_parallelize}): {', '.join(w.task_ids)}")
    print("-" * 75)
    print(f"  CHOSEN STRATEGY:  {plan_ir.planning_record.chosen_strategy.get('name', 'N/A')}")
    print(f"  DECISIONS LOGGED: {len(plan_ir.planning_record.decision_provenance)}")
    print("=" * 75)
    return plan_ir


async def run_mission(request: str, risk: str = "medium"):
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    print("=" * 75)
    print(f"  HERMES ASI-MASTER (v9) — EXECUTING MISSION")
    print(f"  Objective:  {request}")
    print(f"  Risk Level: {risk}")
    print("=" * 75)

    result = await os_kernel.execute_mission(request=request, risk_level=risk)

    print("\n" + "=" * 75)
    print(f"  MISSION ID:     {result['mission_id']}")
    print(f"  STATUS:         {result['status'].upper()}")
    print(f"  PLAN STATUS:    {result.get('plan_ir', {}).get('status', 'N/A')}")
    print(f"  VERIFIED:       {result['proof']['verified']}")
    print(f"  PROOF HASH:     {result['proof']['proof_hash']}")
    print(f"  GOAL DRIFT:     {result['goal_drift']}")
    print(f"  PERCEPTIONS:    {result['perceptions_count']}")
    print(f"  HOOKS RUN:      {result['hooks_executed']}")
    print("=" * 75)
    return result


def show_recon():
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    state = os_kernel.recon.inspect()
    print("=" * 75)
    print(state.to_prompt_summary())
    print("=" * 75)


def show_capabilities():
    os_kernel = HermesIntelligenceOS(workspace_root=str(ROOT))
    caps = os_kernel.capabilities.list_capabilities()
    print("=" * 75)
    print(f"  HERMES ASI-MASTER (v9) — CAPABILITY REGISTRY ({len(caps)} manifests)")
    print("=" * 75)
    for c in caps:
        print(f"  [{c.kind.value.upper():<8}] {c.id:<28} | {c.name}")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Hermes ASI-Master v9 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # compile
    compile_p = subparsers.add_parser("compile", help="Compile request into ExecutionPlanIR")
    compile_p.add_argument("request", type=str, help="Mission objective request")
    compile_p.add_argument("--risk", default="medium", choices=["low", "medium", "high", "critical"])

    # run
    run_p = subparsers.add_parser("run", help="Compile and execute mission")
    run_p.add_argument("request", type=str, help="Mission objective request")
    run_p.add_argument("--risk", default="medium", choices=["low", "medium", "high", "critical"])

    # recon
    subparsers.add_parser("recon", help="Inspect environment state")

    # capabilities
    subparsers.add_parser("capabilities", help="List capability registry")

    args = parser.parse_args()

    if args.command == "compile":
        compile_mission(args.request, risk=args.risk)
    elif args.command == "run":
        asyncio.run(run_mission(args.request, risk=args.risk))
    elif args.command == "recon":
        show_recon()
    elif args.command == "capabilities":
        show_capabilities()


if __name__ == "__main__":
    main()
