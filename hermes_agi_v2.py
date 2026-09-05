#!/usr/bin/env python3
"""Hermes AGI/ASI Harness v3.0 — Unified Entry Point.

Replaces: hermes_agi.py, hermes_engine.py, hermes.py, hermes_ultimate.py,
          hermes_supervisor.py, master.py, harness_control_plane.py

Usage:
    python -m hermes_agi_v2                    # Interactive mode
    python -m hermes_agi_v2 --goal "..."       # Execute a goal
    python -m hermes_agi_v2 --interactive      # Interactive mode
    python -m hermes_agi_v2 --health           # Health check
    python -m hermes_agi_v2 --list-plugins     # List plugins
    python -m hermes_agi_v2 --self-model       # Show capability self-model
    python -m hermes_agi_v2 --benchmark        # Run benchmark suite
    python -m hermes_agi_v2 --version          # Show version
    python -m hermes_agi_v2 --help             # Full help
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.runtime.kernel import HermesKernel, KernelConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("hermes_agi")


async def run_goal(goal: str, config: KernelConfig) -> dict:
    """Execute a single goal and return the result."""
    kernel = HermesKernel(config=config)
    await kernel.boot()
    try:
        from core.runtime.kernel import Task
        task = Task(goal=goal)
        task_id = await kernel.submit_task(task)
        return {"status": "submitted", "task_id": task_id, "goal": goal}
    finally:
        await kernel.shutdown()


async def interactive_mode(config: KernelConfig) -> None:
    """Run interactive REPL loop."""
    kernel = HermesKernel(config=config)
    await kernel.boot()
    try:
        print("""
╔══════════════════════════════════════════════════════════════╗
║           HERMES AGI/ASI HARNESS v3.0 UNIFIED            ║
║                                                               ║
║  Free-first, modular, model-agnostic agent harness       ║
║  Type 'help' for commands, 'quit' to exit                    ║
╚══════════════════════════════════════════════════════════════╝
        """)
        while True:
            try:
                user_input = input("\n🎯 Goal> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if user_input.lower() == "help":
                    print("\nCommands:")
                    print("  health     - Health check")
                    print("  plugins    - List plugins")
                    print("  models     - List models")
                    print("  selfmodel  - Show capability self-model")
                    print("  <goal>     - Execute a goal")
                    print("  quit       - Exit")
                    continue
                if user_input.lower() == "health":
                    health = await kernel.health_check()
                    for key, value in health.items():
                        print(f"  {key}: {value}")
                    continue
                if user_input.lower() == "plugins":
                    if kernel.plugin_manager:
                        for p in kernel.plugin_manager.list_plugins():
                            print(f"  {p['name']}: {'✅' if p['enabled'] else '❌'}")
                    continue
                if user_input.lower() == "models":
                    if kernel.model_router:
                        for m in kernel.model_router.list_models():
                            print(f"  {m.name} ({m.provider}) - {m.cost}")
                    continue
                if user_input.lower() == "selfmodel":
                    if kernel.self_model:
                        for k, v in kernel.self_model.capability_summary().items():
                            print(f"  {k}: {v}")
                    else:
                        print("  Self-model not available")
                    continue

                from core.runtime.kernel import Task
                task = Task(goal=user_input)
                task_id = await kernel.submit_task(task)
                print(f"Task submitted: {task_id}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    finally:
        await kernel.shutdown()
    print("\n👋 Hermes AGI/ASI Harness shutdown complete.")


async def health_check(config: KernelConfig) -> None:
    """Run health check on all components."""
    kernel = HermesKernel(config=config)
    await kernel.boot()
    try:
        health = await kernel.health_check()
        print("\n🏥 Health Check:")
        for key, value in health.items():
            print(f"  {key}: {value}")
    finally:
        await kernel.shutdown()


async def list_plugins(config: KernelConfig) -> None:
    """List all registered plugins."""
    kernel = HermesKernel(config=config)
    await kernel.boot()
    try:
        if kernel.plugin_manager:
            plugins = kernel.plugin_manager.list_plugins()
            print(f"\n🔌 Plugins ({len(plugins)} total):")
            for p in plugins:
                status = '✅' if p['enabled'] else '❌'
                caps = p.get('capabilities', [])
                print(f"  {status} {p['name']} ({len(caps)} capabilities)")
        else:
            print("No plugin manager available")
    finally:
        await kernel.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes AGI/ASI Harness v3.0")
    parser.add_argument("--goal", type=str, help="Goal to execute")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--zero-cost", action="store_true", help="Free-first mode")
    parser.add_argument("--offline", action="store_true", help="Offline mode")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--list-plugins", action="store_true", help="List plugins")
    parser.add_argument("--self-model", action="store_true", help="Show self-model")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark suite")
    parser.add_argument("--profile", type=str, default="default", help="Profile name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--version", action="version", version="Hermes AGI/ASI Harness v3.0")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = KernelConfig(
        profile=args.profile,
        zero_cost=args.zero_cost,
        offline=args.offline,
    )

    if args.health:
        asyncio.run(health_check(config))
    elif args.list_plugins:
        asyncio.run(list_plugins(config))
    elif args.goal:
        result = asyncio.run(run_goal(args.goal, config))
        print(f"\n🚀 Goal: {result['goal']}")
        print(f"   Status: {result['status']}")
        print(f"   Task ID: {result['task_id']}")
    elif args.interactive or not any([args.goal, args.health, args.list_plugins, args.benchmark, args.self_model]):
        asyncio.run(interactive_mode(config))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()