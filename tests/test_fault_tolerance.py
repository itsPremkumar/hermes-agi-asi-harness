"""Tests for FaultTolerance."""
from mesh.fault_tolerance import FailureType, FaultTolerance, RecoveryAction


class TestFaultTolerance:
    def test_create(self):
        ft = FaultTolerance()
        assert ft.count() == 0

    def test_detect(self):
        ft = FaultTolerance()
        event = ft.detect("node1", FailureType.NODE_DOWN)
        assert event.node_id == "node1"
        assert event.failure_type == FailureType.NODE_DOWN
        assert event.resolved is False
        assert ft.count() == 1

    def test_resolve(self):
        ft = FaultTolerance()
        event = ft.detect("node1", FailureType.NODE_DOWN)
        assert ft.resolve(event.id, RecoveryAction.RESTART) is True
        assert ft.get_failures()[0].resolved is True
        assert ft.get_failures()[0].recovery_action == RecoveryAction.RESTART

    def test_set_strategy(self):
        ft = FaultTolerance()
        ft.set_strategy(FailureType.NODE_DOWN, RecoveryAction.MIGRATE)
        assert ft.get_strategy(FailureType.NODE_DOWN) == RecoveryAction.MIGRATE

    def test_get_failures(self):
        ft = FaultTolerance()
        ft.detect("node1", FailureType.NODE_DOWN)
        ft.detect("node2", FailureType.TIMEOUT)
        failures = ft.get_failures("node1")
        assert len(failures) == 1

    def test_get_unresolved(self):
        ft = FaultTolerance()
        event = ft.detect("node1", FailureType.NODE_DOWN)
        ft.detect("node2", FailureType.TIMEOUT)
        ft.resolve(event.id, RecoveryAction.RESTART)
        unresolved = ft.get_unresolved()
        assert len(unresolved) == 1
