"""Tests for the Hermes-combined ASI surface: real bridge, asi dossier, MCP tools.

All asserts execute real code (Harness boots for real); no canned success.
"""

from __future__ import annotations

import asyncio


def _run(coro):
    return asyncio.run(coro)


def test_deliberation_grounds_in_hermes_context():
    from hermes_agi.thinking import DeepThinkingEngine

    hermes = {"home": "H", "profiles": 2, "skills": 3, "boards": 1, "cron_jobs": 4}

    async def go():
        engine = DeepThinkingEngine()
        result = await engine.deliberate("grounding probe", context={"hermes": hermes})
        d = result.to_dict()
        assert d["context_used"] == {"hermes": hermes}, d
        assert any("Grounded in live Hermes home" in line for line in d["reasoning_trace"]), d

    _run(go())


def test_deliberation_without_context_unchanged():
    from hermes_agi.thinking import DeepThinkingEngine

    async def go():
        engine = DeepThinkingEngine()
        result = await engine.deliberate("bare probe")
        d = result.to_dict()
        assert d["context_used"] == {}, d
        assert not any("Grounded in live Hermes home" in line for line in d["reasoning_trace"]), d

    _run(go())


def test_bridge_run_is_real():
    from hermes_agi.bridge import HermesBridge

    async def go():
        bridge = await HermesBridge.create(None)
        try:
            result = await bridge.run("bridge smoke task")
            assert result["status"] in ("completed", "failed"), result
            assert result["task"] == "bridge smoke task", result
            assert "plan" in result or "error" in result, result
        finally:
            await bridge.shutdown()

    _run(go())


def test_bridge_status_health_shape():
    from hermes_agi.bridge import HermesBridge

    async def go():
        bridge = await HermesBridge.create(None)
        try:
            status = await bridge.status()
            assert {"kernel", "bots", "benchmarks", "improvement"} <= set(status), status
            health = await bridge.health()
            assert health["status"] in ("healthy", "degraded"), health
            assert "harness" in health, health
        finally:
            await bridge.shutdown()

    _run(go())


def test_bridge_dispatch_routes():
    from hermes_agi.bridge import HermesBridge

    async def go():
        bridge = await HermesBridge.create(None)
        try:
            assert await bridge.dispatch("") == {"error": "Empty command"}
            status = await bridge.dispatch("status")
            assert "kernel" in status, status
            health = await bridge.dispatch("health")
            assert health["status"] in ("healthy", "degraded"), health
            disc = await bridge.dispatch("discover planning")
            assert disc["query"] == "planning" or "features" in disc or "total" in disc, disc
        finally:
            await bridge.shutdown()

    _run(go())


def test_asi_dossier_structure():
    from hermes_agi import Harness

    async def go():
        harness = await Harness.create()
        try:
            dossier = await harness.asi("asi dossier smoke task")
            assert dossier["task"] == "asi dossier smoke task", dossier
            assert set(dossier["stages"]) == {"deliberation", "execution", "verification"}, dossier
            assert dossier["status"] in ("completed", "failed"), dossier
            assert "duration_s" in dossier and dossier["duration_s"] >= 0, dossier
            assert "proof" in dossier, dossier
            # Live Hermes grounding: read-only mirror attached, deliberation used it.
            ctx = dossier.get("hermes_context", {})
            assert {"home", "profiles", "skills", "boards", "cron_jobs"} <= set(ctx), ctx
            deliberation = dossier["stages"]["deliberation"]
            if isinstance(deliberation, dict) and "context_used" in deliberation:
                assert deliberation["context_used"].get("hermes") == ctx, deliberation
        finally:
            await harness.shutdown()

    _run(go())


def test_mcp_server_exposes_ten_tools():
    from core.mcp.stdio_server import build_server

    async def go():
        server = build_server()
        return sorted(t.name for t in await server.list_tools())

    names = _run(go())
    expected = sorted(
        ["asi", "run_task", "think", "research", "benchmark",
         "spawn_bot", "discover", "allocate", "status", "health"]
    )
    assert names == expected, names


def test_spawn_cli_prints_result():
    """Regression: the spawn positional once shadowed the subcommand dest,
    so `hermes_agi spawn <bot> <cmd>` printed nothing and exited 0."""
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "hermes_agi", "spawn", "harness-coder", "cli smoke"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    assert "spawned" in proc.stdout, proc.stdout[-500:]
