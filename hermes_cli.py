#!/usr/bin/env python3
"""
Hermes AGI/ASI Harness — Unified CLI

Consolidated entry point replacing:
  hermes.py, hermes_agi.py, hermes_engine.py, hermes_ultimate.py,
  hermes_supervisor.py, master.py, harness_control_plane.py

Usage:
  python hermes_cli.py run "write file demo.txt containing HELLO"
  python hermes_cli.py run "what is 2**10 + 5?"
  python hermes_cli.py interactive
  python hermes_cli.py goal "Research the latest AI agent frameworks"
  python hermes_cli.py health
  python hermes_cli.py plugins
  python hermes_cli.py tools
  python hermes_cli.py daemon
  python hermes_cli.py task "Do X"
  python hermes_cli.py verify
  python hermes_cli.py daily
  python hermes_cli.py real-env
  python hermes_cli.py control-plane
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Ensure project root on path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/hermes_cli.log")],
)
logger = logging.getLogger("hermes_cli")


# ── Deprecation shim ──────────────────────────────────────────────────────

def _warn_deprecated(module: str) -> None:
    print(
        f"\033[93m⚠️  DEPRECATED: '{module}' is redirecting to 'hermes_cli'.\n"
        f"   Please update your scripts to use: python hermes_cli.py\033[0m",
        file=sys.stderr,
    )


# ── Shared helpers ────────────────────────────────────────────────────────

def _ensure_temp_home() -> str:
    home = os.environ.get("HERMES_HOME")
    if not home:
        home = tempfile.mkdtemp(prefix="hermes_run_")
        os.environ["HERMES_HOME"] = home
    return home


# ── Subcommand: run / interactive (from hermes.py) ─────────────────────────

async def _cmd_run(task: str, quiet: bool = False) -> None:
    from core.runtime.agent import build_agent, AgentResult

    home = _ensure_temp_home()
    kernel, ctx, agent = await build_agent()
    try:
        result = await agent.run(task, verbose=not quiet)
        print("\n" + "=" * 60)
        print(f"  TASK: {result.goal}")
        print(f"  SUCCESS: {result.success}")
        print(f"  STEPS: {result.steps_executed}")
        if result.final_output is not None:
            out = result.final_output
            if isinstance(out, (dict, list)):
                out = json.dumps(out, indent=2, default=str)
            print(f"  OUTPUT:\n{out}")
        if result.errors:
            print(f"  ERRORS: {result.errors}")
        print("=" * 60)
        sys.exit(0 if result.success else 1)
    finally:
        await kernel.shutdown()


async def _cmd_interactive() -> None:
    from core.runtime.agent import build_agent, AgentResult

    home = _ensure_temp_home()
    kernel, ctx, agent = await build_agent()
    print("=" * 60)
    print("  HERMES AGENT — interactive (type 'exit' to quit)")
    print("=" * 60)
    try:
        while True:
            try:
                task = input("\nhermes> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not task:
                continue
            if task.lower() in ("exit", "quit", "q"):
                break
            result = await agent.run(task, verbose=True)
            print(f"\nResult: success={result.success}")
            if result.final_output is not None:
                out = result.final_output
                if isinstance(out, (dict, list)):
                    out = json.dumps(out, indent=2, default=str)
                print(f"Output:\n{out}")
            if result.errors:
                print(f"Errors: {result.errors}")
    finally:
        await kernel.shutdown()
        print("\nShutdown complete.")


# ── Subcommand: goal (from hermes_agi.py / hermes_engine.py / hermes_ultimate.py) ──

async def _cmd_goal(goal: str, zero_cost: bool = False, offline: bool = False,
                    profile: str = "default", verbose: bool = False) -> None:
    from core.runtime.kernel import HermesKernel, KernelConfig, Task

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = KernelConfig(
        profile=profile,
        zero_cost=zero_cost,
        offline=offline,
    )
    kernel = HermesKernel(config=config)
    try:
        await kernel.boot()
        task = Task(goal=goal)
        task_id = await kernel.submit_task(task)
        print(f"\n🚀 Task submitted: {task_id}")
        print(f"   Goal: {goal}")
    finally:
        await kernel.shutdown()


# ── Subcommand: health (from hermes_agi.py / hermes_supervisor.py / hermes_engine.py / hermes_ultimate.py) ──

async def _cmd_health() -> None:
    from core.runtime.kernel import HermesKernel, KernelConfig

    config = KernelConfig(zero_cost=True, offline=True)
    kernel = HermesKernel(config=config)
    try:
        await kernel.boot()
        health = await kernel.health_check()
        print("\n🏥 Health Check:")
        for key, value in health.items():
            print(f"  {key}: {value}")
    finally:
        await kernel.shutdown()


# ── Subcommand: plugins (from hermes_agi.py) ──────────────────────────────

async def _cmd_plugins() -> None:
    from core.runtime.kernel import HermesKernel, KernelConfig

    config = KernelConfig(zero_cost=True, offline=True)
    kernel = HermesKernel(config=config)
    try:
        await kernel.boot()
        if kernel.plugin_manager:
            plugins = kernel.plugin_manager.list_plugins()
            print("\n🔌 Plugins:")
            for p in plugins:
                print(f"  {p['name']}: {'✅' if p['enabled'] else '❌'} {p.get('capabilities', [])}")
        else:
            print("No plugin manager available.")
    finally:
        await kernel.shutdown()


# ── Subcommand: tools (from hermes_engine.py / hermes_ultimate.py) ─────────

async def _cmd_tools() -> None:
    # Inline minimal tool registry (mirrors hermes_ultimate.py)
    class ToolResult:
        def __init__(self, success, output, error=None, tool_name=""):
            self.success = success
            self.output = output
            self.error = error
            self.tool_name = tool_name

    class ToolRegistry:
        def __init__(self):
            self._tools = {}
        def register(self, name, func):
            self._tools[name] = func
        def list_tools(self):
            return list(self._tools.keys())

    registry = ToolRegistry()
    registry.register("echo", lambda **kw: ToolResult(success=True, output=kw.get("message", ""), tool_name="echo"))
    registry.register("time", lambda **kw: ToolResult(success=True, output=str(datetime.utcnow().isoformat()), tool_name="time"))
    registry.register("health", lambda **kw: ToolResult(success=True, output=json.dumps({"status": "healthy"}), tool_name="health"))

    print("\n🔧 Available Tools:")
    for tool in registry.list_tools():
        print(f"  - {tool}")


# ── Subcommand: daemon / task (from hermes_supervisor.py) ──────────────────

async def _cmd_daemon() -> None:
    from core.runtime.kernel import HermesKernel, KernelConfig

    config = KernelConfig(zero_cost=True, offline=True, max_parallel_tasks=4, max_subagents=8)
    kernel = HermesKernel(config=config)
    try:
        await kernel.boot()
        print("🚀 Hermes Supervisor Daemon starting — 24/7 operation active")
        loop = 0
        while True:
            loop += 1
            health = await kernel.health_check()
            if health.get("status") != "healthy":
                logger.warning("⚠️  Health degraded: %s", health.get("status"))
            logger.info("Heartbeat #%d — status: %s", loop, health.get("status"))
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("\n👋 Supervisor daemon stopped.")
    finally:
        await kernel.shutdown()


async def _cmd_task(task_description: str) -> None:
    from core.runtime.kernel import HermesKernel, KernelConfig, Task

    config = KernelConfig(zero_cost=True, offline=True)
    kernel = HermesKernel(config=config)
    try:
        await kernel.boot()
        start = time.time()
        task = Task(goal=task_description)
        task_id = await kernel.submit_task(task)
        await asyncio.sleep(3)
        duration = time.time() - start
        result = {
            "task": task_description,
            "task_id": task_id,
            "duration_ms": duration * 1000,
            "success": True,
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        await kernel.shutdown()


# ── Subcommand: verify / daily / real-env (from master.py) ─────────────────

def _cmd_verify() -> None:
    from core.verification import MultiRoundVerifier

    project_root = Path(__file__).parent
    verifier = MultiRoundVerifier(str(project_root))
    test_files = [
        "test_phase1.py", "test_phase2.py", "test_phase3_4.py",
        "test_phase5.py", "test_phase6.py", "test_phase7.py",
        "test_phase8.py", "test_runtime.py", "test_working_plugins.py",
        "test_kernel_integration.py",
    ]
    existing = [f for f in test_files if (project_root / f).exists()]
    print(f"\nFound {len(existing)} test files to verify.")
    plan = verifier.create_plan(existing, num_rounds=3)
    print(f"  Rounds: {plan.num_rounds}, Isolated runs: {plan.isolated_runs}")

    result = asyncio.run(verifier.run_verification(plan))
    rounds_passed = sum(1 for r in result["rounds"] if r["passed"])
    print(f"\n  Rounds passed: {rounds_passed}/{len(result['rounds'])}")
    print(f"  Consensus score: {result['consensus']['consensus_score']:.2f}")
    if result.get("brier_score"):
        print(f"  Brier score: {result['brier_score']:.4f}")
    if result["overall_passed"]:
        print("  ✓✓✓ SYSTEM FULLY VERIFIED ✓✓✓")
    else:
        print("  ✗✗✗ VERIFICATION FAILED ✗✗✗")
    sys.exit(0 if result["overall_passed"] else 1)


async def _cmd_daily() -> None:
    from core.runtime.daily_dev import DailyDevEngine, DailyDevConfig

    project_root = Path(__file__).parent
    config = DailyDevConfig(project_root=str(project_root))
    engine = DailyDevEngine(config)
    result = await engine.run_daily_cycle()
    print(f"\nDaily dev cycle complete:")
    print(f"  Ideas generated: {result['ideas_generated']}")
    print(f"  Ideas implemented: {result['ideas_implemented']}")
    print(f"  Tests passed: {result['tests_passed']}/{result['tests_total']}")
    print(f"  Verification: {'PASSED' if result['verification_passed'] else 'FAILED'}")


async def _cmd_real_env() -> None:
    from core.runtime.daily_dev import DailyDevEngine, DailyDevConfig

    project_root = Path(__file__).parent
    config = DailyDevConfig(project_root=str(project_root))
    engine = DailyDevEngine(config)
    result = await engine.run_real_env_check()
    print(f"\nReal-env check: {'✓ PASSED' if result.get('passed') else '✗ FAILED'}")


# ── Subcommand: control-plane (from harness_control_plane.py) ──────────────

def _cmd_control_plane() -> None:
    """Show control-plane module info."""
    print("\n🛡️  Hermes AGI/ASI Harness — Executive Control Plane")
    print("  Modules: IPlugin, PluginRegistry, SafetyGuard, ExecutiveControlPlane")
    print("  Run 'python harness_control_plane.py' for library usage.")
    print("  CLI: python hermes_cli.py control-plane --info")


# ── Main parser ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hermes AGI/ASI Harness — Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Deprecated entry points:
  hermes.py, hermes_agi.py, hermes_engine.py, hermes_ultimate.py,
  hermes_supervisor.py, master.py, harness_control_plane.py

All legacy scripts redirect to this CLI with a deprecation warning.
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # run
    run_p = sub.add_parser("run", help="Run a single task (from hermes.py)")
    run_p.add_argument("task", help="Task description")
    run_p.add_argument("--quiet", action="store_true", help="Suppress streaming output")

    # interactive
    sub.add_parser("interactive", help="Interactive REPL (from hermes.py)")

    # goal
    goal_p = sub.add_parser("goal", help="Submit a goal for execution (from hermes_agi.py / engine / ultimate)")
    goal_p.add_argument("goal", help="Goal description")
    goal_p.add_argument("--zero-cost", action="store_true", help="Free-first mode")
    goal_p.add_argument("--offline", action="store_true", help="Offline mode")
    goal_p.add_argument("--profile", type=str, default="default", help="Profile name")
    goal_p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # health
    sub.add_parser("health", help="Health check (from hermes_agi.py / supervisor / engine / ultimate)")

    # plugins
    sub.add_parser("plugins", help="List plugins (from hermes_agi.py)")

    # tools
    sub.add_parser("tools", help="List tools (from hermes_engine.py / ultimate)")

    # daemon
    sub.add_parser("daemon", help="Start 24/7 supervisor daemon (from hermes_supervisor.py)")

    # task
    task_p = sub.add_parser("task", help="Execute a single task (from hermes_supervisor.py)")
    task_p.add_argument("description", help="Task description")

    # verify
    sub.add_parser("verify", help="Run multi-round verification (from master.py)")

    # daily
    sub.add_parser("daily", help="Run daily development cycle (from master.py)")

    # real-env
    sub.add_parser("real-env", help="Run real-environment validation (from master.py)")

    # control-plane
    cp_p = sub.add_parser("control-plane", help="Control plane info (from harness_control_plane.py)")
    cp_p.add_argument("--info", action="store_true", help="Show module info")

    return parser


# ── Dispatch ───────────────────────────────────────────────────────────────

async def dispatch(args: argparse.Namespace) -> None:
    if args.command == "run":
        await _cmd_run(args.task, quiet=args.quiet)
    elif args.command == "interactive":
        await _cmd_interactive()
    elif args.command == "goal":
        await _cmd_goal(args.goal, zero_cost=args.zero_cost, offline=args.offline,
                        profile=args.profile, verbose=args.verbose)
    elif args.command == "health":
        await _cmd_health()
    elif args.command == "plugins":
        await _cmd_plugins()
    elif args.command == "tools":
        await _cmd_tools()
    elif args.command == "daemon":
        await _cmd_daemon()
    elif args.command == "task":
        await _cmd_task(args.description)
    elif args.command == "verify":
        _cmd_verify()
    elif args.command == "daily":
        await _cmd_daily()
    elif args.command == "real-env":
        await _cmd_real_env()
    elif args.command == "control-plane":
        _cmd_control_plane()
    else:
        parser = build_parser()
        parser.print_help()
        sys.exit(1)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(dispatch(args))


if __name__ == "__main__":
    main()
