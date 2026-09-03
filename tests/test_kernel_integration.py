#!/usr/bin/env python3
"""
Kernel Integration Tests — boot the full HermesKernel with all 11 core plugins
and execute tasks end-to-end.

Tests:
1. Kernel boots all 11 core plugins (no failed loads)
2. All core plugins report healthy
3. Task submission + execution via execution_engine
4. State manager persists task state
5. Memory system stores and retrieves
6. Event bus emits/replays events
7. Recovery engine creates checkpoints
8. Full health check
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ PASS  {name} {detail}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL  {name} {detail}")


async def main():
    global PASS, FAIL
    print("=" * 70)
    print("  HERMES AGI/ASI HARNESS — KERNEL INTEGRATION TESTS")
    print("=" * 70)

    from core.runtime.kernel import HermesKernel, KernelConfig, Task

    print("\n  Booting Hermes Kernel...")
    config = KernelConfig(zero_cost=True, offline=True)
    kernel = HermesKernel(config=config)

    try:
        await kernel.boot()

        # ── Test 1: All 11 core plugins loaded ──────────────────────────
        print("\n  Test 1: Core plugins loaded")
        core_plugins = [
            'security_core', 'event_bus', 'state_manager', 'model_router',
            'memory_system', 'plugin_manager', 'execution_engine',
            'verification_engine', 'recovery_engine', 'evolution_engine',
            'ecosystem_intel'
        ]
        loaded = [name for name in core_plugins if getattr(kernel, name) is not None]
        check("kernel-loads-all-11", len(loaded) == 11,
              f"(loaded {len(loaded)}/11: {loaded})")

        # ── Test 2: Health check ────────────────────────────────────────
        print("\n  Test 2: Health check")
        health = await kernel.health_check()
        all_healthy = health["status"] == "healthy"
        check("kernel-healthy", all_healthy,
              f"(status={health['status']})")

        # ── Test 3: Task submission ─────────────────────────────────────
        print("\n  Test 3: Task submission")
        task = Task(goal="write file integration_test.txt containing KERNEL TEST")
        task_id = await kernel.submit_task(task)
        check("task-submitted", task_id is not None, f"(id={task_id[:8]})")
        await asyncio.sleep(3)

        # ── Test 4: State manager persistence ───────────────────────────
        print("\n  Test 4: State manager persistence")
        if kernel.state_manager:
            session_id = kernel.state_manager.create_session("integration", {"test": True})
            task_id2 = kernel.state_manager.create_task("test task", "desc", session_id=session_id)
            task_obj = kernel.state_manager.get_task(task_id2)
            check("state-session-task", session_id and task_id2 and task_obj is not None,
                  f"(session={session_id[:8]}, task={task_id2[:8]})")
        else:
            check("state-session-task", False, "(state_manager is None)")

        # ── Test 5: Memory system ───────────────────────────────────────
        print("\n  Test 5: Memory system")
        if kernel.memory_system:
            from plugins.memory_system import MemoryType
            mem_id = kernel.memory_system.store(
                memory_type=MemoryType.SEMANTIC,
                content="Hermes harness memory test fact",
                importance=0.9,
                tags=["test", "integration"]
            )
            retrieved = kernel.memory_system.retrieve("Hermes harness", top_k=5)
            check("memory-store-retrieve", mem_id and len(retrieved) >= 1,
                  f"(stored={mem_id[:8]}, retrieved={len(retrieved)})")

            stats = kernel.memory_system.get_stats()
            check("memory-stats", stats["total"] > 0, f"(total={stats['total']})")
        else:
            check("memory-store-retrieve", False, "(memory_system is None)")

        # ── Test 6: Event bus ───────────────────────────────────────────
        print("\n  Test 6: Event bus")
        if kernel.event_bus:
            received = []
            kernel.event_bus.subscribe("test.*", lambda e: received.append(e))
            kernel.event_bus.emit("test.event", {"value": 42})
            check("event-bus-emit", len(received) == 1, f"(received={len(received)})")

            replayed = kernel.event_bus.replay("test.*", limit=10)
            check("event-bus-replay", len(replayed) >= 1, f"(replayed={len(replayed)})")
        else:
            check("event-bus-emit", False, "(event_bus is None)")

        # ── Test 7: Recovery engine ─────────────────────────────────────
        print("\n  Test 7: Recovery engine")
        if kernel.recovery_engine:
            task_id = kernel.state_manager.create_task("ckpt_test", "ckpt desc", session_id=kernel.state_manager.create_session("test", {})) if kernel.state_manager else "test-task-id"
            checkpoint = kernel.recovery_engine.create_checkpoint(task_id, {"step": 1, "state": "test"})
            check("recovery-checkpoint", checkpoint is not None, f"(checkpoint={checkpoint})")
        else:
            check("recovery-checkpoint", False, "(recovery_engine is None)")

        # ── Test 8: Plugin manager ──────────────────────────────────────
        print("\n  Test 8: Plugin manager")
        if kernel.plugin_manager:
            # Discover plugins
            discovered = kernel.plugin_manager.discover_plugins()
            check("plugin-manager-loaded", len(discovered) > 0,
                  f"(plugins discovered={len(discovered)})")
        else:
            check("plugin-manager-loaded", False, "(plugin_manager is None)")

        # ── Test 9: Model router ────────────────────────────────────────
        print("\n  Test 9: Model router")
        if kernel.model_router:
            models = kernel.model_router.list_models()
            active = kernel.model_router.get_active_model().name if kernel.model_router.get_active_model() else "none"
            check("model-router-loaded", len(models) > 0,
                  f"(models={len(models)}, active={active})")
        else:
            check("model-router-loaded", False, "(model_router is None)")

    finally:
        await kernel.shutdown()

    print("\n" + "=" * 70)
    print(f"  KERNEL INTEGRATION TESTS: {PASS} passed, {FAIL} failed")
    print("=" * 70)
    if FAIL > 0:
        sys.exit(1)
    print("  ✅ ALL KERNEL INTEGRATION TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
