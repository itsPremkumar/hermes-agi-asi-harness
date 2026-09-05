"""Tests for NodeManager."""
from mesh import NodeManager, NodeStatus


class TestNodeManager:
    def test_create(self):
        nm = NodeManager()
        assert nm.count() == 0

    def test_register(self):
        nm = NodeManager()
        node = nm.register("node1", "http://localhost:8001", capacity=4)
        assert node.name == "node1"
        assert node.address == "http://localhost:8001"
        assert node.capacity == 4
        assert nm.count() == 1

    def test_unregister(self):
        nm = NodeManager()
        node = nm.register("node1", "http://localhost:8001")
        assert nm.unregister(node.id) is True
        assert nm.count() == 0

    def test_get(self):
        nm = NodeManager()
        node = nm.register("node1", "http://localhost:8001")
        result = nm.get(node.id)
        assert result is not None
        assert result.name == "node1"

    def test_set_status(self):
        nm = NodeManager()
        node = nm.register("node1", "http://localhost:8001")
        assert nm.set_status(node.id, NodeStatus.ONLINE) is True
        assert nm.get(node.id).status == NodeStatus.ONLINE

    def test_assign_task(self):
        nm = NodeManager()
        node = nm.register("node1", "http://localhost:8001", capacity=2)
        assert nm.assign_task(node.id) is True
        assert nm.get(node.id).load == 1

    def test_assign_task_over_capacity(self):
        nm = NodeManager()
        node = nm.register("node1", "http://localhost:8001", capacity=1)
        nm.assign_task(node.id)
        assert nm.assign_task(node.id) is False

    def test_list_online(self):
        nm = NodeManager()
        n1 = nm.register("node1", "http://localhost:8001")
        n2 = nm.register("node2", "http://localhost:8002")
        nm.set_status(n1.id, NodeStatus.ONLINE)
        online = nm.list_online()
        assert len(online) == 1
