#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS — RUNTIME INTEGRATION TESTS
==================================================
End-to-end tests of the agent runtime (kernel + context + planner + agent).
No LLM, no network. All artifacts verified on disk / in memory.
"""

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, '.')

# Isolate all state to a temp dir
_TMP = tempfile.mkdtemp(prefix="hermes_rt_")
os.environ["HERMES_HOME"] = _TMP

from core.runtime.agent import build_agent, AgentResult


async def run(goal: str, verbose: bool = False) -> AgentResult:
    kernel, ctx, agent = await build_agent()
    try:
        return await agent.run(goal, verbose=verbose)
    finally:
        await kernel.shutdown()


def check(name: str, cond: bool, detail: str = ""):
    status = "✅ PASS" if cond else "❌ FAIL"
    print(f"  {status}  {name:<34} {detail}")
    return cond


async def main():
    print("\n" + "=" * 72)
    print("  HERMES RUNTIME INTEGRATION TESTS")
    print("=" * 72 + "\n")

    results = []

    # ── 1. Write file ───────────────────────────────────────────────────
    r1 = await run('write file demo.txt containing HELLO')
    ok = r1.success and os.path.exists("demo.txt") and open("demo.txt").read().strip() == "HELLO"
    results.append(check("write file + verify content", ok, f"content={open('demo.txt').read().strip()!r}" if os.path.exists('demo.txt') else 'no file'))

    # ── 2. Math compute ────────────────────────────────────────────────
    r2 = await run("what is 2**10 + 5?")
    out2 = r2.final_output or {}
    ok = r2.success and isinstance(out2, dict) and out2.get("result") == 1029
    results.append(check("compute 2**10+5 == 1029", ok, f"result={out2.get('result')}"))

    # ── 3. Optimize via swarm ──────────────────────────────────────────
    r3 = await run("optimize sum of squares in [-3,3]")
    out3 = r3.final_output or {}
    bp = out3.get("best_position", [1, 1])
    dist = (bp[0]**2 + bp[1]**2) ** 0.5 if isinstance(bp, list) and len(bp) == 2 else 999
    ok = r3.success and dist < 1.0
    results.append(check("swarm optimize -> origin", ok, f"best={[round(v,3) for v in bp]}, dist={dist:.3f}"))

    # ── 4. Remember + recall ────────────────────────────────────────────
    r4a = await run("remember that the project uses MIT license")
    mem_id = r4a.final_output
    ok_store = r4a.success and isinstance(mem_id, str) and mem_id.startswith("mem_")
    # Recall it
    r4b = await run("search memory for MIT license")
    out4 = r4b.final_output or []
    found = any("MIT" in str(m.get("content", "")) for m in (out4 if isinstance(out4, list) else []))
    ok = ok_store and r4b.success and found
    results.append(check("remember + recall from memory", ok, f"stored={ok_store}, recalled={found}"))

    # ── 5. Audit + permission exercised on a permission-gated step ──────
    # Use a shell command (run_shell permission) — verify audit log captures it
    r5 = await run('run command "echo audit_test_marker"')
    # Audit log should contain the agent.task.start / step entries
    audit_plugin = None
    kernel, ctx, agent = await build_agent()
    try:
        audit_plugin = kernel.get("audit_logger")
        audit_plugin.flush()
        entries = audit_plugin.query()
        has_audit = any("agent" in (e.get("actor", "")) for e in entries)
    finally:
        await kernel.shutdown()
    ok = r5.success and has_audit
    results.append(check("audit log captures agent actions", ok, f"shell_ok={r5.success}, audit_entries={len(entries) if 'entries' in dir() else 0}"))

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"\n{'=' * 72}")
    print(f"  RUNTIME TESTS: {passed}/{total} passed")
    print(f"{'=' * 72}\n")

    return passed == total


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
