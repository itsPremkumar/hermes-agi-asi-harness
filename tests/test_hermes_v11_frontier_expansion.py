"""
HERMES ASI HARNESS — v11 FRONTIER EXPANSION TEST SUITE
======================================================
Tests all 5 architectural enhancements:
1. Developer Agency Tool Suite in ToolEnvironmentOS (write_file, edit_file, list_dir, grep_search, find_by_name, execute_shell, git operations).
2. Memory OS Long-Term Disk Persistence across all 7 non-volatile memory subsystems (.hermes/memory/ JSONL export/import/hydration).
3. Unified SDK/CLI Dual-Substrate Bridge (Harness.run(mode="dual_substrate") -> HermesIntelligenceOS & RuntimeRouter).
4. Empirical SWE-bench Benchmark Evaluation Engine (BenchmarkRunner.run_empirical_task, isolated git workspace, RealityVerificationEngine L5 proof, patch generation).
5. Live Dynamic MCP Server Hub & Capability Registry (connect_mcp_client, ToolDescriptor registration, CapabilityManifest reflection).
"""

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from hermes_agi import Harness, HermesIntelligenceOS
from hermes_agi.benchmarks.runner import BenchmarkRunner
from hermes_os.capabilities import CapabilityKind, CapabilityRegistry
from hermes_os.tool_env import ToolEnvironmentOS
from memory.manager import MemoryOS
from memory.subsystems import (
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
    FailureMemory,
    DecisionMemory,
    WorldStateMemory,
    CapabilityMemory,
)
from plugins.mcp_client import MCPClient


