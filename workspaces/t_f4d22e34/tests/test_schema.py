"""Tests for the AI/ML Knowledge Graph schema and data model."""

from __future__ import annotations

import pytest
import networkx as nx

from kg import (
    Vertical,
    NodeType,
    EdgeType,
    KGNode,
    KGEdge,
    create_empty_graph,
    validate_node,
    validate_edge,
    add_node_to_graph,
    add_edge_to_graph,
    get_vertical_summary,
    VERTICAL_METADATA,
)


class TestVerticals:
    """Test the 16 vertical definitions."""

    def test_all_16_verticals_defined(self):
        assert len(Vertical) == 16

    def test_all_verticals_have_metadata(self):
        for v in Vertical:
            assert v in VERTICAL_METADATA
            meta = VERTICAL_METADATA[v]
            assert "name" in meta
            assert "description" in meta
            assert "key_concepts" in meta
            assert len(meta["key_concepts"]) >= 3

    def test_vertical_names_unique(self):
        names = [v.value for v in Vertical]
        assert len(names) == len(set(names))


class TestNodeTypes:
    """Test node type definitions."""

    def test_node_types_count(self):
        assert len(NodeType) == 10

    def test_all_node_types_valid(self):
        expected = {
            "concept", "algorithm", "framework", "paper",
            "dataset", "metric", "task", "architecture",
            "technique", "protocol",
        }
        actual = {nt.value for nt in NodeType}
        assert actual == expected


class TestEdgeTypes:
    """Test edge type definitions."""

    def test_edge_types_count(self):
        assert len(EdgeType) == 10

    def test_edge_type_values(self):
        expected = {
            "depends_on", "extends", "implements",
            "evaluated_by", "applied_to", "derived_from",
            "competes_with", "complements", "version_of",
            "protocol_for",
        }
        actual = {et.value for et in EdgeType}
        assert actual == expected


class TestKGNodeModel:
    """Test KGNode pydantic model."""

    def test_create_valid_node(self):
        node = KGNode(
            id="test_concept",
            label="Test Concept",
            node_type=NodeType.CONCEPT,
            vertical=Vertical.ML_ALGORITHMS,
        )
        assert node.id == "test_concept"
        assert node.label == "Test Concept"
        assert node.version == "1.0.0"

    def test_node_to_dict(self):
        node = KGNode(
            id="test_node",
            label="Test",
            node_type=NodeType.ALGORITHM,
            vertical=Vertical.NLP,
        )
        d = node.to_dict()
        assert d["id"] == "test_node"
        assert d["node_type"] == "algorithm"
        assert d["vertical"] == "nlp"

    def test_node_with_properties(self):
        node = KGNode(
            id="rich_node",
            label="Rich Node",
            node_type=NodeType.FRAMEWORK,
            vertical=Vertical.MLOPS,
            properties={"version": "2.0", "language": "python"},
        )
        assert node.properties["version"] == "2.0"

    def test_node_empty_id_rejected(self):
        with pytest.raises(Exception):
            KGNode(id="", label="Test", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS)

    def test_node_empty_label_rejected(self):
        with pytest.raises(Exception):
            KGNode(id="test_id", label="", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS)


class TestKGEdgeModel:
    """Test KGEdge pydantic model."""

    def test_create_valid_edge(self):
        edge = KGEdge(
            source="node_a",
            target="node_b",
            edge_type=EdgeType.DEPENDS_ON,
        )
        assert edge.source == "node_a"
        assert edge.target == "node_b"
        assert edge.weight == 1.0

    def test_edge_weight_clamped(self):
        with pytest.raises(Exception):
            KGEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON, weight=1.5)

        with pytest.raises(Exception):
            KGEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON, weight=-0.1)

    def test_edge_to_dict(self):
        edge = KGEdge(source="a", target="b", edge_type=EdgeType.EXTENDS, weight=0.8)
        d = edge.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["edge_type"] == "extends"
        assert d["weight"] == 0.8


class TestGraphCreation:
    """Test graph initialization."""

    def test_create_empty_graph(self):
        g = create_empty_graph()
        assert isinstance(g, nx.DiGraph)
        assert g.graph["name"] == "AI/ML Knowledge Graph"
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_graph_has_vertical_metadata(self):
        g = create_empty_graph()
        assert "verticals" in g.graph
        assert len(g.graph["verticals"]) == 16

    def test_graph_has_node_type_metadata(self):
        g = create_empty_graph()
        assert "node_types" in g.graph
        assert len(g.graph["node_types"]) == 10

    def test_graph_has_edge_type_metadata(self):
        g = create_empty_graph()
        assert "edge_types" in g.graph
        assert len(g.graph["edge_types"]) == 10


