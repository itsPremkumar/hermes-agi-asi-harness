"""Tests for Operations Workstream — Watchdog, Scheduler, Checkpointing, Economic Ledger."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from operations import (
    AgentStatus,
    Checkpoint,
    CheckpointManager,
    EconomicEntry,
    EconomicLedger,
    Scheduler,
    Watchdog,
)


class TestWatchdog(unittest.TestCase):
    def setUp(self):
        self.watchdog = Watchdog(heartbeat_timeout=1.0, max_restarts=3)

    def test_register_agent(self):
        self.watchdog.register("agent-1", pid=1234)
        health = self.watchdog.check_health()
        self.assertEqual(len(health), 0)

    def test_heartbeat_updates_timestamp(self):
        self.watchdog.register("agent-1")
        time.sleep(0.1)
        self.watchdog.heartbeat("agent-1", memory_mb=100.0)
        health = self.watchdog.check_health()
        self.assertEqual(len(health), 0)

    def test_stalled_detection(self):
        self.watchdog.register("agent-1")
        time.sleep(1.5)
        stalled = self.watchdog.check_health()
        self.assertEqual(len(stalled), 1)
        self.assertEqual(stalled[0].status, AgentStatus.STALLED)

    def test_should_restart_under_limit(self):
        self.watchdog.register("agent-1")
        self.assertTrue(self.watchdog.should_restart("agent-1"))

    def test_restart_resets_status(self):
        self.watchdog.register("agent-1")
        time.sleep(1.5)
        self.watchdog.check_health()
        result = self.watchdog.restart("agent-1")
        self.assertTrue(result)
        self.assertEqual(self.watchdog._agents["agent-1"].status, AgentStatus.RUNNING)

    def test_restart_limit_enforced(self):
        self.watchdog.register("agent-1")
        for _ in range(3):
            time.sleep(0.1)
            self.watchdog.restart("agent-1")
        self.assertFalse(self.watchdog.should_restart("agent-1"))

    def test_multiple_agents(self):
        for i in range(5):
            self.watchdog.register(f"agent-{i}")
        self.assertEqual(len(self.watchdog._agents), 5)

    def test_heartbeat_with_metrics(self):
        self.watchdog.register("agent-1")
        self.watchdog.heartbeat("agent-1", memory_mb=256.5, cpu_percent=45.0, task_count=3)
        agent = self.watchdog._agents["agent-1"]
        self.assertEqual(agent.memory_mb, 256.5)
        self.assertEqual(agent.cpu_percent, 45.0)
        self.assertEqual(agent.task_count, 3)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler(max_concurrent=3)

    def test_submit_and_get(self):
        asyncio.run(self.scheduler.submit("task-1", priority=1))
        result = asyncio.run(self.scheduler.get_next())
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "task-1")

    def test_priority_ordering(self):
        asyncio.run(self.scheduler.submit("low", priority=10))
        asyncio.run(self.scheduler.submit("high", priority=1))
        asyncio.run(self.scheduler.submit("medium", priority=5))
        first = asyncio.run(self.scheduler.get_next())
        second = asyncio.run(self.scheduler.get_next())
        third = asyncio.run(self.scheduler.get_next())
        self.assertEqual(first[0], "high")
        self.assertEqual(second[0], "medium")
        self.assertEqual(third[0], "low")

    def test_concurrency_limit(self):
        for i in range(5):
            asyncio.run(self.scheduler.submit(f"task-{i}"))
        # Should only get 3 (max_concurrent)
        results = []
        for _ in range(5):
            result = asyncio.run(self.scheduler.get_next())
            if result:
                results.append(result)
        self.assertEqual(len(results), 3)

    def test_complete_frees_slot(self):
        asyncio.run(self.scheduler.submit("task-1"))
        asyncio.run(self.scheduler.get_next())
        self.scheduler.complete("task-1")
        self.assertEqual(self.scheduler.running_count, 0)

    def test_queue_size(self):
        for i in range(5):
            asyncio.run(self.scheduler.submit(f"task-{i}"))
        # None running yet, so queue should have 5
        self.assertEqual(self.scheduler.queue_size, 5)

    def test_empty_queue_returns_none(self):
        result = asyncio.run(self.scheduler.get_next())
        self.assertIsNone(result)


class TestCheckpointManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CheckpointManager(self.temp_dir)

    def test_save_and_load(self):
        checkpoint = Checkpoint(
            checkpoint_id="cp-1",
            agent_id="agent-1",
            state={"progress": 50},
            timestamp=time.time(),
        )
        self.manager.save(checkpoint)
        loaded = self.manager.load("agent-1", "cp-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.state["progress"], 50)

    def test_load_nonexistent(self):
        result = self.manager.load("agent-1", "nonexistent")
        self.assertIsNone(result)

    def test_latest_checkpoint(self):
        for i in range(3):
            cp = Checkpoint(
                checkpoint_id=f"cp-{i}",
                agent_id="agent-1",
                state={"progress": i * 10},
                timestamp=time.time() + i,
            )
            self.manager.save(cp)
        latest = self.manager.latest("agent-1")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.checkpoint_id, "cp-2")

    def test_list_checkpoints(self):
        for i in range(3):
            self.manager.save(Checkpoint(
                checkpoint_id=f"cp-{i}",
                agent_id="agent-1",
                state={},
                timestamp=time.time(),
            ))
        cps = self.manager.list_checkpoints("agent-1")
        self.assertEqual(len(cps), 3)

    def test_list_all_checkpoints(self):
        for agent in ["agent-1", "agent-2"]:
            self.manager.save(Checkpoint(
                checkpoint_id="cp-1",
                agent_id=agent,
                state={},
                timestamp=time.time(),
            ))
        cps = self.manager.list_checkpoints()
        self.assertEqual(len(cps), 2)

    def test_checkpoint_with_metadata(self):
        cp = Checkpoint(
            checkpoint_id="cp-1",
            agent_id="agent-1",
            state={},
            timestamp=time.time(),
            metadata={"reason": "test"},
        )
        self.manager.save(cp)
        loaded = self.manager.load("agent-1", "cp-1")
        self.assertEqual(loaded.metadata["reason"], "test")


class TestEconomicLedger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ledger_path = os.path.join(self.temp_dir, "ledger.jsonl")
        self.ledger = EconomicLedger(self.ledger_path)

    def test_record_entry(self):
        entry = EconomicEntry(
            timestamp=time.time(),
            agent_id="agent-1",
            action="task_complete",
            cost=0.50,
            value=2.00,
            task_id="task-1",
        )
        self.ledger.record(entry)
        self.assertEqual(len(self.ledger._entries), 1)

    def test_total_cost(self):
        for i in range(3):
            self.ledger.record(EconomicEntry(
                timestamp=time.time(),
                agent_id="agent-1",
                action="task",
                cost=1.0,
                value=0.0,
                task_id=f"task-{i}",
            ))
        self.assertEqual(self.ledger.total_cost(), 3.0)

    def test_total_value(self):
        for i in range(3):
            self.ledger.record(EconomicEntry(
                timestamp=time.time(),
                agent_id="agent-1",
                action="task",
                cost=0.0,
                value=5.0,
                task_id=f"task-{i}",
            ))
        self.assertEqual(self.ledger.total_value(), 15.0)

    def test_roi_calculation(self):
        self.ledger.record(EconomicEntry(
            timestamp=time.time(),
            agent_id="agent-1",
            action="task",
            cost=1.0,
            value=3.0,
            task_id="task-1",
        ))
        self.assertEqual(self.ledger.roi(), 2.0)

    def test_roi_zero_cost(self):
        self.ledger.record(EconomicEntry(
            timestamp=time.time(),
            agent_id="agent-1",
            action="task",
            cost=0.0,
            value=5.0,
            task_id="task-1",
        ))
        self.assertEqual(self.ledger.roi(), 0.0)

    def test_filter_by_agent(self):
        for agent in ["agent-1", "agent-2"]:
            self.ledger.record(EconomicEntry(
                timestamp=time.time(),
                agent_id=agent,
                action="task",
                cost=1.0,
                value=2.0,
                task_id="task-1",
            ))
        self.assertEqual(self.ledger.total_cost("agent-1"), 1.0)
        self.assertEqual(self.ledger.total_value("agent-2"), 2.0)

    def test_summary(self):
        self.ledger.record(EconomicEntry(
            timestamp=time.time(),
            agent_id="agent-1",
            action="task",
            cost=1.0,
            value=3.0,
            task_id="task-1",
        ))
        summary = self.ledger.summary()
        self.assertEqual(summary["total_entries"], 1)
        self.assertEqual(summary["total_cost"], 1.0)
        self.assertEqual(summary["roi"], 2.0)

    def test_persistence(self):
        self.ledger.record(EconomicEntry(
            timestamp=time.time(),
            agent_id="agent-1",
            action="task",
            cost=1.0,
            value=2.0,
            task_id="task-1",
        ))
        # Create new ledger pointing to same file
        new_ledger = EconomicLedger(self.ledger_path)
        self.assertEqual(len(new_ledger._entries), 1)

    def test_empty_ledger(self):
        self.assertEqual(self.ledger.total_cost(), 0.0)
        self.assertEqual(self.ledger.total_value(), 0.0)
        self.assertEqual(self.ledger.roi(), 0.0)


class TestIntegration(unittest.TestCase):
    """Integration tests across operations modules."""

    def test_watchdog_with_checkpoints(self):
        """Watchdog detects stall, checkpoint saved, agent restarted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(heartbeat_timeout=0.5, max_restarts=3)
            checkpoint_mgr = CheckpointManager(tmpdir)

            watchdog.register("agent-1", pid=1234)
            checkpoint_mgr.save(Checkpoint(
                checkpoint_id="before-stall",
                agent_id="agent-1",
                state={"progress": 50},
                timestamp=time.time(),
            ))

            time.sleep(0.6)
            stalled = watchdog.check_health()
            self.assertEqual(len(stalled), 1)

            watchdog.restart("agent-1")
            self.assertEqual(watchdog._agents["agent-1"].status, AgentStatus.RUNNING)

    def test_scheduler_with_economics(self):
        """Scheduler dispatches tasks, ledger tracks cost."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(max_concurrent=2)
            ledger = EconomicLedger(os.path.join(tmpdir, "ledger.jsonl"))

            asyncio.run(scheduler.submit("task-1", priority=1))
            result = asyncio.run(scheduler.get_next())
            self.assertIsNotNone(result)

            ledger.record(EconomicEntry(
                timestamp=time.time(),
                agent_id="agent-1",
                action="dispatch",
                cost=0.10,
                value=1.00,
                task_id=result[0],
            ))
            self.assertEqual(ledger.total_cost(), 0.10)

    def test_full_workflow(self):
        """Complete workflow: schedule → dispatch → checkpoint → complete → ledger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(max_concurrent=3)
            checkpoint_mgr = CheckpointManager(tmpdir)
            ledger = EconomicLedger(os.path.join(tmpdir, "ledger.jsonl"))
            watchdog = Watchdog()

            # Register agent
            watchdog.register("agent-1")

            # Submit task
            asyncio.run(scheduler.submit("task-1", priority=1, payload={"type": "research"}))
            result = asyncio.run(scheduler.get_next())
            self.assertIsNotNone(result)

            # Save checkpoint
            checkpoint_mgr.save(Checkpoint(
                checkpoint_id="start",
                agent_id="agent-1",
                state={"task": "task-1", "progress": 0},
                timestamp=time.time(),
            ))

            # Complete task
            scheduler.complete("task-1")
            ledger.record(EconomicEntry(
                timestamp=time.time(),
                agent_id="agent-1",
                action="complete",
                cost=0.50,
                value=2.00,
                task_id="task-1",
            ))

            self.assertEqual(scheduler.running_count, 0)
            self.assertEqual(ledger.total_value(), 2.00)


if __name__ == "__main__":
    unittest.main()
