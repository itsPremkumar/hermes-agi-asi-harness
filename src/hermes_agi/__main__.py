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
    research_parser = subparsers.add_parser(
        "research", help="Run autonomous deep research on a topic"
    )
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
        ov_parser = subparsers.add_parser(
            name, help="Run autonomous overnight endurance loop (gnhf pattern)"
        )
        ov_parser.add_argument("objective", help="High-level engineering objective")
        ov_parser.add_argument(
            "--max-iterations", type=int, default=10, help="Maximum iterations to run"
        )
        ov_parser.add_argument(
            "--max-failures", type=int, default=3, help="Consecutive failure abort limit"
        )
        ov_parser.add_argument(
            "--current-branch", action="store_true", help="Commit directly on current branch"
        )
        ov_parser.add_argument(
            "--stop-when", default="", help="Natural language stopping condition"
        )

    # Evolve command (Darwinian Closed-Loop Self-Improvement)
    evolve_parser = subparsers.add_parser(
        "evolve", help="Run Darwinian Closed-Loop Self-Evolution cycle"
    )
    evolve_parser.add_argument(
        "--cycles", type=int, default=1, help="Number of recursive evolution cycles to run"
    )
    evolve_parser.add_argument(
        "--margin", type=float, default=0.015, help="Minimum improvement margin to accept patch"
    )
    evolve_parser.add_argument(
        "--avo",
        action="store_true",
        help="Use NVIDIA Agentic Variation Operators (AVO) with lineage DAG",
    )

    # Refine command (Prime Agent Continual Self-Refinement)
    subparsers.add_parser(
        "refine", help="Run continual harness self-refinement on session logs (/refine)"
    )

    # REPL command (Prime Agent Recursive Language Model)
    repl_parser = subparsers.add_parser(
        "repl", help="Execute Python code snippet in RLM persistent REPL"
    )
    repl_parser.add_argument(
        "code", nargs="?", default="", help="Python code to evaluate with 'agent' bridge"
    )
    subparsers.add_parser("interactive", help="Interactive task loop (type 'exit' to quit)")

    # Daemon command (24/7 continuous operation)
    daemon_parser = subparsers.add_parser("daemon", help="Run 24/7 continuous daemon loop")
    daemon_parser.add_argument("action", nargs="?", default="run", help="run|enqueue|status|stop")
    daemon_parser.add_argument(
        "request", nargs="?", default="", help="Mission request (for enqueue)"
    )
    daemon_parser.add_argument("--max-iterations", type=int, default=0, help="0 = infinite")
    daemon_parser.add_argument("--poll", type=float, default=2.0, help="Poll interval seconds")

    # Hermes control command
    hx_parser = subparsers.add_parser("hermes", help="Hermes lifecycle control")
    hx_parser.add_argument(
        "action", nargs="?", default="health", help="health|spawn|delegate|kill|update|list"
    )
    hx_parser.add_argument("task", nargs="?", default="", help="Task text for spawn/delegate")
    hx_parser.add_argument("--profile", default="default", help="Hermes profile")
    hx_parser.add_argument("--role", default="leaf", help="leaf|orchestrator")
    hx_parser.add_argument("--background", action="store_true", help="Background spawn")
    hx_parser.add_argument("--iid", default="", help="Instance id for kill")

    # Consolidate (P22 sleep cycle) + invariants
    subparsers.add_parser("consolidate", help="Run P22 memory consolidation (sleep cycle)")
    subparsers.add_parser("invariants", help="Verify 22 safety invariants")
    llm_parser = subparsers.add_parser("llm", help="Hermes-first LLM chain status")
    llm_parser.add_argument("action", nargs="?", default="status", help="status|refresh")
    llm_parser.add_argument("--ask", default="", help="Test prompt sent through the chain")
    api_parser = subparsers.add_parser("api", help="Status API server")
    api_parser.add_argument("action", nargs="?", default="serve", help="serve")
    api_parser.add_argument("--port", type=int, default=8471, help="Local port")
    sb_parser = subparsers.add_parser("sandbox", help="Sandbox execution probe")
    sb_parser.add_argument("code", nargs="?", default="print(42)", help="Python code to run")
    cx_parser = subparsers.add_parser("compact", help="Compact an oversized context file")
    cx_parser.add_argument("file", help="Text file to compact")
    cx_parser.add_argument("--max-chars", type=int, default=12000, help="Compaction threshold")
    subparsers.add_parser("metrics", help="Show per-tool plane metrics summary")
    sk_parser = subparsers.add_parser("skills", help="Skill registry operations")
    sk_parser.add_argument("action", nargs="?", default="list", help="list|search|sync")
    sk_parser.add_argument("query", nargs="?", default="", help="Search text or sync source dir")
    sk_parser.add_argument("--limit", type=int, default=60, help="Max imports on sync")
    kill_parser = subparsers.add_parser("killswitch", help="Kill-switch control")
    kill_parser.add_argument("action", nargs="?", default="status", help="status|engage|release")

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
        if args.avo:
            print("\n=======================================================")
            print("  HERMES NVIDIA AVO (AGENTIC VARIATION OPERATORS) ENGINE")
            print("=======================================================")
            print(f"Running AVO evolution with Lineage DAG & In-Harness Multi-Turn Repair...")
            res = loop.run_avo_evolution(objective="runtime_performance", generations=args.cycles)
            print(f"  Generations Completed:  {res['generations_completed']}")
            print(f"  Candidates Evaluated:   {res['total_candidates_evaluated']}")
            print(f"  Initial Best Fitness:   {res['initial_fitness']:.4f}")
            print(f"  Final Best Fitness:     {res['final_fitness']:.4f}")
            print(f"  Fitness Gain Percent:   {res['fitness_gain_percent']:.2f}%")
            print(f"  Lineage DAG Nodes:      {res['lineage_nodes_count']}")
            print(f"  Interventions Issued:   {res['interventions_issued']}")
            print(f"  Elapsed Time:           {res['elapsed_seconds']:.2f}s")
            print("=======================================================\n")
        else:
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
    elif args.command == "refine":
        from hermes_agi.refine import HarnessRefiner

        refiner = HarnessRefiner()
        report = refiner.refine()
        report.print_summary()
    elif args.command == "repl":
        from hermes_agi.rlm import RLMREPLExecutor

        executor = RLMREPLExecutor()
        code = (
            args.code
            or "print('Hermes RLM REPL Active. Variables and agent.* functions available.')"
        )
        res = executor.execute(code)
        if res.stdout:
            print(res.stdout, end="")
        if res.stderr:
            print(res.stderr, end="", file=sys.stderr)
        if res.returned_value is not None:
            print(res.returned_value)
    elif args.command == "interactive":
        print("=" * 60)
        print("  HERMES interactive mission loop (type 'exit' to quit)")
        print("=" * 60)
        while True:
            try:
                task = input("\nhermes> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not task or task.lower() in ("exit", "quit", "q"):
                break
            try:
                result = await harness.run(task)
                status = result.get("status", "?") if isinstance(result, dict) else result
                print(f"\nResult: {status}")
                if isinstance(result, dict) and result.get("proof"):
                    print(f"Proof: {result['proof'].get('proof_hash', '')[:16]}")
            except Exception as e:
                print(f"Error: {e}")
        print("\nShutdown complete.")
    elif args.command == "daemon":
        from hermes_os.kernel import HermesIntelligenceOS

        os_kernel = HermesIntelligenceOS()
        if args.action == "enqueue" and args.request:
            mid = os_kernel.enqueue(args.request)
            print(f"enqueued {mid}")
        elif args.action == "status":
            print(os_kernel.daemon.stats())
            if getattr(os_kernel, "scheduler", None) is not None:
                print(os_kernel.scheduler.stats())
        elif args.action == "stop":
            os_kernel.daemon.request_stop()
            print("stop requested")
        else:
            max_iter = args.max_iterations or None
            print(f"Starting 24/7 daemon (max_iter={max_iter})... Ctrl+C to stop.")
            try:
                # run_command already runs inside asyncio.run — await directly.
                summary = await os_kernel.run_daemon_forever(
                    poll_interval_seconds=args.poll, max_iterations=max_iter
                )
                print(summary)
            except KeyboardInterrupt:
                os_kernel.daemon.request_stop()
                print("stopped by user")
    elif args.command == "hermes":
        from hermes_os.kernel import HermesIntelligenceOS

        os_kernel = HermesIntelligenceOS()
        ctl = os_kernel.hermes
        if ctl is None:
            print("Hermes controller unavailable")
            return
        if args.action == "spawn" and args.task:
            print(
                ctl.spawn(
                    args.task, profile=args.profile, role=args.role, background=args.background
                ).to_dict()
            )
        elif args.action == "delegate" and args.task:
            print(
                ctl.delegate_task(
                    args.task, role=args.role, background=args.background, profile=args.profile
                )
            )
        elif args.action == "kill" and args.iid:
            print({"killed": ctl.kill(args.iid)})
        elif args.action == "update":
            print(ctl.update())
        elif args.action == "list":
            print(ctl.list_instances())
        else:
            print(ctl.health())
            print(ctl.poll_completions())
    elif args.command == "consolidate":
        from hermes_os.kernel import HermesIntelligenceOS

        os_kernel = HermesIntelligenceOS()
        print(os_kernel.memory.consolidate_p22())
    elif args.command == "invariants":
        from hermes_os.safety_kernel import SafetyKernel

        sk = SafetyKernel()
        print(
            sk.verify_invariants(
                {"action_type": "mission_dispatch", "action_args": {}, "principal": "system:master"}
            )
        )
    elif args.command == "sandbox":
        from hermes_os.docker_sandbox import DockerSandbox

        print(DockerSandbox().run(args.code))
    elif args.command == "metrics":
        from hermes_os.plane_metrics import MetricsCollector

        print(MetricsCollector.for_workspace().get_all_metrics())
    elif args.command == "compact":
        from hermes_os.context_compaction import ContextCompactor
        from pathlib import Path

        text = Path(args.file).read_text(encoding="utf-8")
        rep = ContextCompactor(max_chars=args.max_chars).compact(text, label=Path(args.file).stem)
        print({k: (v if k != "compacted" else f"<{len(v)} chars>") for k, v in rep.items()})
        if rep["compacted_flag"]:
            enc = getattr(sys.stdout, "encoding", None) or "utf-8"
            print(rep["compacted"][:2000].encode(enc, errors="replace").decode(enc))
    elif args.command == "skills":
        from hermes_os.skills import SkillRegistry

        reg = SkillRegistry(workspace_root=".")
        if args.action == "sync":
            src = args.query or "../hermes-agent/skills"
            print(reg.sync_from_dir(src, limit=args.limit))
        elif args.action == "search" and args.query:
            print([s.to_dict() for s in reg.search(args.query)])
        else:
            print([s["name"] for s in reg.list()])
    elif args.command == "api":
        from hermes_os.api import create_app
        import uvicorn

        app = create_app()
        print(
            f"Serving Hermes API on 127.0.0.1:{args.port} (HERMES_API_KEY={'set' if __import__('os').getenv('HERMES_API_KEY') else 'unset-local-only'})"
        )
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    elif args.command == "llm":
        from hermes_os.hermes_llm import HermesFirstLLMClient, resolve_tier

        if args.action == "refresh":
            print(resolve_tier(force_refresh=True))
            return
        client = HermesFirstLLMClient()
        if args.ask:
            out = client.generate(args.ask)
            print(
                {
                    "tier": client.active_tier,
                    "model": client.active_model,
                    "output": (out[:500] if out else None),
                }
            )
        else:
            print(client.status())
    elif args.command == "killswitch":
        from hermes_os.safety_kernel import SafetyKernel

        sk = SafetyKernel()
        if args.action == "engage":
            print({"engaged": sk.engage_kill_switch("manual")})
        elif args.action == "release":
            print({"released": sk.release_kill_switch()})
        else:
            print({"engaged": sk.kill_engaged()})


if __name__ == "__main__":
    main()
