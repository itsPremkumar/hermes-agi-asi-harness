#!/usr/bin/env python3
"""
Cognitive Architecture Integration Tests.

Tests the three new components added per the reference analysis:
1. Event Bus — typed async events with topic patterns + replay
2. Reliability Verifier — AST syntax + secret scan + earned-completion
3. ReAct Loop — Thought→Action→Observation cycle with verification gates
4. Red Team Critic — critiques plans, extracts failure lessons

All tests run WITHOUT network. Uses real plugins from the harness.
"""

import asyncio
import sys

sys.path.insert(0, ".")

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ PASS  {name} {detail}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL  {name} {detail}")

async def main():
    from core.runtime.event_bus import EventBus
    from core.runtime.react_loop import ReActLoop, ReliabilityVerifier, RedTeamCritic

    # ─── 1. Event Bus ─────────────────────────────────────────────────
    print("\n  Testing Event Bus...")
    bus = EventBus(max_history=10)

    received = []
    bus.subscribe("agent.*", lambda e: received.append(e))
    bus.subscribe("tool.*", lambda e: received.append(("tool", e.topic)))

    bus.emit("agent.loop_start", {"task": "test"})
    bus.emit("agent.step_start", {"step": 1})
    bus.emit("tool.pre_execute", {"tool": "python_exec"})

    check("event-bus-receive", len(received) == 3,
          f"(got {len(received)} events)")

    # Glob pattern matching
    matched = bus.replay("agent.*", limit=10)
    check("event-bus-replay-pattern", len(matched) == 2,
          f"(got {len(matched)} matching 'agent.*')")

    # No-match pattern
    none_matched = bus.replay("nonexistent.*")
    check("event-bus-replay-no-match", len(none_matched) == 0)

    # ─── 2. Reliability Verifier ────────────────────────────────────────
    print("  Testing Reliability Verifier...")
    v = ReliabilityVerifier()

    # Good code passes
    result = v.verify_python_code("x = 1 + 2\nprint(x)")
    check("verifier-good-code", result["passed"],
          f"(ast={result['checks'].get('ast_syntax')}, secrets={result['checks'].get('zero_secrets')})")

    # Syntax error fails
    result = v.verify_python_code("def broken(:\n    pass")
    check("verifier-syntax-error", not result["passed"],
          f"(ast={result['checks'].get('ast_syntax')})")

    # Secret detection fails
    result = v.verify_python_code("api_key = 'sk-1234567890abcdefghijklmnop'")
    check("verifier-secret-detection", not result["passed"],
          f"(secrets={result['checks'].get('zero_secrets')})")

    # Earned completion: all PASS
    proofs = [{"id": "test1", "status": "PASS"}, {"id": "test2", "status": "PASS"}]
    result = v.verify_earned_completion(proofs)
    check("verifier-earned-complete", result["passed"] and result["confidence"] == 1.0)

    # Earned completion: one FAIL
    proofs = [{"id": "test1", "status": "PASS"}, {"id": "test2", "status": "FAIL"}]
    result = v.verify_earned_completion(proofs)
    check("verifier-partial-complete", not result["passed"] and result["confidence"] == 0.5)

    # ─── 3. Red Team Critic ────────────────────────────────────────────
    print("  Testing Red Team Critic...")
    critic = RedTeamCritic()

    # Plan missing verification
    steps = ["write file", "run script"]
    critiques = critic.critique_plan(steps)
    check("critic-missing-verify", "verification" in str(critiques).lower(),
          f"(critiques={len(critiques)})")

    # Plan too brief
    steps = ["do it"]
    critiques = critic.critique_plan(steps)
    check("critic-too-brief", any("brief" in c.lower() for c in critiques))

    # Good plan passes
    steps = ["analyze", "write code", "verify output", "rollback on error"]
    critiques = critic.critique_plan(steps)
    check("critic-good-plan", len(critiques) == 0, f"(critiques={len(critiques)})")

    # Failure lesson extraction
    lesson = critic.extract_lesson("compute 1+1", "TimeoutError: took 10s")
    check("critic-failure-lesson", lesson["root_cause"] == "Timeout" and len(critic.lessons) == 1,
          f"(root_cause={lesson['root_cause']})")

    # ─── 4. ReAct Loop ────────────────────────────────────────────────
    print("  Testing ReAct Loop...")

    # Build a mini kernel for the loop
    from core.runtime.agent_kernel import build_kernel, WORKING_PLUGINS
    kernel = await build_kernel("plugins", include=WORKING_PLUGINS)

    loop = ReActLoop(event_bus=bus, max_steps=10)

    # Register a test tool
    def fake_python(code: str):
        return {"stdout": "42", "success": True}
    loop.register_tool("python_exec", fake_python)
    loop.register_tool("file_write", lambda path, content: {"success": True})

    # Run a compute-style task (triggers python_exec on step 1)
    result = loop.run("compute the answer to everything")
    check("react-loop-ran", result.success and result.steps >= 1,
          f"(steps={result.steps}, answer={result.final_answer[:60]})")
    check("react-loop-emits-events", len(bus.history) > 0,
          f"(bus has {len(bus.history)} events, loop_start present: {any(e.topic == 'agent.loop_start' for e in bus.history)})")
    check("react-loop-step-history", len(result.step_results) == result.steps,
          f"(history={len(result.step_results)} steps)")

    # Test failure lesson extraction in the loop
    loop_fail = ReActLoop(event_bus=EventBus(), max_steps=10)
    def failing_tool(code: str):
        raise ValueError("SyntaxError: invalid")
    loop_fail.register_tool("python_exec", failing_tool)
    result2 = loop_fail.run("compute something")
    check("react-loop-catches-failures", len(loop_fail.critic.lessons) >= 1,
          f"(lessons={len(loop_fail.critic.lessons)})")

    # ─── 5. Integration with real plugins ─────────────────────────────
    print("  Testing ReAct loop with real plugins...")
    loop2 = ReActLoop(event_bus=EventBus(), max_steps=10)
    loop2.register_tools_from_kernel(kernel)
    check("react-loop-real-tools", "memory_search" in loop2.tools or "file_write" in loop2.tools or
          len(loop2.tools) > 0,
          f"(registered={len(loop2.tools)} tools: {list(loop2.tools.keys())})")

    # Verify the python_tool plugin works through the loop
    loop3 = ReActLoop(event_bus=EventBus(), max_steps=10)
    py_plugin = kernel.get("python_tool")
    if py_plugin and hasattr(py_plugin, "run"):
        loop3.register_tool("python_exec", py_plugin.run)
        result3 = loop3.run("test python execution")
        check("react-loop-real-python", result3.success, f"(steps={result3.steps})")
    else:
        check("react-loop-real-python", False, "(python_tool plugin not available)")

    print("\n" + "=" * 60)
    print(f"  COGNITIVE ARCHITECTURE TESTS: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    if FAIL > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
