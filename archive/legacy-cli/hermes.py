#!/usr/bin/env python3
"""
Hermes Agent CLI — run tasks through the plugin harness.

Usage:
  python hermes.py run "write file demo.txt containing HELLO"
  python hermes.py run "what is 2**10 + 5?"
  python hermes.py run "optimize sum of squares in [-3,3]"
  python hermes.py run "remember that the project uses MIT license"
  python hermes.py interactive

All plugins run locally — no LLM API required.
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile

# Ensure project root on path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from core.runtime.agent import build_agent, AgentResult


def _ensure_temp_home():
    """Isolate state/memory/audit to a temp dir so the repo stays clean."""
    home = os.environ.get("HERMES_HOME")
    if not home:
        home = tempfile.mkdtemp(prefix="hermes_run_")
        os.environ["HERMES_HOME"] = home
    return home


async def run_task(task: str, verbose: bool = True) -> AgentResult:
    home = _ensure_temp_home()
    kernel, ctx, agent = await build_agent()
    try:
        result = await agent.run(task, verbose=verbose)
        return result
    finally:
        await kernel.shutdown()


async def interactive():
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


def main():
    parser = argparse.ArgumentParser(description="Hermes Agent CLI")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a single task")
    run_p.add_argument("task", help="The task description (string)")
    run_p.add_argument("--quiet", action="store_true", help="Suppress streaming output")

    sub.add_parser("interactive", help="Interactive REPL")

    args = parser.parse_args()

    if args.command == "run":
        result = asyncio.run(run_task(args.task, verbose=not args.quiet))
        # Final machine-readable summary
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

    elif args.command == "interactive":
        asyncio.run(interactive())

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
