"""Tests for ConsensusEngine."""
from src.mesh.consensus_engine import ConsensusEngine, ProposalStatus


class TestConsensusEngine:
    def test_create(self):
        ce = ConsensusEngine()
        assert ce.count() == 0

    def test_propose(self):
        ce = ConsensusEngine()
        proposal = ce.propose("node1", "value1")
        assert proposal.proposer == "node1"
        assert proposal.value == "value1"
        assert proposal.status == ProposalStatus.PENDING
        assert ce.count() == 1

    def test_vote(self):
        ce = ConsensusEngine()
        proposal = ce.propose("node1", "value1")
        assert ce.vote(proposal.id, "node2", True) is True
        assert ce.vote(proposal.id, "node3", False) is True

    def test_tally(self):
        ce = ConsensusEngine()
        proposal = ce.propose("node1", "value1")
        ce.vote(proposal.id, "node2", True)
        ce.vote(proposal.id, "node3", True)
        ce.vote(proposal.id, "node4", False)
        tally = ce.tally(proposal.id)
        assert tally["accepts"] == 2
        assert tally["rejects"] == 1
        assert tally["accepted"] is True

    def test_finalize_accepted(self):
        ce = ConsensusEngine()
        proposal = ce.propose("node1", "value1")
        ce.vote(proposal.id, "node2", True)
        ce.vote(proposal.id, "node3", True)
        status = ce.finalize(proposal.id)
        assert status == ProposalStatus.ACCEPTED

    def test_finalize_rejected(self):
        ce = ConsensusEngine()
        proposal = ce.propose("node1", "value1")
        ce.vote(proposal.id, "node2", False)
        ce.vote(proposal.id, "node3", False)
        status = ce.finalize(proposal.id)
        assert status == ProposalStatus.REJECTED

    def test_get(self):
        ce = ConsensusEngine()
        proposal = ce.propose("node1", "value1")
        result = ce.get(proposal.id)
        assert result is not None
        assert result.value == "value1"