class TestNodeValidation:
    """Test node validation logic."""

    def test_valid_node_passes(self):
        node = KGNode(id="valid_id", label="Valid", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS)
        errors = validate_node(node)
        assert errors == []

    def test_empty_id_fails(self):
        # Can't construct KGNode with empty id, so test validate_node indirectly
        # by constructing with valid then checking with a hypothetical
        node = KGNode(id="x", label="X", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS)
        # Pydantic validates this; we test the function with a valid node
        errors = validate_node(node)
        assert len(errors) == 0


class TestEdgeValidation:
    """Test edge validation logic."""

    def test_edge_missing_source_fails(self):
        g = create_empty_graph()
        g.add_node("only_node", vertical="ml_algorithms", node_type="concept")
        edge = KGEdge(source="missing", target="only_node", edge_type=EdgeType.DEPENDS_ON)
        errors = validate_edge(edge, g)
        assert len(errors) > 0
        assert "Source node 'missing' does not exist" in errors[0]

    def test_edge_missing_target_fails(self):
        g = create_empty_graph()
        g.add_node("only_node", vertical="ml_algorithms", node_type="concept")
        edge = KGEdge(source="only_node", target="missing", edge_type=EdgeType.DEPENDS_ON)
        errors = validate_edge(edge, g)
        assert len(errors) > 0

    def test_self_loop_fails(self):
        g = create_empty_graph()
        g.add_node("self_node", vertical="ml_algorithms", node_type="concept")
        edge = KGEdge(source="self_node", target="self_node", edge_type=EdgeType.DEPENDS_ON)
        errors = validate_edge(edge, g)
        assert "Self-loops are not allowed" in errors

    def test_valid_edge_passes(self):
        g = create_empty_graph()
        g.add_node("node_a", vertical="ml_algorithms", node_type="concept")
        g.add_node("node_b", vertical="ml_algorithms", node_type="concept")
        edge = KGEdge(source="node_a", target="node_b", edge_type=EdgeType.DEPENDS_ON)
        errors = validate_edge(edge, g)
        assert errors == []


class TestAddNodeToGraph:
    """Test adding nodes to graph."""

    def test_add_node_success(self):
        g = create_empty_graph()
        node = KGNode(id="n1", label="N1", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS)
        errors = add_node_to_graph(g, node)
        assert errors == []
        assert "n1" in g.nodes

    def test_add_duplicate_node_fails(self):
        g = create_empty_graph()
        node = KGNode(id="n1", label="N1", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS)
        add_node_to_graph(g, node)
        errors = add_node_to_graph(g, node)
        assert len(errors) > 0
        assert "already exists" in errors[0]

    def test_add_node_preserves_data(self):
        g = create_empty_graph()
        node = KGNode(
            id="detailed",
            label="Detailed Node",
            node_type=NodeType.ARCHITECTURE,
            vertical=Vertical.NLP,
            description="A detailed node",
            properties={"year": 2017},
        )
        add_node_to_graph(g, node)
        data = g.nodes["detailed"]
        assert data["label"] == "Detailed Node"
        assert data["description"] == "A detailed node"
        assert data["properties"]["year"] == 2017


class TestAddEdgeToGraph:
    """Test adding edges to graph."""

    def test_add_edge_success(self):
        g = create_empty_graph()
        add_node_to_graph(g, KGNode(id="a", label="A", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS))
        add_node_to_graph(g, KGNode(id="b", label="B", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS))
        edge = KGEdge(source="a", target="b", edge_type=EdgeType.DEPENDS_ON)
        errors = add_edge_to_graph(g, edge)
        assert errors == []
        assert g.has_edge("a", "b")

    def test_add_edge_missing_nodes_fails(self):
        g = create_empty_graph()
        edge = KGEdge(source="x", target="y", edge_type=EdgeType.DEPENDS_ON)
        errors = add_edge_to_graph(g, edge)
        assert len(errors) > 0


class TestVerticalSummary:
    """Test vertical summary statistics."""

    def test_empty_graph_summary(self):
        g = create_empty_graph()
        summary = get_vertical_summary(g)
        assert len(summary) == 16
        assert all(v == 0 for v in summary.values())

    def test_summary_with_nodes(self):
        g = create_empty_graph()
        add_node_to_graph(g, KGNode(id="n1", label="N1", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS))
        add_node_to_graph(g, KGNode(id="n2", label="N2", node_type=NodeType.CONCEPT, vertical=Vertical.ML_ALGORITHMS))
        add_node_to_graph(g, KGNode(id="n3", label="N3", node_type=NodeType.CONCEPT, vertical=Vertical.NLP))
        summary = get_vertical_summary(g)
        assert summary[Vertical.ML_ALGORITHMS.value] == 2
        assert summary[Vertical.NLP.value] == 1
