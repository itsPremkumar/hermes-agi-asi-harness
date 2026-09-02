"""approval.py — Human approval gate for Level 10 modifications.

Level 10 modifications require explicit human approval before they can
be applied. This module provides the approval gate that blocks high-risk
evolution changes until a human operator reviews and approves them.

Module API:
- ApprovalStatus: enum-like status values
- ApprovalRequest: a request for human approval
- ApprovalGate: manages approval workflow
- ApprovalRecord: record of an approval decision
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class ApprovalStatus:
    """Status values for approval requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Approval request
# ---------------------------------------------------------------------------


@dataclass
class ApprovalRequest:
    """A request for human approval of a Level 10 modification."""

    request_id: str
    plugin_name: str
    description: str
    changes: dict[str, Any]
    risk_level: int  # 1-10
    requested_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: str = ApprovalStatus.PENDING
    approved_by: str = ""
    approved_at: float = 0.0
    rejection_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            # Default expiry: 24 hours
            self.expires_at = self.requested_at + 86400

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == ApprovalStatus.REJECTED

    def approve(self, approver: str) -> None:
        """Approve this request."""
        self.status = ApprovalStatus.APPROVED
        self.approved_by = approver
        self.approved_at = time.time()

    def reject(self, reason: str) -> None:
        """Reject this request."""
        self.status = ApprovalStatus.REJECTED
        self.rejection_reason = reason

    def cancel(self) -> None:
        """Cancel this request."""
        self.status = ApprovalStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "plugin_name": self.plugin_name,
            "description": self.description,
            "changes": self.changes,
            "risk_level": self.risk_level,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejection_reason": self.rejection_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Approval record
# ---------------------------------------------------------------------------


@dataclass
class ApprovalRecord:
    """Record of an approval decision."""

    request_id: str
    plugin_name: str
    decision: str  # approved or rejected
    approver: str
    timestamp: float = field(default_factory=time.time)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "plugin_name": self.plugin_name,
            "decision": self.decision,
            "approver": self.approver,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Approval gate
# ---------------------------------------------------------------------------


class ApprovalGate:
    """Manages the approval workflow for Level 10 modifications.

    Usage:
        gate = ApprovalGate()
        request = gate.request_approval("my_plugin", "...", {"x": 1}, risk_level=10)
        # Human reviews...
        gate.approve(request.request_id, "operator")
        if gate.is_approved(request.request_id):
            # Apply changes
    """

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._records: list[ApprovalRecord] = []

    def request_approval(
        self,
        plugin_name: str,
        description: str,
        changes: dict[str, Any],
        risk_level: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request.

        Returns the request object. The request starts in PENDING status.
        """
        request_id = self._make_id(plugin_name, changes)
        request = ApprovalRequest(
            request_id=request_id,
            plugin_name=plugin_name,
            description=description,
            changes=changes,
            risk_level=risk_level,
            metadata=metadata or {},
        )
        self._requests[request_id] = request
        return request

    def approve(self, request_id: str, approver: str) -> bool:
        """Approve a request. Returns True if successful."""
        request = self._requests.get(request_id)
        if request is None:
            return False
        if request.is_expired:
            request.status = ApprovalStatus.EXPIRED
            return False
        request.approve(approver)
        self._records.append(
            ApprovalRecord(
                request_id=request_id,
                plugin_name=request.plugin_name,
                decision=ApprovalStatus.APPROVED,
                approver=approver,
            )
        )
        return True

    def reject(self, request_id: str, reason: str) -> bool:
        """Reject a request. Returns True if successful."""
        request = self._requests.get(request_id)
        if request is None:
            return False
        request.reject(reason)
        self._records.append(
            ApprovalRecord(
                request_id=request_id,
                plugin_name=request.plugin_name,
                decision=ApprovalStatus.REJECTED,
                approver="",
                reason=reason,
            )
        )
        return True

    def cancel(self, request_id: str) -> bool:
        """Cancel a request. Returns True if successful."""
        request = self._requests.get(request_id)
        if request is None:
            return False
        request.cancel()
        return True

    def is_approved(self, request_id: str) -> bool:
        """Check if a request is approved."""
        request = self._requests.get(request_id)
        if request is None:
            return False
        if request.is_expired:
            request.status = ApprovalStatus.EXPIRED
            return False
        return request.is_approved

    def is_pending(self, request_id: str) -> bool:
        """Check if a request is pending."""
        request = self._requests.get(request_id)
        if request is None:
            return False
        if request.is_expired:
            request.status = ApprovalStatus.EXPIRED
            return False
        return request.is_pending

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        """List all pending requests."""
        pending = []
        for req in self._requests.values():
            if req.is_expired:
                req.status = ApprovalStatus.EXPIRED
            elif req.is_pending:
                pending.append(req)
        return pending

    def list_all(self) -> list[ApprovalRequest]:
        """List all requests."""
        for req in self._requests.values():
            if req.is_expired:
                req.status = ApprovalStatus.EXPIRED
        return list(self._requests.values())

    def list_records(self) -> list[ApprovalRecord]:
        """List all approval records."""
        return list(self._records)

    def requires_approval(self, risk_level: int) -> bool:
        """Check if a risk level requires approval."""
        return risk_level >= 10

    def clear(self) -> None:
        """Clear all requests and records."""
        self._requests.clear()
        self._records.clear()

    def __len__(self) -> int:
        return len(self._requests)

    def _make_id(self, plugin_name: str, changes: dict[str, Any]) -> str:
        """Generate a stable request ID."""
        payload = json.dumps({"plugin": plugin_name, "changes": changes}, sort_keys=True)
        h = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return f"req-{h}"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def check_approval_gate(risk_level: int, approver: str | None = None) -> tuple[bool, str]:
    """Quick check if a modification can proceed.

    Returns (can_proceed, reason).
    """
    if risk_level < 10:
        return True, "no approval required"
    if approver is None:
        return False, "Level 10 modification requires human approval"
    return True, f"approved by {approver}"
