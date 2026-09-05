"""Tests for graph.py — LangGraph State Graph."""

from __future__ import annotations

import pytest

from src.harness.errors import GraphError, NodeError
from src.harness.graph import (
    Edge,
    Graph,
    Node,
    State,
    create_avopisaging_graph,
)


class TestState:
    """Tests for State class."""

    def test_state_creation(self):
        state = State()
        assert state.data == {}
        assert state.errors == []
        assert state.step == 0

    def test_state_get_set(self):
        state = State()
        state.set("key", "value")
        assert state.get("key") == "value"

    def test_state_get_default(self):
        state = State()
        assert state.get("missing", "default") == "default"

    def test_state_update(self):
        state = State()
        state.update({"a": 1, "b": 2})
        assert state.get("a") == 1
        assert state.get("b") == 2

    def test_state_add_error(self):
        state = State()
        state.add_error("node1", "something failed")
        assert len(state.errors) == 1
        assert state.errors[0]["node_id"] == "node1"

    def test_state_fork(self):
        state = State()
        state.set("key", "value")
        forked = state.fork()
        assert forked.get("key") == "value"
        forked.set("key", "changed")
        assert state.get("key") == "value"

    def test_state_metadata(self):
        state = State(metadata={"run_id": "abc"})
        assert state.metadata["run_id"] == "abc"


class TestNode:
    """Tests for Node class."""

    def test_node_creation(self):
        node = Node(id="n1", func=lambda s: s)
        assert node.id == "n1"
        assert node.max_retries == 3

    def test_node_execute_success(self):
        node = Node(id="n1", func=lambda s: s.set("done", True) or s)
        state = State()
        result = node.execute(state)
        assert result.get("done") is True

    def test_node_execute_failure(self):
        def fail(state):
            raise ValueError("fail")
        node = Node(id="n1", func=fail, max_retries=1)
        with pytest.raises(NodeError):
            node.execute(State())

    def test_node_retry_count(self):
        attempts = [0]
        def flaky(state):
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("not yet")
            return state
        node = Node(id="n1", func=flaky, max_retries=2)
        node.execute(State())
        assert node.retry_count == 1


class TestEdge:
    """Tests for Edge class."""

    def test_edge_creation(self):
        edge = Edge(source="a", target="b")
        assert edge.source == "a"
        assert edge.target == "b"

    def test_edge_resolve_unconditional(self):
        edge = Edge(source="a", target="b")
        assert edge.resolve(State()) == "b"

    def test_edge_resolve_conditional_true(self):
        edge = Edge(source="a", target="b", condition=lambda s: "b")
        assert edge.resolve(State()) == "b"

    def test_edge_resolve_conditional_false(self):
        edge = Edge(source="a", target="b", condition=lambda s: None)
        assert edge.resolve(State()) is None


class TestGraph:
    """Tests for Graph class."""

    def test_graph_creation(self):
        g = Graph(name="test")
        assert g.name == "test"
        assert g.entry_point is None

    def test_add_node(self):
        g = Graph()
        g.add_node("n1", lambda s: s)
        assert "n1" in g.nodes
        assert g.entry_point == "n1"

    def test_add_edge(self):
        g = Graph()
        g.add_node("n1", lambda s: s)
        g.add_node("n2", lambda s: s)
        g.add_edge("n1", "n2")
        assert len(g.edges) == 1

    def test_set_entry_point(self):
        g = Graph()
        g.add_node("n1", lambda s: s)
        g.add_node("n2", lambda s: s)
        g.set_entry_point("n2")
        assert g.entry_point == "n2"

    def test_set_entry_point_invalid(self):
        g = Graph()
        with pytest.raises(GraphError):
            g.set_entry_point("missing")

    def test_execute_simple(self):
        g = Graph()
        g.add_node("n1", lambda s: s.set("step1", True) or s)
        g.add_node("n2", lambda s: s.set("step2", True) or s)
        g.add_edge("n1", "n2")
        g.add_edge("n2", "__end__")
        result = g.execute()
        assert result.get("step1") is True
        assert result.get("step2") is True

    def test_execute_with_initial_state(self):
        g = Graph()
        g.add_node("n1", lambda s: s.set("value", s.get("value", 0) + 1) or s)
        g.add_edge("n1", "__end__")
        state = State()
        state.set("value", 5)
        result = g.execute(state)
        assert result.get("value") == 6

    def test_execute_conditional_branch(self):
        g = Graph()
        g.add_node("start", lambda s: s)
        g.add_node("branch_a", lambda s: s.set("branch", "a") or s)
        g.add_node("branch_b", lambda s: s.set("branch", "b") or s)
        g.add_edge("start", "branch_a", condition=lambda s: "branch_a")
        g.add_edge("start", "branch_b", condition=lambda s: "branch_b")
        g.add_edge("branch_a", "__end__")
        g.add_edge("branch_b", "__end__")
        result = g.execute()
        assert result.get("branch") == "a"

    def test_execute_no_entry_point(self):
        g = Graph()
        with pytest.raises(GraphError):
            g.execute()

    def test_get_outgoing(self):
        g = Graph()
        g.add_node("n1", lambda s: s)
        g.add_node("n2", lambda s: s)
        g.add_node("n3", lambda s: s)
        g.add_edge("n1", "n2")
        g.add_edge("n1", "n3")
        outgoing = g.get_outgoing("n1")
        assert len(outgoing) == 2

    def test_dead_letter_queue(self):
        g = Graph()
        g.add_node("n1", lambda s: (_ for _ in ()).throw(ValueError("fail")))
        g.add_edge("n1", "__end__")
        with pytest.raises(GraphError):
            g.execute()
        assert g.dead_letter_queue.size == 1

    def test_circuit_breaker_property(self):
        g = Graph()
        assert g.circuit_breaker is not None


class TestAVOPISAgingGraph:
    """Tests for the AVOPISAging workflow graph."""

    def test_create_graph(self):
        g = create_avopisaging_graph()
        assert g.name == "avopisaging"
        assert len(g.nodes) == 6

    def test_graph_has_cycle(self):
        g = create_avopisaging_graph()
        assess_out = g.get_outgoing("iterate")
        assert any(e.target == "assess" for e in assess_out)

    def test_graph_execution(self):
        g = create_avopisaging_graph()
        result = g.execute()
        assert result.get("assessment") is not None
        assert result.get("iteration_count", 0) >= 1

    def test_graph_entry_point(self):
        g = create_avopisaging_graph()
        assert g.entry_point == "assess"
