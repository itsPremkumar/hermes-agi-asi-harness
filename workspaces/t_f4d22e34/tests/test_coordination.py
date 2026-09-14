"""Tests for agent coordination protocols."""

from __future__ import annotations

import pytest
import networkx as nx

from kg import create_empty_graph, KGNode, Vertical, NodeType
from kg.coordination import (
    AgentRole,
    AgentCapability,
    CoordinationMessage,
    GraphBuilderAgent,
    ValidatorAgent,
    QueryEngineAgent,
    create_agent_registry,
    register_agent,
    dispatch_message,
)


class TestAgentRoles:
    """Test agent role definitions."""

    def test_six_roles_defined(self):
        assert len(AgentRole) == 6

    def test_role_values(self):
        expected = {"graph_builder", "validator", "query_engine", "orchestrator", "learner", "curator"}
        assert {r.value for r in AgentRole} == expected


class TestAgentCapabilities:
    """Test agent capability definitions."""

    def test_seven_capabilities(self):
        assert len(AgentCapability) == 7

    def test_capability_values(self):
        expected = {
            "node_creation", "node_validation", "edge_creation",
            "graph_query", "vertical_expertise", "conflict_resolution",
            "schema_evolution",
        }
        assert {c.value for c in AgentCapability} == expected


class TestCoordinationMessage:
    """Test coordination message model."""

    def test_create_message(self):
        msg = CoordinationMessage(
            sender="agent_1",
            recipient="agent_2",
            action="add_node",
            payload={"node": {"id": "test", "label": "Test", "node_type": "concept", "vertical": "ml_algorithms"}},
        )
        assert msg.sender == "agent_1"
        assert msg.recipient == "agent_2"
        assert msg.action == "add_node"

    def test_message_to_dict(self):
        msg = CoordinationMessage(sender="a", recipient="b", action="test")
        d = msg.to_dict()
        assert d["sender"] == "a"
        assert d["action"] == "test"


class TestGraphBuilderAgent:
    """Test the GraphBuilder agent."""

    def test_add_node_action(self):
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        msg = CoordinationMessage(
            sender="test",
            recipient="builder_1",
            action="add_node",
            payload={"node": {
                "id": "test_concept",
                "label": "Test Concept",
                "node_type": "concept",
                "vertical": "ml_algorithms",
            }},
        )
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert "test_concept" in g.nodes

    def test_add_edge_action(self):
        g = create_empty_graph()
        # Pre-populate with nodes
        g.add_node("node_a", vertical="ml_algorithms", node_type="concept", label="A")
        g.add_node("node_b", vertical="ml_algorithms", node_type="concept", label="B")
        agent = GraphBuilderAgent("builder_1", g)
        msg = CoordinationMessage(
            sender="test",
            recipient="builder_1",
            action="add_edge",
            payload={"edge": {
                "source": "node_a",
                "target": "node_b",
                "edge_type": "depends_on",
            }},
        )
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert g.has_edge("node_a", "node_b")

    def test_unknown_action(self):
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        msg = CoordinationMessage(sender="test", recipient="builder_1", action="unknown")
        result = agent.handle(msg)
        assert result["status"] == "error"

    def test_can_handle(self):
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        assert agent.can_handle("add_node") is True
        assert agent.can_handle("add_edge") is True
        assert agent.can_handle("validate_graph") is False


class TestValidatorAgent:
    """Test the Validator agent."""

    def test_validate_graph_clean(self):
        g = create_empty_graph()
        g.add_node("n1", vertical="ml_algorithms", node_type="concept", label="N1")
        agent = ValidatorAgent("validator_1", g)
        msg = CoordinationMessage(sender="test", recipient="validator_1", action="validate_graph")
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["errors"] == []

    def test_validate_graph_with_errors(self):
        g = create_empty_graph()
        g.add_node("n1")  # Missing vertical and node_type
        agent = ValidatorAgent("validator_1", g)
        msg = CoordinationMessage(sender="test", recipient="validator_1", action="validate_graph")
        result = agent.handle(msg)
        assert result["status"] == "error"
        assert len(result["errors"]) > 0

    def test_check_vertical(self):
        g = create_empty_graph()
        g.add_node("n1", vertical="ml_algorithms", node_type="concept", label="N1")
        g.add_node("n2", vertical="ml_algorithms", node_type="concept", label="N2")
        agent = ValidatorAgent("validator_1", g)
        msg = CoordinationMessage(
            sender="test",
            recipient="validator_1",
            action="check_vertical",
            payload={"vertical": "ml_algorithms"},
        )
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["node_count"] == 2

    def test_find_cycles_empty(self):
        g = create_empty_graph()
        agent = ValidatorAgent("validator_1", g)
        msg = CoordinationMessage(sender="test", recipient="validator_1", action="find_cycles")
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["cycle_count"] == 0


