"""Hermes AGI/ASI Harness — offline self-test with REAL asserts.

Runs without network, without API keys, without optional extras.
Every check executes real code paths and asserts real outcomes:

    python -m hermes_agi self-test
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

passed = 0
failed = 0
failures: list[str] = []


def test(name: str):
    """Decorator: run the function, count REAL assert outcomes."""

    def wrap(fn):
        global passed, failed
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - recorded, reported, counted
            failed += 1
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"  FAIL {name} — {exc}")
        else:
            passed += 1
            print(f"  ok   {name}")
        return fn

    return wrap


@test("version is 2.0.0")
def _t_version():
    import hermes_agi

    assert hermes_agi.__version__ == "2.0.0", hermes_agi.__version__


@test("harness creates and reports healthy offline")
def _t_harness_health():
    from hermes_agi import Harness

    async def go():
        h = await Harness.create()
        health = await h.health()
        assert health["status"] == "healthy", health
        assert health["kernel"] == "healthy", health
        status = await h.status()
        assert status["initialized"] is True, status
        assert status["plugins"]["running"] >= 6, status
        assert len(status["benchmarks"]["available"]) >= 10, status
        return health, status

    asyncio.run(go())


@test("all 10 core plugins register on a real PluginManager")
def _t_plugins():
    from hermes_agi.plugins.core_plugins import ALL_PLUGINS, register_all_plugins
    from hermes_agi.plugins.manager import PluginManager

    assert len(ALL_PLUGINS) == 10, len(ALL_PLUGINS)
    mgr = PluginManager()
    register_all_plugins(mgr)
    assert len(mgr.plugins) == 10, len(mgr.plugins)


@test("benchmark runner scores pass/fail honestly")
def _t_benchmark():
    from core.benchmark.harness import BenchmarkRunner

    runner = BenchmarkRunner()
    scores = runner.run(
        [
            {"name": "pass-task", "fn": lambda: True},
            {"name": "fail-task", "fn": lambda: False},
            {"name": "boom-task", "fn": lambda: 1 / 0},
        ]
    )
    by_name = {s.name: s for s in scores}
    assert by_name["pass-task"].passed is True
    assert by_name["fail-task"].passed is False
    assert by_name["boom-task"].passed is False
    assert "ZeroDivisionError" in by_name["boom-task"].error
    summary = runner.summary()
    assert summary["total_tasks"] == 3, summary
    assert summary["passed_tasks"] == 1, summary
    assert summary["measured"] is True


@test("operations watchdog tracks heartbeat and restart budget")
def _t_watchdog():
    from operations import Watchdog

    wd = Watchdog(heartbeat_timeout=60.0, max_restarts=1)
    wd.register("agent-1", pid=1234)
    wd.heartbeat("agent-1", memory_mb=10.0, cpu_percent=5.0)
    assert wd.check_health() == [], "fresh heartbeat must not flag stalled"
    stale = Watchdog(heartbeat_timeout=-1.0)  # negative: any heartbeat is expired
    stale.register("agent-9")
    assert len(stale.check_health()) == 1, "expired heartbeat must flag stalled"
    assert wd.should_restart("agent-1") is True  # budget unused
    assert wd.restart("agent-1") is True  # first restart within budget
    assert wd.should_restart("agent-1") is False  # budget exhausted
    assert wd.restart("agent-1") is False  # refused over budget


@test("operations scheduler orders by priority")
def _t_scheduler():
    from operations import Scheduler

    async def go():
        sch = Scheduler(max_concurrent=2)
        await sch.submit("low", priority=9)
        await sch.submit("high", priority=1)
        first, _ = await sch.get_next()
        assert first == "high", first
        assert sch.running_count == 1, sch.running_count
        assert sch.queue_size == 1, sch.queue_size
        sch.complete("high")
        assert sch.running_count == 0, sch.running_count

    asyncio.run(go())


@test("operations checkpoint round-trips through disk")
def _t_checkpoint():
    import time

    from operations import Checkpoint, CheckpointManager

    with tempfile.TemporaryDirectory() as tmp:
        mgr = CheckpointManager(Path(tmp))
        cp = Checkpoint(
            checkpoint_id="cp-1", agent_id="a1", state={"step": 3}, timestamp=time.time()
        )
        path = mgr.save(cp)
        assert path.exists(), path
        loaded = mgr.load("a1", "cp-1")
        assert loaded is not None and loaded.state == {"step": 3}, loaded
        assert mgr.latest("a1").checkpoint_id == "cp-1"
        assert len(mgr.list_checkpoints("a1")) == 1


@test("operations ledger computes cost, value and ROI")
def _t_ledger():
    import time

    from operations import EconomicEntry, EconomicLedger

    with tempfile.TemporaryDirectory() as tmp:
        ledger = EconomicLedger(Path(tmp) / "ledger.jsonl")
        ledger.record(
            EconomicEntry(
                timestamp=time.time(), agent_id="a1", action="run",
                cost=2.0, value=10.0, task_id="t1",
            )
        )
        assert ledger.total_cost("a1") == 2.0
        assert ledger.total_value("a1") == 10.0
        assert ledger.roi("a1") == 4.0, ledger.roi("a1")
        assert ledger.summary()["total_entries"] >= 1, ledger.summary()


@test("safety risk assessment dataclass works")
def _t_safety():
    from safety import RiskAssessment

    ra = RiskAssessment(
        risk_id="r1", title="t", level="HIGH",
        score=0.9, likelihood=0.5, impact=0.5,
    )
    assert ra.risk_id == "r1"
    assert ra.score == 0.9


@test("harness graph State get/set round-trips")
def _t_graph():
    from harness.graph import State

    st = State()
    st.set("k", "v")
    assert st.get("k") == "v"
    assert st.get("missing", "dflt") == "dflt"


@test("dashboard logic imports without optional fastapi server")
def _t_dashboard():
    import core.dashboard as dash

    assert dash.plugins.count() >= 0
    assert dash.missions.count() >= 0
    assert dash.health.overall_status() is not None
    # Server itself is optional: either a live FastAPI app or None.
    assert (dash.app is None) or hasattr(dash.app, "get"), type(dash.app)


@test("canonical import guard passes (no src.* imports)")
def _t_canonical():
    import re
    from pathlib import Path as _P

    root = _P(__file__).resolve().parent.parent.parent
    bad = []
    for area in ("src/hermes_os", "src/memory", "src/harness", "src/safety"):
        base = root / area
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", text, re.M):
                mod = ((m.group(1) or m.group(2)).split(",")[0].strip())
                if mod.startswith("src."):
                    bad.append(f"{path.name}: {mod}")
    assert not bad, bad[:5]


def main() -> int:
    print(f"Hermes self-test: {passed} passed, {failed} failed")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL SELF-TESTS PASSED")
    return 0
