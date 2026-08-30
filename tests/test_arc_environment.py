"""Tests for ARC-AGI-3 Environment Connector."""
import pytest
from core.arc_agi_3.environment import (
    EnvironmentConnector, ConnectionStatus, ActionType, Action, Observation, Task
)


class TestEnvironmentConnector:
    def test_create(self):
        conn = EnvironmentConnector()
        assert conn.status == ConnectionStatus.DISCONNECTED

    def test_connect(self):
        conn = EnvironmentConnector()
        assert conn.connect() is True
        assert conn.status == ConnectionStatus.CONNECTED

    def test_disconnect(self):
        conn = EnvironmentConnector()
        conn.connect()
        conn.disconnect()
        assert conn.status == ConnectionStatus.DISCONNECTED

    def test_register_task(self):
        conn = EnvironmentConnector()
        task = Task("t1", "Test Task", "A test task")
        conn.register_task(task)
        assert conn.load_task("t1") is not None

    def test_get_current_task(self):
        conn = EnvironmentConnector()
        task = Task("t1", "Test Task", "A test task")
        conn.register_task(task)
        conn.load_task("t1")
        assert conn.get_current_task() is not None

    def test_get_observation(self):
        conn = EnvironmentConnector()
        task = Task("t1", "Test", "Desc", test_grids=[[[1, 2], [3, 4]]])
        conn.register_task(task)
        conn.load_task("t1")
        obs = conn.get_observation()
        assert obs is not None
        assert obs.grid == [[1, 2], [3, 4]]

    def test_take_action(self):
        conn = EnvironmentConnector()
        task = Task("t1", "Test", "Desc")
        conn.register_task(task)
        conn.load_task("t1")
        action = Action("a1", ActionType.MOVE)
        obs = conn.take_action(action)
        assert obs is not None

    def test_submit(self):
        conn = EnvironmentConnector()
        task = Task("t1", "Test", "Desc")
        conn.register_task(task)
        conn.load_task("t1")
        result = conn.submit([[1, 2], [3, 4]])
        assert "correct" in result
        assert "score" in result

    def test_get_available_tasks(self):
        conn = EnvironmentConnector()
        conn.register_task(Task("t1", "A", "Desc"))
        conn.register_task(Task("t2", "B", "Desc"))
        assert len(conn.get_available_tasks()) == 2

    def test_get_state(self):
        conn = EnvironmentConnector()
        conn.connect()
        state = conn.get_state()
        assert state["status"] == "connected"
        assert state["tasks_loaded"] == 0
