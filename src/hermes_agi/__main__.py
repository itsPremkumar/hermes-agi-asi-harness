#!/usr/bin/env python3
"""CLI entry point for Hermes AGI/ASI Harness."""

from __future__ import annotations

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(description="Hermes AGI/ASI Harness")
    parser.add_argument("--version", action="version", version="%(prog)s 2.0.0")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a task")
    run_parser.add_argument("task", help="Task description")
    
    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmarks")
    bench_parser.add_argument("--name", default="all", help="Benchmark name")
    
    # Spawn command
    spawn_parser = subparsers.add_parser("spawn", help="Spawn a bot")
    spawn_parser.add_argument("bot", help="Bot name")
    spawn_parser.add_argument("command", help="Command for the bot")
    
    # Status command
    subparsers.add_parser("status", help="Show system status")
    
    # Health command
    subparsers.add_parser("health", help="Show health status")
    
    # Research command
    research_parser = subparsers.add_parser("research", help="Run autonomous deep research on a topic")
    research_parser.add_argument("topic", help="Research topic or question")
    research_parser.add_argument("--depth", type=int, default=3, help="Research depth (1-5)")

    # Think command
    think_parser = subparsers.add_parser("think", help="Run deep thinking deliberation on a goal")
    think_parser.add_argument("goal", help="Goal to deliberate")

    # Allocate command
    allocate_parser = subparsers.add_parser("allocate", help="Allocate a mission packet to Hermes")
    allocate_parser.add_argument("task", help="Task description")
    allocate_parser.add_argument("--role", default="hermes-coder", help="Assigned agent role")

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover features")
    discover_parser.add_argument("query", nargs="?", default="", help="Search query")

    # Overnight (gnhf) command
    for name in ("overnight", "gnhf"):
        ov_parser = subparsers.add_parser(name, help="Run autonomous overnight endurance loop (gnhf pattern)")
        ov_parser.add_argument("objective", help="High-level engineering objective")
        ov_parser.add_argument("--max-iterations", type=int, default=10, help="Maximum iterations to run")
        ov_parser.add_argument("--max-failures", type=int, default=3, help="Consecutive failure abort limit")
        ov_parser.add_argument("--current-branch", action="store_true", help="Commit directly on current branch")
        ov_parser.add_argument("--stop-when", default="", help="Natural language stopping condition")

    # Evolve command (Darwinian Closed-Loop Self-Improvement)
    evolve_parser = subparsers.add_parser("evolve", help="Run Darwinian Closed-Loop Self-Evolution cycle")
    evolve_parser.add_argument("--cycles", type=int, default=1, help="Number of recursive evolution cycles to run")
    evolve_parser.add_argument("--margin", type=float, default=0.015, help="Minimum improvement margin to accept patch")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    asyncio.run(run_command(args))


async def run_command(args):
    """Run a command."""
    from hermes_agi import Harness
    
    harness = await Harness.create()
    
    if args.command == "run":
        result = await harness.run(args.task)
        print(result)
    elif args.command == "research":
        result = await harness.research(args.topic, depth=args.depth)
        print(result)
    elif args.command == "think":
        result = await harness.think(args.goal)
        print(result)
    elif args.command == "allocate":
        result = await harness.allocate_hermes(args.task, role=args.role)
        print(result)
    elif args.command == "benchmark":
        result = await harness.benchmark(args.name)
        print(result)
    elif args.command == "spawn":
        result = await harness.spawn(args.bot, args.command)
        print(result)
    elif args.command == "status":
        result = await harness.status()
        print(result)
    elif args.command == "health":
        result = await harness.health()
        print(result)
    elif args.command == "discover":
        result = await harness.discover(args.query)
        print(result)
    elif args.command in ("overnight", "gnhf"):
        from hermes_agi.overnight import OvernightConfig, OvernightLoopController
        config = OvernightConfig(
            objective=args.objective,
            max_iterations=args.max_iterations,
            max_consecutive_failures=args.max_failures,
            use_current_branch=args.current_branch,
            stop_when=args.stop_when,
        )
        controller = OvernightLoopController(config)
        summary = controller.run()
        summary.print_summary()
    elif args.command == "evolve":
        from engines.self_evolution import SelfEvolutionLoop
        loop = SelfEvolutionLoop(minimum_improvement_margin=args.margin)
        print("\n=======================================================")
        print("  HERMES CLOSED-LOOP DARWINIAN SELF-EVOLUTION ENGINE")
        print("=======================================================")
        for i in range(1, args.cycles + 1):
            print(f"\n[Cycle {i}/{args.cycles}] Initiating Darwinian improvement cycle...")
            res = loop.run_evolution_cycle()
            print(f"  Baseline Score:      {res.baseline_score:.4f}")
            print(f"  Final Evolved Score: {res.final_score:.4f}")
            print(f"  Mutations Evaluated: {res.candidates_evaluated}")
            print(f"  Mutations Merged:    {res.mutations_merged}")
            print(f"  Mutations Discarded: {res.mutations_discarded}")
            if res.history:
                print(f"  Outcome Rationale:   {res.history[0].rationale}")
        print("\n=======================================================\n")


if __name__ == "__main__":
    main()