class TestQueryEngineAgent:
    """Test the QueryEngine agent."""

    def test_query_nodes_by_vertical(self):
        g = create_empty_graph()
        g.add_node("n1", vertical="ml_algorithms", node_type="concept", label="N1")
        g.add_node("n2", vertical="nlp", node_type="concept", label="N2")
        agent = QueryEngineAgent("query_1", g)
        msg = CoordinationMessage(
            sender="test",
            recipient="query_1",
            action="query_nodes",
            payload={"vertical": "ml_algorithms"},
        )
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["count"] == 1

    def test_query_edges(self):
        g = create_empty_graph()
        g.add_node("n1", vertical="ml_algorithms", node_type="concept", label="N1")
        g.add_node("n2", vertical="ml_algorithms", node_type="concept", label="N2")
        g.add_edge("n1", "n2", edge_type="depends_on")
        agent = QueryEngineAgent("query_1", g)
        msg = CoordinationMessage(sender="test", recipient="query_1", action="query_edges")
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["count"] == 1

    def test_shortest_path(self):
        g = create_empty_graph()
        g.add_node("a", vertical="ml_algorithms", node_type="concept", label="A")
        g.add_node("b", vertical="ml_algorithms", node_type="concept", label="B")
        g.add_node("c", vertical="ml_algorithms", node_type="concept", label="C")
        g.add_edge("a", "b", edge_type="depends_on")
        g.add_edge("b", "c", edge_type="depends_on")
        agent = QueryEngineAgent("query_1", g)
        msg = CoordinationMessage(
            sender="test",
            recipient="query_1",
            action="shortest_path",
            payload={"source": "a", "target": "c"},
        )
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["path"] == ["a", "b", "c"]
        assert result["length"] == 2

    def test_shortest_path_no_path(self):
        g = create_empty_graph()
        g.add_node("a", vertical="ml_algorithms", node_type="concept", label="A")
        g.add_node("b", vertical="ml_algorithms", node_type="concept", label="B")
        agent = QueryEngineAgent("query_1", g)
        msg = CoordinationMessage(
            sender="test",
            recipient="query_1",
            action="shortest_path",
            payload={"source": "a", "target": "b"},
        )
        result = agent.handle(msg)
        assert result["status"] == "error"

    def test_get_verticals(self):
        g = create_empty_graph()
        g.add_node("n1", vertical="ml_algorithms", node_type="concept", label="N1")
        agent = QueryEngineAgent("query_1", g)
        msg = CoordinationMessage(sender="test", recipient="query_1", action="get_verticals")
        result = agent.handle(msg)
        assert result["status"] == "ok"
        assert result["verticals"]["ml_algorithms"] == 1


class TestAgentRegistry:
    """Test agent registration and dispatch."""

    def test_create_registry(self):
        reg = create_agent_registry()
        assert reg == {}

    def test_register_agent(self):
        reg = create_agent_registry()
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        assert register_agent(reg, agent) is True
        assert "builder_1" in reg

    def test_register_duplicate_fails(self):
        reg = create_agent_registry()
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        register_agent(reg, agent)
        assert register_agent(reg, agent) is False

    def test_dispatch_to_specific_agent(self):
        reg = create_agent_registry()
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        register_agent(reg, agent)
        msg = CoordinationMessage(
            sender="test",
            recipient="builder_1",
            action="add_node",
            payload={"node": {
                "id": "test",
                "label": "Test",
                "node_type": "concept",
                "vertical": "ml_algorithms",
            }},
        )
        result = dispatch_message(reg, msg)
        assert result["status"] == "ok"

    def test_dispatch_unknown_recipient(self):
        reg = create_agent_registry()
        msg = CoordinationMessage(sender="test", recipient="nobody", action="test")
        result = dispatch_message(reg, msg)
        assert result["status"] == "error"

    def test_dispatch_agent_cannot_handle(self):
        reg = create_agent_registry()
        g = create_empty_graph()
        agent = GraphBuilderAgent("builder_1", g)
        register_agent(reg, agent)
        msg = CoordinationMessage(sender="test", recipient="builder_1", action="validate_graph")
        result = dispatch_message(reg, msg)
        assert result["status"] == "error"

    def test_broadcast(self):
        reg = create_agent_registry()
        g = create_empty_graph()
        register_agent(reg, GraphBuilderAgent("builder_1", g))
        register_agent(reg, ValidatorAgent("validator_1", g))
        msg = CoordinationMessage(
            sender="test",
            recipient="broadcast",
            action="validate_graph",
        )
        result = dispatch_message(reg, msg)
        assert result["status"] == "broadcast"
        assert "validator_1" in result["results"]
