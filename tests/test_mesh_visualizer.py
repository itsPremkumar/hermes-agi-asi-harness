"""Tests for MeshVisualizer."""
from mesh.mesh_visualizer import MeshVisualizer


class TestMeshVisualizer:
    def test_create(self):
        mv = MeshVisualizer()
        assert mv.count_nodes() == 0
        assert mv.count_edges() == 0

    def test_add_node(self):
        mv = MeshVisualizer()
        node = mv.add_node("node1", x=10.0, y=20.0)
        assert node.label == "node1"
        assert node.x == 10.0
        assert node.y == 20.0
        assert mv.count_nodes() == 1

    def test_add_edge(self):
        mv = MeshVisualizer()
        n1 = mv.add_node("node1")
        n2 = mv.add_node("node2")
        edge = mv.add_edge(n1.id, n2.id, weight=2.0)
        assert edge.source == n1.id
        assert edge.target == n2.id
        assert edge.weight == 2.0
        assert mv.count_edges() == 1

    def test_list_nodes(self):
        mv = MeshVisualizer()
        mv.add_node("a")
        mv.add_node("b")
        assert len(mv.list_nodes()) == 2

    def test_list_edges(self):
        mv = MeshVisualizer()
        n1 = mv.add_node("a")
        n2 = mv.add_node("b")
        mv.add_edge(n1.id, n2.id)
        assert len(mv.list_edges()) == 1

    def test_layout_circular(self):
        mv = MeshVisualizer()
        mv.add_node("a")
        mv.add_node("b")
        mv.add_node("c")
        mv.layout_circular(radius=100.0)
        nodes = mv.list_nodes()
        assert all(n.x != 0 or n.y != 0 for n in nodes)

    def test_layout_grid(self):
        mv = MeshVisualizer()
        mv.add_node("a")
        mv.add_node("b")
        mv.add_node("c")
        mv.layout_grid(spacing=50.0)
        nodes = mv.list_nodes()
        assert all(n.x >= 0 and n.y >= 0 for n in nodes)

    def test_clear(self):
        mv = MeshVisualizer()
        mv.add_node("a")
        mv.add_node("b")
        mv.clear()
        assert mv.count_nodes() == 0
        assert mv.count_edges() == 0
