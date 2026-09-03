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
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover features")
    discover_parser.add_argument("query", nargs="?", default="", help="Search query")
    
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


if __name__ == "__main__":
    main()