@pytest.fixture
def temp_workspace():
    tmp_dir = tempfile.mkdtemp(prefix="hermes_v11_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


# =====================================================================
# GAP 1: Developer Agency Tool Suite in ToolEnvironmentOS
# =====================================================================

@pytest.mark.asyncio
async def test_developer_agency_tools(temp_workspace):
    tool_env = ToolEnvironmentOS(workspace_root=temp_workspace)

    # 1. write_file
    res_write = await tool_env.execute_tool("write_file", {
        "path": "src/module.py",
        "content": "def calculate(x, y):\n    return x + y\n\ndef multiply(x, y):\n    return x * y\n",
    })
    assert res_write["success"] is True
    assert (Path(temp_workspace) / "src" / "module.py").exists()

    # 2. list_dir
    res_list = await tool_env.execute_tool("list_dir", {"path": "src"})
    assert res_list["success"] is True
    names = [item["name"] for item in res_list["result"]]
    assert "module.py" in names

    # 3. grep_search
    res_grep = await tool_env.execute_tool("grep_search", {"query": "multiply", "path": "src"})
    assert res_grep["success"] is True
    assert len(res_grep["result"]) > 0
    assert "multiply" in res_grep["result"][0]["line"]

    # 4. find_by_name
    res_find = await tool_env.execute_tool("find_by_name", {"pattern": "*.py", "path": "src"})
    assert res_find["success"] is True
    assert any("module.py" in p for p in res_find["result"])

    # 5. edit_file
    res_edit = await tool_env.execute_tool("edit_file", {
        "path": "src/module.py",
        "old_str": "return x * y",
        "new_str": "return x * y * 2",
    })
    assert res_edit["success"] is True
    new_content = (Path(temp_workspace) / "src" / "module.py").read_text(encoding="utf-8")
    assert "return x * y * 2" in new_content

    # 6. execute_shell
    res_shell = await tool_env.execute_tool("execute_shell", {
        "command": f'"{sys.executable}" -c "print(\'agency_shell_ok\')"',
    })
    assert res_shell["success"] is True
    assert res_shell["result"]["exit_code"] == 0
    assert "agency_shell_ok" in res_shell["result"]["stdout"]


# =====================================================================
# GAP 2: Memory OS Long-Term Disk Persistence
# =====================================================================

def test_memory_os_disk_persistence(temp_workspace):
    mem_os = MemoryOS(workspace_root=temp_workspace)

    # 1. Store records in all 7 non-volatile subsystems
    mem_os.semantic.store("Python async/await runtime semantics", tags=["python", "async"])
    mem_os.episodic.record(
        mission_id="m-v11-test",
        user_request="Deploy v11 frontier harness",
        plan_summary="Executed 5 architectural expansions",
        outcome={"status": "success"},
        earned_proof_hash="sha256:abc123v11",
    )
    mem_os.procedural.store_skill(
        name="surgical_refactor",
        trigger_context="Code requires targeted modification",
        preconditions=["File exists"],
        action_sequence=["grep_search", "edit_file", "verify_test_suite"],
        verification_method="oracle_check",
    )
    mem_os.failure.record_failure(
        error_type="SyntaxError",
        context={"file": "broken.py"},
        traceback_str="line 1: unexpected token",
        recovery_attempted="edit_file with correction",
        resolved=True,
    )
    mem_os.decision.record_decision(
        task_id="task-arch-v11",
        alternatives=["single_agent", "dual_substrate"],
        chosen="dual_substrate",
        rationale="LangGraph durable DAG combined with Deep Agents inner sandboxes",
    )
    mem_os.world_state.update_state("system_status", "operational", confidence=1.0)
    mem_os.capability.update_success_rate("tool.python_repl", success=True)

    # 2. Persist to disk
    persisted_counts = mem_os.save_to_disk()
    assert len(persisted_counts) >= 7
    for name, count in persisted_counts.items():
        fp = mem_os.storage_dir / f"{name}.jsonl"
        assert fp.exists()
        assert fp.stat().st_size > 0

    # 3. Create a brand new MemoryOS instance pointing to the same workspace
    new_mem_os = MemoryOS(workspace_root=temp_workspace)

    # Verify auto-hydration
    assert len(new_mem_os.semantic.search("Python")) > 0
    assert len(new_mem_os.episodic.get_recent(10)) == 1
    assert new_mem_os.episodic.get_recent(10)[0].mission_id == "m-v11-test"
    assert new_mem_os.procedural.get_skill("surgical_refactor") is not None
    assert len(new_mem_os.failure.get_failures(resolved_only=True)) == 1
    assert len(new_mem_os.decision.get_history()) == 1
    assert new_mem_os.decision.get_history()[0].chosen == "dual_substrate"
    assert new_mem_os.world_state.get_state("system_status") == "operational"
    assert new_mem_os.capability.get_metrics("tool.python_repl")["successes"] >= 1


# =====================================================================
# GAP 3: Unified SDK/CLI Dual-Substrate Bridge
# =====================================================================

@pytest.mark.asyncio
async def test_harness_dual_substrate_bridge(temp_workspace):
    harness = await Harness.create(use_real_plugins=False)

    # Test dual_substrate execution routing
    result = await harness.run(
        "Refactor matrix multiplication kernel and run verification",
        mode="dual_substrate",
        workspace_root=temp_workspace,
    )

    assert result["status"] == "completed"
    assert result["mode"] == "dual_substrate"
    assert "plan" in result
    assert "execution_result" in result
    exec_res = result["execution_result"]
    assert exec_res["success"] is True
    assert exec_res["runtime_used"] == "composite_dual_substrate"
    assert len(exec_res["waves_completed"]) > 0
    assert exec_res["proof_hash"] is not None
    assert len(exec_res["worker_sandboxes"]) > 0

    # Verify backward compatibility with mode="auto"
    auto_result = await harness.run("Generate simple project plan")
    assert auto_result["status"] == "completed"
    assert "plan" in auto_result
    await harness.shutdown()


# =====================================================================
# GAP 4: Empirical SWE-bench Benchmark Evaluation Engine
# =====================================================================

@pytest.mark.asyncio
async def test_empirical_swe_bench_task(temp_workspace):
    runner = BenchmarkRunner()

    task_spec = {
        "instance_id": "math__add-fix-01",
        "base_files": {
            "math_lib.py": "def add(a, b):\n    return a - b  # Buggy subtraction\n",
        },
        "solution_files": {
            "math_lib.py": "def add(a, b):\n    return a + b  # Correct addition\n",
        },
        "test_command": [
            sys.executable,
            "-c",
            "import math_lib; assert math_lib.add(2, 3) == 5, 'add(2, 3) must equal 5'",
        ],
        "timeout_s": 30.0,
    }

    result = await runner.run_empirical_task(task_spec, workspace_root=temp_workspace)

    assert result["instance_id"] == "math__add-fix-01"
    assert result["status"] == "resolved"
    assert result["passed"] is True
    assert result["accuracy"] == 1.0
    assert "return a + b" in result["patch"]
    assert result["verification_proof"]["tier"] == "L5"
    assert result["verification_proof"]["verified"] is True
    assert result["verification_proof"]["proof_hash"] != ""

    # Test suite evaluation
    suite_res = await runner.run_swe_bench_suite([task_spec], workspace_root=temp_workspace)
    assert suite_res["benchmark"] == "swe_bench"
    assert suite_res["status"] == "completed"
    assert suite_res["total_tasks"] == 1
    assert suite_res["resolved_count"] == 1
    assert suite_res["resolve_rate"] == 1.0


# =====================================================================
# GAP 5: Live Dynamic MCP Server Hub & Capability Registry
# =====================================================================

@pytest.mark.asyncio
async def test_dynamic_mcp_server_hub_and_registry(temp_workspace):
    cap_registry = CapabilityRegistry(workspace_root=temp_workspace)
    tool_env = ToolEnvironmentOS(workspace_root=temp_workspace)

    # 1. Verify developer agency tools are registered by default in CapabilityRegistry
    assert cap_registry.get("tool.write_file") is not None
    assert cap_registry.get("tool.edit_file") is not None
    assert cap_registry.get("tool.grep_search") is not None
    assert cap_registry.get("tool.execute_shell") is not None

    # 2. Setup MCPClient
    client = MCPClient()
    client.add_server("code_intel", "mock_server_cmd")
    conn = client.connect("code_intel")
    assert conn["connected"] is True

    # 3. Connect MCP client to ToolEnvironmentOS and propagate to CapabilityRegistry
    registered = tool_env.connect_mcp_client(client, "code_intel", capability_registry=cap_registry)
    assert len(registered) > 0
    assert "mcp_code_intel_example_tool" in registered

    # Verify tool exists in tool_env
    descriptor = tool_env.get_tool("mcp_code_intel_example_tool")
    assert descriptor is not None

    # Execute dynamic MCP tool
    exec_res = await tool_env.execute_tool("mcp_code_intel_example_tool", {"query": "AST"})
    assert exec_res["success"] is True
    assert exec_res["result"]["server"] == "code_intel"
    assert exec_res["result"]["tool"] == "example_tool"

    # Verify capability reflection in CapabilityRegistry
    mcp_cap = cap_registry.get("mcp.code_intel.example_tool")
    assert mcp_cap is not None
    assert mcp_cap.kind == CapabilityKind.MCP
    assert mcp_cap.name == "code_intel:example_tool"
