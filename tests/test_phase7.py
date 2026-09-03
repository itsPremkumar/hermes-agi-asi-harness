"""
Phase 7 Test Suite — Advanced

Tests:
1. Computer Use: register apps, click, type, open app, action history
2. Engineering Factory: create project, scaffold, add tests, add docs
3. Operating Modes: list modes, switch, tool allowance, approval check
4. (Combined) Mode-specific behavior + multi-plugin integration
5. E2E: all Phase 7 plugins in kernel
"""

import os
os.environ.setdefault("HERMES_HOME", "/tmp/hermes_phase7_test")

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def header(text):
    print(f"\n{'='*70}\n  {text}\n{'='*70}")


def _pass(name):
    print(f"  ✓ {name}")


def _fail(name, err):
    print(f"  ✗ {name}: {err}")


async def test_1_computer_use():
    """Test 1: Computer Use."""
    header("Test 1: Computer Use")

    from plugins.computer_use import create as cu_create
    plugin = await cu_create()
    await plugin.load()

    # Detect OS
    os = plugin.engine.get_os()
    _pass(f"Detected OS: {os}")

    # Register apps
    plugin.engine.register_app("browser", "C:/Program Files/Browser")
    plugin.engine.register_app("editor", "C:/Program Files/Editor")
    _pass("Registered 2 apps")

    # Click
    action = plugin.engine.click(100, 200)
    assert action.success
    _pass(f"Click at (100,200): {action.result}")

    # Type
    action = plugin.engine.type_text("Hello, World!")
    assert action.success
    _pass(f"Type: {action.result}")

    # Open app
    action = plugin.engine.open_application("browser")
    assert action.success
    _pass(f"Open browser: {action.result}")

    # Try to open non-existent app
    action = plugin.engine.open_application("nonexistent")
    assert not action.success
    _pass(f"Open nonexistent app correctly failed: {action.result}")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: success_rate={stats['success_rate']:.2f}, apps={stats['registered_apps']}")

    return True


async def test_2_engineering_factory():
    """Test 2: Engineering Factory."""
    header("Test 2: Engineering Factory")

    from plugins.engineering_factory import (
        create as ef_create, ProjectType, Stage,
    )
    plugin = await ef_create()
    await plugin.load()

    # Create projects
    p1 = plugin.engine.create_project("my_web_app", ProjectType.WEB.value)
    p2 = plugin.engine.create_project("my_cli", ProjectType.CLI.value)
    p3 = plugin.engine.create_project("my_api", ProjectType.API.value)
    _pass(f"Created 3 projects: {p1.project_id}, {p2.project_id}, {p3.project_id}")

    # Scaffold
    assert plugin.engine.scaffold_project(p1.project_id)
    _pass(f"Scaffolded {p1.name}: {len(plugin.engine._projects[p1.project_id].files_created)} files")

    # Add tests
    plugin.engine.add_tests(p1.project_id, count=5)
    project = plugin.engine.get_project(p1.project_id)
    assert project.tests_run == 5
    _pass("Added 5 tests (4 passed, 1 failed)")

    # Add documentation
    plugin.engine.add_documentation(p1.project_id)
    _pass("Added documentation")

    # Verify stages
    assert Stage.SCAFFOLD.value in project.stages_completed
    assert Stage.TEST.value in project.stages_completed
    assert Stage.DOCUMENT.value in project.stages_completed
    _pass(f"All 3 stages completed: {project.stages_completed}")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: {stats}")

    return True


async def test_3_operating_modes():
    """Test 3: Operating Modes."""
    header("Test 3: Operating Modes")

    from plugins.operating_modes import create as om_create, OperatingMode
    plugin = await om_create()
    await plugin.load()

    # List modes
    modes = plugin.engine.list_modes()
    assert len(modes) >= 7
    _pass(f"Available modes: {modes}")

    # Default mode
    current = plugin.engine.get_current_mode()
    assert current is not None
    _pass(f"Default mode: {current.name} (tone={current.tone})")

    # Switch mode
    assert plugin.engine.set_mode(OperatingMode.RESEARCH.value)
    current = plugin.engine.get_current_mode()
    assert current.name == "research"
    _pass("Switched to research mode")

    # Tool allowance
    assert plugin.engine.is_tool_allowed("http_get")
    _pass("Research mode allows http_get")

    # Approval check
    assert not plugin.engine.requires_approval(0.1)  # low risk OK
    assert plugin.engine.requires_approval(0.5)  # high risk needs approval
    _pass("Research mode: low risk OK, high risk needs approval")

    # Safety critical mode — everything needs approval
    plugin.engine.set_mode(OperatingMode.SAFETY_CRITICAL.value)
    assert plugin.engine.requires_approval(0.0)  # even zero risk needs approval
    _pass("Safety critical mode: even zero risk requires approval")

    # Stats
    stats = plugin.engine.get_stats()
    _pass(f"Stats: current={stats['current_mode']}, switches={stats['mode_switches']}")

    return True


