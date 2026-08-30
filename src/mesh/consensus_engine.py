"""Consensus Engine — distributed consensus for the mesh."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProposalStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABORTED = "aborted"


@dataclass
class Proposal:
    id: str
    proposer: str
    value: Any
    status: ProposalStatus = ProposalStatus.PENDING
    votes: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConsensusEngine:
    """Distributed consensus using voting."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._proposals: dict[str, Proposal] = {}

    def propose(self, proposer: str, value: Any) -> Proposal:
        proposal = Proposal(id=str(uuid.uuid4()), proposer=proposer, value=value)
        self._proposals[proposal.id] = proposal
        return proposal

    def vote(self, proposal_id: str, voter: str, accept: bool) -> bool:
        if proposal_id in self._proposals:
            self._proposals[proposal_id].votes[voter] = accept
            return True
        return False

    def tally(self, proposal_id: str) -> dict[str, Any]:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"error": "proposal not found"}
        accepts = sum(1 for v in proposal.votes.values() if v)
        rejects = sum(1 for v in proposal.votes.values() if not v)
        return {
            "accepts": accepts,
            "rejects": rejects,
            "total": len(proposal.votes),
            "accepted": accepts > rejects,
        }

    def finalize(self, proposal_id: str) -> ProposalStatus:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return ProposalStatus.ABORTED
        tally = self.tally(proposal_id)
        proposal.status = ProposalStatus.ACCEPTED if tally["accepted"] else ProposalStatus.REJECTED
        return proposal.status

    def get(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)

    def list_all(self) -> list[Proposal]:
        return list(self._proposals.values())

    def count(self) -> int:
        return len(self._proposals)
