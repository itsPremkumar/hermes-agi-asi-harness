"""
Test Suite for Phase 10: Infrastructure & Safety

Tests:
1. Event-Sourced State: emit events, replay, query
2. Rollback Engine: create versions, promote, rollback
3. Scenario Harness: run scenarios, splits
4. Agent Communication: send messages, inbox
5. Research Engine V2: add sources/claims, find contradictions
6. Sandbox Architecture: static check, execute
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print(f"\n{'='*60}")
    print("  PHASE 10: Infrastructure & Safety Tests")
    print(f"{'='*60}")

    results = []

    # Test 1: Event-Sourced State
    print("\n[1/6] Event-Sourced State...")
    try:
        from plugins.event_sourced_state import create as es_create

        plugin = await es_create()
        await plugin.load()

        # Register a reducer
        def task_reducer(state, event):
            if event.event_type == "task.completed":
                state["completed_tasks"] = state.get("completed_tasks", 0) + 1
            return state

        plugin.store.register_reducer("task.completed", task_reducer)

        # Emit events
        plugin.store.emit("task.completed", {"task_id": "T1"})
        plugin.store.emit("task.completed", {"task_id": "T2"})
        plugin.store.emit("task.failed", {"task_id": "T3"})

        # Query events
        completed = plugin.store.get_events(event_type="task.completed")
        assert len(completed) >= 2

        # Check state
        state = plugin.store.get_state()
        assert state.get("completed_tasks") == 2

        stats = plugin.store.get_stats()
        assert stats["total_events"] >= 3

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Event-Sourced State", True, f"events={stats['total_events']}"))
        print(f"  ✓ Event-Sourced State: {stats['total_events']} events")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Event-Sourced State", False, str(e)[:100]))
        print(f"  ✗ Event-Sourced State failed: {e}")

    # Test 2: Rollback Engine
    print("\n[2/6] Rollback Engine...")
    try:
        from plugins.rollback import create as rb_create

        plugin = await rb_create()
        await plugin.load()

        # Create versions
        v1 = plugin.engine.create_version({"kernel": "v1"})
        v2 = plugin.engine.create_version({"kernel": "v2"}, parent=v1.version_id)

        # Promote v2 then rollback to v1
        plugin.engine.promote_version(v2.version_id)
        assert plugin.engine.get_current_version().version_id == v2.version_id

        # Rollback from v2 to v1
        rolled_back = plugin.engine.rollback()
        assert rolled_back == v1.version_id

        stats = plugin.engine.get_stats()
        assert stats["total_versions"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Rollback Engine", True, f"versions={stats['total_versions']}"))
        print(f"  ✓ Rollback Engine: {stats['total_versions']} versions")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Rollback Engine", False, str(e)[:100]))
        print(f"  ✗ Rollback Engine failed: {e}")

    # Test 3: Scenario Harness
    print("\n[3/6] Scenario Harness...")
    try:
        from plugins.scenario_harness import create as sh_create

        plugin = await sh_create()
        await plugin.load()

        # Get scenarios
        scenarios = plugin.harness.get_scenarios()
        assert len(scenarios) > 0

        # Get categories
        categories = plugin.harness.get_categories()
        assert len(categories) >= 5

        # Get splits
        splits = plugin.harness.get_evaluation_splits()
        assert len(splits) >= 1

        # Run a suite
        suite_result = await plugin.harness.run_suite(category="nominal")
        assert suite_result["total"] > 0

        stats = plugin.harness.get_stats()
        assert stats["total_scenarios"] >= 10

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Scenario Harness", True, f"scenarios={stats['total_scenarios']}"))
        print(f"  ✓ Scenario Harness: {stats['total_scenarios']} scenarios")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Scenario Harness", False, str(e)[:100]))
        print(f"  ✗ Scenario Harness failed: {e}")

    # Test 4: Agent Communication
    print("\n[4/6] Agent Communication...")
    try:
        from plugins.agent_communication import create as ac_create

        plugin = await ac_create()
        await plugin.load()

        # Send messages
        await plugin.send(
            task_id="T001",
            sender="agent-a",
            receiver="agent-b",
            message_type="result",
            confidence=0.9,
            artifact_refs=["artifact://patch/123"],
        )

        msg2 = plugin.bus.create_handoff(
            task_id="T001",
            from_agent="agent-a",
            to_agent="agent-c",
            artifact_refs=["artifact://patch/123"],
            context={"summary": "done"},
        )
        plugin.bus.send(msg2)

        # Get inbox
        inbox = await plugin.get_inbox("agent-b")
        assert len(inbox) >= 1

        # Get messages
        messages = plugin.bus.get_messages(task_id="T001")
        assert len(messages) >= 2

        stats = plugin.bus.get_stats()
        assert stats["total_messages"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Agent Communication", True, f"messages={stats['total_messages']}"))
        print(f"  ✓ Agent Communication: {stats['total_messages']} messages")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Agent Communication", False, str(e)[:100]))
        print(f"  ✗ Agent Communication failed: {e}")

    # Test 5: Research Engine V2
    print("\n[5/6] Research Engine V2...")
    try:
        from plugins.research_engine_v2 import create as rv_create

        plugin = await rv_create()
        await plugin.load()

        # Add sources and claims
        sources = [
            {"url": "http://example.com/1", "title": "Source 1", "authority": "high"},
            {"url": "http://example.com/2", "title": "Source 2", "authority": "medium"},
        ]
        report = await plugin.research("Test question?", sources=sources)
        assert report.id is not None

        # Add claim
        claim = plugin.engine.graph.add_claim("Test claim", confidence=0.5)
        assert claim.id is not None

        # Get contradictions
        contradictions = await plugin.find_contradictions()
        assert isinstance(contradictions, list)

        stats = plugin.engine.get_stats()
        assert stats["sources"] >= 2

        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Research Engine V2", True, f"reports={stats['reports']}"))
        print(f"  ✓ Research Engine V2: {stats['reports']} reports, {stats['sources']} sources")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Research Engine V2", False, str(e)[:100]))
        print(f"  ✗ Research Engine V2 failed: {e}")

    # Test 6: Sandbox Architecture
    print("\n[6/6] Sandbox Architecture...")
    try:
        from plugins.sandbox_architecture import create as sa_create

        plugin = await sa_create()
        await plugin.load()

        # Static check
        check = await plugin.static_check("print('hello')")
        assert check["safe"]

        check_bad = await plugin.static_check("import os; os.system('rm -rf /')")
        assert not check_bad["safe"]

        # Execute code
        result = await plugin.execute("print('hello world')")
        assert result.success
        assert "hello" in result.stdout.lower() or "world" in result.stdout.lower() or len(result.stdout) > 0

        stats = {"healthy": True}
        health = await plugin.health()
        assert health["status"] == "healthy"

        results.append(("Sandbox Architecture", True, f"executed={result.success}"))
        print("  ✓ Sandbox Architecture: static_check OK, execution OK")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Sandbox Architecture", False, str(e)[:100]))
        print(f"  ✗ Sandbox Architecture failed: {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Phase 10 Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
