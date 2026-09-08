"""Tests for StateGraphEngine."""
import pytest

from src.harness.runtime.state_graph import (
    StateGraphEngine,
    GraphState,
    Node,
    Edge,
    NodeState,
)


class TestStateGraphEngine:
    def test_init(self):
        sge = StateGraphEngine("test")
        assert sge.name == "test"
        assert sge.node_count == 0
        assert sge.edge_count == 0

    def test_add_node(self):
        sge = StateGraphEngine()
        node = sge.add_node("n1", lambda s: s)
        assert sge.node_count == 1
        assert node.name == "n1"

    def test_add_node_with_options(self):
        sge = StateGraphEngine()
        node = sge.add_node("n1", lambda s: s, description="test", retries=3)
        assert node.description == "test"
        assert node.retries == 3

    def test_add_edge(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        edge = sge.add_edge("n1", "n2")
        assert sge.edge_count == 1
        assert edge.source == "n1"
        assert edge.target == "n2"

    def test_add_edge_missing_source(self):
        sge = StateGraphEngine()
        sge.add_node("n2", lambda s: s)
        with pytest.raises(ValueError):
            sge.add_edge("missing", "n2")

    def test_add_edge_missing_target(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        with pytest.raises(ValueError):
            sge.add_edge("n1", "missing")

    def test_add_conditional_edge(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        edge = sge.add_edge("n1", "n2", condition=lambda s: s.get("go") == True)
        assert edge.is_conditional is True

    def test_set_entry_point(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.set_entry_point("n1")
        assert sge._entry_point == "n1"

    def test_set_entry_point_missing(self):
        sge = StateGraphEngine()
        with pytest.raises(ValueError):
            sge.set_entry_point("missing")

    def test_add_exit_point(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_exit_point("n1")
        assert "n1" in sge._exit_points

    def test_add_exit_point_missing(self):
        sge = StateGraphEngine()
        with pytest.raises(ValueError):
            sge.add_exit_point("missing")

    def test_get_node(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        node = sge.get_node("n1")
        assert node is not None
        assert node.name == "n1"

    def test_get_node_missing(self):
        sge = StateGraphEngine()
        assert sge.get_node("missing") is None

    def test_get_edges_from(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.add_node("n3", lambda s: s)
        sge.add_edge("n1", "n2")
        sge.add_edge("n1", "n3")
        edges = sge.get_edges_from("n1")
        assert len(edges) == 2

    def test_get_edges_to(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.add_node("n3", lambda s: s)
        sge.add_edge("n1", "n3")
        sge.add_edge("n2", "n3")
        edges = sge.get_edges_to("n3")
        assert len(edges) == 2

    def test_validate_empty(self):
        sge = StateGraphEngine()
        is_valid, errors = sge.validate()
        assert is_valid is False
        assert "Graph has no nodes" in errors

    def test_validate_no_entry(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        is_valid, errors = sge.validate()
        assert is_valid is False
        assert "No entry point set" in errors

    def test_validate_valid(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.set_entry_point("n1")
        is_valid, errors = sge.validate()
        assert is_valid is True

    def test_validate_disconnected(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.set_entry_point("n1")
        is_valid, errors = sge.validate()
        assert is_valid is False
        assert any("Disconnected" in e for e in errors)

    def test_validate_cycle(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.add_edge("n1", "n2")
        sge.add_edge("n2", "n1")
        sge.set_entry_point("n1")
        is_valid, errors = sge.validate()
        assert is_valid is False
        assert any("cycles" in e for e in errors)

    def test_execute_simple(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.set_entry_point("n1")
        result = sge.execute()
        assert result.success is True
        assert "n1" in result.node_order

    def test_execute_with_initial_state(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.set_entry_point("n1")
        result = sge.execute({"key": "value"})
        assert result.final_state.get("key") == "value"

    def test_execute_linear_chain(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.add_edge("n1", "n2")
        sge.set_entry_point("n1")
        result = sge.execute()
        assert result.success is True
        assert result.node_order == ["n1", "n2"]

    def test_execute_with_transform(self):
        def transform(s: GraphState):
            s.set("transformed", True)
            return s
        sge = StateGraphEngine()
        sge.add_node("n1", transform)
        sge.set_entry_point("n1")
        result = sge.execute()
        assert result.final_state.get("transformed") is True

    def test_execute_conditional_branch(self):
        sge = StateGraphEngine()
        sge.add_node("start", lambda s: s)
        sge.add_node("branch_a", lambda s: s)
        sge.add_node("branch_b", lambda s: s)
        sge.add_edge("start", "branch_a", condition=lambda s: s.get("a") == True)
        sge.add_edge("start", "branch_b", condition=lambda s: s.get("a") != True)
        sge.set_entry_point("start")
        result = sge.execute({"a": True})
        assert "branch_a" in result.node_order
        assert "branch_b" not in result.node_order

    def test_execute_node_failure(self):
        def fail(s: GraphState):
            raise RuntimeError("fail!")
        sge = StateGraphEngine()
        sge.add_node("n1", fail)
        sge.set_entry_point("n1")
        result = sge.execute()
        assert result.success is True  # Graph completes but node fails
        assert "n1" in result.errors

    def test_execute_with_retry(self):
        attempts = []
        def flaky(s: GraphState):
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("not yet")
            return s
        sge = StateGraphEngine()
        sge.add_node("n1", flaky, retries=2, retry_delay=0.01)
        sge.set_entry_point("n1")
        result = sge.execute()
        assert result.success is True
        assert len(attempts) == 2

    def test_execute_invalid_graph(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        # No entry point
        result = sge.execute()
        assert result.success is False

    def test_execution_count(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.set_entry_point("n1")
        sge.execute()
        sge.execute()
        assert sge.get_execution_count() == 2

    def test_reset(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.set_entry_point("n1")
        sge.execute()
        sge.reset()
        assert sge.get_execution_count() == 0

    def test_remove_node(self):
        sge = StateGraphEngine()
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.add_edge("n1", "n2")
        assert sge.remove_node("n1") is True
        assert sge.node_count == 1
        assert sge.edge_count == 0

    def test_remove_node_missing(self):
        sge = StateGraphEngine()
        assert sge.remove_node("missing") is False

    def test_to_dict(self):
        sge = StateGraphEngine("mygraph")
        sge.add_node("n1", lambda s: s)
        sge.add_node("n2", lambda s: s)
        sge.add_edge("n1", "n2")
        sge.set_entry_point("n1")
        d = sge.to_dict()
        assert d["name"] == "mygraph"
        assert "n1" in d["nodes"]
        assert len(d["edges"]) == 1

    def test_graph_state_get_set(self):
        s = GraphState()
        s.set("key", "value")
        assert s.get("key") == "value"

    def test_graph_state_default(self):
        s = GraphState()
        assert s.get("missing", "default") == "default"

    def test_graph_state_update(self):
        s = GraphState()
        s.update({"a": 1, "b": 2})
        assert s.get("a") == 1
        assert s.get("b") == 2

    def test_graph_state_to_dict(self):
        s = GraphState()
        s.set("key", "value")
        assert s.to_dict() == {"key": "value"}

    def test_node_post_init_empty_name(self):
        with pytest.raises(ValueError):
            Node(name="", func=lambda s: s)

    def test_node_post_init_non_callable(self):
        with pytest.raises(ValueError):
            Node(name="n1", func="not_callable")

    def test_edge_is_conditional(self):
        e1 = Edge("a", "b")
        e2 = Edge("a", "b", condition=lambda s: True)
        assert e1.is_conditional is False
        assert e2.is_conditional is True