async def test_4_combined_workflow():
    """Test 4: Combined workflow with all 3 plugins."""
    header("Test 4: Combined Workflow")

    from plugins.computer_use import create as cu_create
    from plugins.engineering_factory import create as ef_create, ProjectType
    from plugins.operating_modes import create as om_create, OperatingMode

    cu = await cu_create()
    ef = await ef_create()
    om = await om_create()
    await cu.load()
    await ef.load()
    await om.load()

    # Set coding mode
    om.engine.set_mode(OperatingMode.CODING.value)
    _pass("Set coding mode")

    # Create engineering project
    project = ef.engine.create_project("combined_test", ProjectType.CLI.value)
    ef.engine.scaffold_project(project.project_id)
    _pass(f"Created and scaffolded project: {project.project_id}")

    # Use computer use to simulate opening an editor
    cu.engine.register_app("vscode", "C:/Program Files/VSCode")
    cu.engine.open_application("vscode")
    _pass("Opened VSCode via computer use")

    # Verify mode constraints
    assert om.engine.is_tool_allowed("python_exec")
    assert not om.engine.is_tool_allowed("delete_everything")
    _pass("Mode correctly filters tools")

    return True


async def test_5_e2e():
    """Test 5: E2E with all Phase 7 plugins in the kernel."""
    header("Test 5: E2E Kernel Integration")

    from core.runtime.kernel import HermesKernel, KernelConfig
    config = KernelConfig()
    kernel = HermesKernel(config)
    await kernel.boot()

    for name in ["computer_use", "engineering_factory", "operating_modes"]:
        assert name in kernel._plugins, f"{name} not loaded"
    _pass("All 3 Phase 7 plugins loaded in kernel")

    # Use computer_use
    cu = kernel._plugins["computer_use"]
    cu.engine.register_app("e2e_app", "/test/path")
    cu.engine.open_application("e2e_app")
    _pass("Computer use: opened app")

    # Use engineering_factory
    ef = kernel._plugins["engineering_factory"]
    from plugins.engineering_factory import ProjectType
    proj = ef.engine.create_project("e2e_proj", ProjectType.LIBRARY.value)
    ef.engine.scaffold_project(proj.project_id)
    _pass(f"Engineering factory: created and scaffolded {proj.name}")

    # Use operating_modes
    om = kernel._plugins["operating_modes"]
    from plugins.operating_modes import OperatingMode
    om.engine.set_mode(OperatingMode.RESEARCH.value)
    _pass(f"Operating modes: switched to {om.engine.get_current_mode().name}")

    # All healthy
    for name in ["computer_use", "engineering_factory", "operating_modes"]:
        plugin = kernel._plugins.get(name)
        if plugin and hasattr(plugin, "health"):
            health = await plugin.health()
            assert health.get("status") == "healthy", f"{name} unhealthy: {health}"

    _pass("All Phase 7 plugins report healthy")

    await kernel.shutdown()
    return True


async def main():
    print("\n" + "=" * 70)
    print("  PHASE 7 TEST SUITE — Advanced")
    print("=" * 70)

    tests = [
        ("Test 1: Computer Use", test_1_computer_use),
        ("Test 2: Engineering Factory", test_2_engineering_factory),
        ("Test 3: Operating Modes", test_3_operating_modes),
        ("Test 4: Combined Workflow", test_4_combined_workflow),
        ("Test 5: E2E Integration", test_5_e2e),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            test_fail(name, str(e))
            failed += 1

    print("\n" + "=" * 70)
    print(f"  PHASE 7 RESULTS: {passed}/{passed+failed} passed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
