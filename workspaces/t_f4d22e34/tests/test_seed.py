"""Tests for the seed data loader."""

from __future__ import annotations

import pytest

from kg import create_empty_graph, get_vertical_summary, Vertical
from kg.seed import seed_graph


class TestSeedGraph:
    """Test the seed data loading."""

    def test_seed_populates_all_verticals(self):
        g = create_empty_graph()
        errors = seed_graph(g)
        assert errors == [], f"Seed errors: {errors}"
        summary = get_vertical_summary(g)
        for v in Vertical:
            assert summary[v.value] > 0, f"Vertical '{v.value}' has no nodes"

    def test_seed_creates_expected_node_count(self):
        g = create_empty_graph()
        seed_graph(g)
        # Should have many nodes across all 16 verticals
        assert len(g.nodes) >= 60

    def test_seed_creates_cross_vertical_edges(self):
        g = create_empty_graph()
        seed_graph(g)
        assert len(g.edges) > 0

    def test_seed_no_errors(self):
        g = create_empty_graph()
        errors = seed_graph(g)
        assert errors == []

    def test_seed_vertical_distribution(self):
        g = create_empty_graph()
        seed_graph(g)
        summary = get_vertical_summary(g)
        # Each vertical should have at least 3 nodes
        for v in Vertical:
            assert summary[v.value] >= 3, f"Vertical '{v.value}' has only {summary[v.value]} nodes"

    def test_seed_graph_metadata_preserved(self):
        g = create_empty_graph()
        assert g.graph["name"] == "AI/ML Knowledge Graph"
        seed_graph(g)
        assert g.graph["name"] == "AI/ML Knowledge Graph"
        assert "verticals" in g.graph
