"""Tests for the Hermes-combined ASI surface: real bridge, asi dossier, MCP tools.

All asserts execute real code (Harness boots for real); no canned success.
"""

from __future__ import annotations

import asyncio


def _run(coro):
    return asyncio.run(coro)


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
