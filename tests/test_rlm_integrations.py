"""
Unit tests for Hermes RLM Deep Integrations across:
- Harnix LangGraph Cognitive State Machine (rlm_node & rlm action step)
- ARC-AGI-3 Solver Programmatic DSL Synthesis (RLMTransformationSynthesizer)
- Deep Research In-Memory Context Offloading (investigate_via_rlm)
"""

from __future__ import annotations

import pytest

from harnix.state import create_initial_state, AgentPhase
from harnix.nodes import rlm_node, _execute_step
from arc_agi_3.engine import Task, Grid, RLMTransformationSynthesizer
from hermes_agi.research import DeepResearchAgent, ResearchDossier


class TestHarnixRLM:
    """Test RLM execution within the Harnix LangGraph runtime."""

    def test_execute_step_rlm_action(self):
        step = {
            "id": "s-rlm-1",
            "action": "rlm",
            "args": ["val = sum([i * 3 for i in range(5)]); val"],
            "description": "Calculate arithmetic progression",
        }
        res = _execute_step(step)
        assert "RLM Result: 30" in res

    def test_rlm_node_execution(self):
        initial_state = create_initial_state("test algorithmic calculation")
        initial_state["context"] = {
            "rlm_code": "output = [x**2 for x in [1, 2, 3]]; output"
        }
        final_state = rlm_node(initial_state)
        assert final_state["phase"] == AgentPhase.RLM
        assert len(final_state["results"]) == 1
        assert final_state["results"][0]["result"] == [1, 4, 9]


class TestARCRLM:
    """Test ARC-AGI-3 solver with RLM programmatic DSL synthesis."""

    def test_arc_programmatic_reflection(self):
        ex_in = Grid([[1, 2], [3, 4]])
        ex_out = Grid([[3, 4], [1, 2]])  # Horizontal flip
        test_in = Grid([[5, 6], [7, 8]])
        task = Task(id="arc_test_1", input_grid=test_in, examples=[(ex_in, ex_out)])

        synth = RLMTransformationSynthesizer()
        try:
            solution = synth.synthesize(task)
            assert solution is not None
            assert solution.score == 1.0
            assert solution.verified is True
            assert solution.grid.cells == [[7, 8], [5, 6]]
        finally:
            synth.close()


class TestResearchRLM:
    """Test Deep Research context offloading via RLM in-memory processing."""

    def test_research_context_offloading(self):
        agent = DeepResearchAgent()
        raw_corpus = [
            "Section 1: Distributed consensus algorithm uses Raft with leader leases.",
            "Section 2: Irrelevant recipe for chocolate chip cookies.",
            "Section 3: Consensus heartbeats must be broadcast every 50ms.",
        ]
        dossier = agent.investigate_via_rlm("distributed consensus algorithm", raw_corpus)
        assert isinstance(dossier, ResearchDossier)
        assert len(dossier.findings) >= 1
        assert any("Raft" in f.summary for f in dossier.findings)
        assert not any("chocolate" in f.summary for f in dossier.findings)
