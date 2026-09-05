"""
Unit tests for Hermes Core Async RLM Engine (Prime Agent parity):
- Top-level await in REPL execution
- Recursive subagent spawning (`await rlm.run()`)
- Parallel fan-out via `asyncio.gather()`
- Heap memory snapshots and restoration
"""

from __future__ import annotations

from hermes_agi.rlm import RLMREPLExecutor, RLMSpawnHandle


class TestAsyncRLMCore:
    """Test the asynchronous RLM REPL engine."""

    def test_top_level_await(self):
        repl = RLMREPLExecutor()
        try:
            code = "await asyncio.sleep(0.01)\nx = 100\nx * 2"
            res = repl.execute(code)
            assert res.success is True
            assert res.returned_value == 200
            assert repl.get_variable("x") == 100
        finally:
            repl.close()

    def test_recursive_subagent_spawning(self):
        repl = RLMREPLExecutor()
        try:
            code = (
                "child = await rlm.run('inspect cache latency', role='researcher')\n"
                "print('Spawned name:', child.name)\n"
                "child.status\n"
            )
            res = repl.execute(code)
            assert res.success is True
            assert res.returned_value == "completed"
            assert "Spawned name:" in res.stdout
            child = repl.get_variable("child")
            assert isinstance(child, RLMSpawnHandle)
        finally:
            repl.close()

    def test_parallel_subagent_gather(self):
        repl = RLMREPLExecutor()
        try:
            code = (
                "t1 = rlm.run('subtask 1', role='coder')\n"
                "t2 = rlm.run('subtask 2', role='coder')\n"
                "c1, c2 = await asyncio.gather(t1, t2)\n"
                "[c1.status, c2.status]\n"
            )
            res = repl.execute(code)
            assert res.success is True
            assert res.returned_value == ["completed", "completed"]
        finally:
            repl.close()

    def test_heap_snapshot_and_restore(self, tmp_path):
        repl = RLMREPLExecutor(workspace_root=str(tmp_path))
        try:
            repl.execute("large_matrix = [[i * j for j in range(5)] for i in range(5)]")
            assert repl.get_variable("large_matrix") is not None

            # Snapshot
            snap_path = repl.snapshot_memory("test_heap")
            assert snap_path is not None

            # Create fresh REPL and restore
            repl2 = RLMREPLExecutor(workspace_root=str(tmp_path))
            try:
                restored = repl2.restore_memory("test_heap")
                assert restored is True
                assert repl2.get_variable("large_matrix") == repl.get_variable("large_matrix")
            finally:
                repl2.close()
        finally:
            repl.close()
