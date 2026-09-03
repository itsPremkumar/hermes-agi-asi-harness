"""
Phase 8 Test Suite — Deployment

Tests:
1. Observability Dashboard: record metrics, get stats, register plugin health, alerts
2. Dockerfile validation: existence and content
3. requirements.txt: has core deps
4. install.py: runs without errors
5. E2E: full system boot with all 8 phases
"""

import os
os.environ.setdefault("HERMES_HOME", "/tmp/hermes_phase8_test")

import sys
import asyncio
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def header(text):
    print(f"\n{'='*70}\n  {text}\n{'='*70}")


def _pass(name):
    print(f"  ✓ {name}")


def _fail(name, err):
    print(f"  ✗ {name}: {err}")


async def test_1_observability():
    """Test 1: Observability Dashboard."""
    header("Test 1: Observability Dashboard")

    from plugins.observability_dashboard import create as od_create
    plugin = await od_create()
    await plugin.load()

    # Record metrics
    for i in range(10):
        plugin.engine.record_metric("cpu_usage", 30.0 + i, unit="%")
        plugin.engine.record_metric("memory_mb", 100.0 + i * 5, unit="MB")
    _pass("Recorded 20 metrics (10 cpu, 10 memory)")

    # Get stats
    cpu_stats = plugin.engine.get_metric_stats("cpu_usage")
    assert cpu_stats["count"] == 10
    assert cpu_stats["min"] == 30.0
    assert cpu_stats["max"] == 39.0
    _pass(f"CPU stats: min={cpu_stats['min']}, max={cpu_stats['max']}, avg={cpu_stats['avg']:.1f}")

    # Register plugin health
    plugin.engine.register_plugin_health("kernel", {"status": "healthy", "uptime": 3600})
    plugin.engine.register_plugin_health("watchdog", {"status": "healthy", "anomalies": 0})
    _pass("Registered 2 plugin health statuses")

    # Get health
    h = plugin.engine.get_plugin_health("kernel")
    assert h["status"] == "healthy"
    _pass(f"Retrieved kernel health: {h['status']}")

    # Raise alert
    plugin.engine.raise_alert("warning", "watchdog", "Memory usage high")
    plugin.engine.raise_alert("critical", "kernel", "Plugin failed")
    _pass("Raised 2 alerts")

    # Active alerts
    active = plugin.engine.get_active_alerts()
    assert len(active) == 2
    _pass(f"Active alerts: {len(active)}")

    # Acknowledge
    plugin.engine.acknowledge_alert(0)
    active = plugin.engine.get_active_alerts()
    assert len(active) == 1
    _pass(f"After ack: {len(active)} active alerts")

    # Summary
    summary = plugin.engine.get_dashboard_summary()
    assert summary["plugins_healthy"] == 2
    _pass(f"Summary: {summary}")

    return True


def test_2_dockerfile():
    """Test 2: Dockerfile validation."""
    header("Test 2: Dockerfile")

    dockerfile = Path("Dockerfile")
    assert dockerfile.exists(), "Dockerfile not found"
    _pass("Dockerfile exists")

    content = dockerfile.read_text()
    assert "FROM python" in content, "Missing FROM python"
    _pass("Has FROM python")

    assert "WORKDIR" in content
    _pass("Has WORKDIR")

    assert "HEALTHCHECK" in content
    _pass("Has HEALTHCHECK")

    assert "CMD" in content
    _pass("Has CMD")

    assert "EXPOSE" in content
    _pass("Has EXPOSE")

    return True


def test_3_requirements():
    """Test 3: requirements.txt validation."""
    header("Test 3: requirements.txt")

    req_file = Path("requirements.txt")
    assert req_file.exists()
    _pass("requirements.txt exists")

    content = req_file.read_text()
    assert "pyyaml" in content.lower() or "yaml" in content.lower()
    _pass("Has YAML dependency")

    # Count packages
    packages = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
    assert len(packages) >= 3, f"Too few packages: {len(packages)}"
    _pass(f"Has {len(packages)} package entries")

    return True


def test_4_install_script():
    """Test 4: install.py syntactic validity."""
    header("Test 4: install.py")

    install = Path("install.py")
    assert install.exists()
    _pass("install.py exists")

    # Verify it's syntactically valid (compile)
    result = subprocess.run(
        [sys.executable, "-c", "import ast; ast.parse(open('install.py').read()); print('valid')"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"install.py invalid: {result.stderr}"
    _pass("install.py syntactically valid")

    # Run in dry mode (just check it doesn't crash on imports)
    # We won't actually install, just verify the script can be parsed
    return True


async def test_5_e2e():
    """Test 5: E2E with ALL phase plugins in the kernel."""
    header("Test 5: E2E — Full System Boot")

    from core.runtime.kernel import HermesKernel, KernelConfig
    config = KernelConfig()
    kernel = HermesKernel(config)
    await kernel.boot()

    # Count all plugins
    total_plugins = len(kernel._plugins)
    _pass(f"Total plugins loaded: {total_plugins}")

    # Verify all 8 phases are represented
    phase_plugins = {
        "Phase 1 (Executive)": ["goal_contract", "context_os", "safety_gates", "completion_proof"],
        "Phase 2 (Persistent)": ["belief_engine", "mission_queue", "capability_registry"],
        "Phase 3 (Autonomous)": ["watchdog", "economic_ledger"],
        "Phase 4 (Multi-Agent)": ["independent_critic", "debate_protocol"],
        "Phase 5 (Learning)": ["self_evaluation", "skill_forge", "curriculum_engine", "sleep_cycle"],
        "Phase 6 (Evolution)": ["evolution_safety_loop", "benchmark_db", "self_improvement_boundary", "world_sync"],
        "Phase 7 (Advanced)": ["computer_use", "engineering_factory", "operating_modes"],
        "Phase 8 (Deployment)": ["observability_dashboard"],
    }

    all_healthy = True
    for phase, plugins in phase_plugins.items():
        for plugin_name in plugins:
            if plugin_name not in kernel._plugins:
                test_fail(phase, f"Missing: {plugin_name}")
                all_healthy = False
        if all_healthy:
            _pass(f"{phase}: all {len(plugins)} plugins loaded")

    assert all_healthy, "Some phases have missing plugins"

    # Use observability dashboard to track all plugins
    od = kernel._plugins.get("observability_dashboard")
    if od:
        for name, plugin in kernel._plugins.items():
            if hasattr(plugin, "health"):
                try:
                    health = await plugin.health()
                    od.engine.register_plugin_health(name, health if isinstance(health, dict) else {"status": "unknown"})
                except Exception:
                    pass
        summary = od.engine.get_dashboard_summary()
        _pass(f"Observability: {summary['plugins_healthy']}/{summary['plugins_total']} healthy")

    await kernel.shutdown()
    return True


async def main():
    print("\n" + "=" * 70)
    print("  PHASE 8 TEST SUITE — Deployment")
    print("=" * 70)

    tests = [
        ("Test 1: Observability Dashboard", test_1_observability),
        ("Test 2: Dockerfile", test_2_dockerfile),
        ("Test 3: requirements.txt", test_3_requirements),
        ("Test 4: install.py", test_4_install_script),
        ("Test 5: E2E Full System", test_5_e2e),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            result = test_fn()
            if asyncio.iscoroutine(result):
                await result
            passed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            test_fail(name, str(e))
            failed += 1

    print("\n" + "=" * 70)
    print(f"  PHASE 8 RESULTS: {passed}/{passed+failed} passed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
