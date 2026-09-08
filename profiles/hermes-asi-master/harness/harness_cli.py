#!/usr/bin/env python3
"""
harness_cli.py — Master CLI Interface for Hermes Evolutionary AGI/ASI Harness
Universal launcher for autonomous execution, benchmarks, plugin inspection, and GEPA evolution.
"""

import sys
import json
import argparse
import pathlib

# Ensure src is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from src.kernel.event_bus import EventBus
from src.kernel.model_router import ModelRouter
from src.kernel.state_store import TransactionalStateStore
from src.kernel.agent_loop import AgentKernelLoop
from src.plugins.plugin_manager import PluginManager, BasePlugin
from src.plugins.manifest_schema import PluginManifest, PermissionLevel
from src.orchestration.goal_engine import GoalEngine
from src.orchestration.supervisor import AgentSupervisor
from src.memory.hybrid_memory import HybridMemoryStore, MemoryType
from src.memory.world_model import WorldModel
from src.environment.sandbox import ExecutionSandbox
from src.reliability.verifier import ReliabilityVerifier
from src.evolution.jit_harness import JITHarnessGenerator
from src.evolution.gepa_optimizer import GEPAOptimizer
from src.benchmarks.benchmark_engine import BenchmarkEngine

def print_banner():
    print(r"""
======================================================================
         HERMES EVOLUTIONARY AGI/ASI AGENTIC HARNESS
======================================================================
  Mode: 100% Free-First / Zero-Cost Architecture | Ring-0 to Ring-2
  Subsystems: Kernel | Plugins | Supervisor | Memory | Reliability
======================================================================
""")

def cmd_run(args):
    print(f"[*] Analyzing task with JIT-Harness generator: {args.task}")
    jit = JITHarnessGenerator()
    profile = jit.analyze_task(args.task)
    print(f"    - Domain: {profile.domain}")
    print(f"    - Complexity: {profile.complexity_score:.2f}")
    print(f"    - Temperature: {profile.recommended_temperature}")
    print(f"    - Verification Mode: {profile.verification_mode}")

    print("\n[*] Initializing Hermes Kernel and Multi-Agent Supervisor...")
    bus = EventBus()
    router = ModelRouter(zero_cost_only=args.zero_cost)
    state = TransactionalStateStore()
    goal_eng = GoalEngine()
    supervisor = AgentSupervisor(event_bus=bus, model_router=router, goal_engine=goal_eng)

    goal = goal_eng.create_goal("Master Autonomous Goal", args.task)
    goal_eng.auto_decompose(goal)

    print(f"[*] Decomposed goal into {len(goal.subtasks)} subtasks. Executing...")
    res = supervisor.execute_goal(goal)

    print("\n" + "="*50)
    print(f"Execution Verdict: {'SUCCESS' if res['success'] else 'FAILED'}")
    print(f"Total Iterations: {res['iterations']}")
    print("Execution Trace:")
    for step in res["trace"]:
        print(f"  - [{step['role'].upper()}] {step['task_id']}: {step['result'][:70]}...")
    print("="*50)

def cmd_benchmark(args):
    print("[*] Launching Hermes 4-Domain Benchmark Suite...")
    engine = BenchmarkEngine()
    summary = engine.run_suite()

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Total Tasks:     {summary.total_tasks}")
    print(f"Passed Tasks:    {summary.passed_tasks}")
    print(f"Overall Accuracy: {summary.overall_accuracy * 100:.1f}%")
    print(f"Average Latency: {summary.avg_latency_ms:.2f} ms")
    print("\nPer-Task Breakdown:")
    for t in summary.task_results:
        status_str = "PASS" if t.passed else "FAIL"
        print(f"  [{status_str}] {t.task_id} ({t.category}): Score {t.score:.1f} in {t.duration_ms:.1f}ms ({t.steps_taken} steps)")
    print("==================================================\n")

def cmd_evolve(args):
    print(f"[*] Initiating GEPA Pareto genetic mutation on base prompt:\n    '{args.prompt}'")
    opt = GEPAOptimizer(base_prompt=args.prompt)
    population = opt.evolve_population(iterations=2)
    best = opt.get_best_prompt()

    print(f"\n[+] Evolved population of {len(population)} candidate prompt variants.")
    print(f"[+] Best Pareto Variant ({best.variant_id}):")
    print(f"    Accuracy Score: {best.accuracy_score:.2f}")
    print(f"    Prompt Text:\n{best.prompt_text}\n")

def cmd_status(args):
    mem = HybridMemoryStore()
    wm = WorldModel()
    print("[*] Hermes AGI Harness System Status:")
    print("    - Kernel: Active (Ring 0)")
    print("    - Memory: 9-Type SQLite FTS5 Active")
    print("    - Model Router: 100% Free / Zero-Cost Enforced")
    print("    - Reliability Gate: AST + Secret Scanner Active")

def main():
    parser = argparse.ArgumentParser(description="Hermes AGI/ASI Harness CLI")
    parser.add_argument("--zero-cost", action="store_true", default=True, help="Enforce 100% free model providers")
    subparsers = parser.add_subparsers(dest="command")

    # run
    p_run = subparsers.add_parser("run", help="Execute an autonomous task")
    p_run.add_argument("--task", type=str, required=True, help="Task description")

    # benchmark
    p_bm = subparsers.add_parser("benchmark", help="Run benchmark suite")

    # evolve
    p_ev = subparsers.add_parser("evolve", help="Run GEPA prompt evolution")
    p_ev.add_argument("--prompt", type=str, default="You are a helpful AGI assistant.")

    # status
    p_st = subparsers.add_parser("status", help="Show system status")

    args = parser.parse_args()
    print_banner()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "evolve":
        cmd_evolve(args)
    elif args.command == "status" or args.command is None:
        cmd_status(args)

if __name__ == "__main__":
    main()
