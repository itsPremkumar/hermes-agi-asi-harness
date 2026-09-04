"""
HERMES INTELLIGENCE OS — PLANE 02: IDENTITY & AUTHORITY PLANE
=============================================================
Separates capabilities from authorities:
'Tool available' != 'Tool authorized'
Enforces principal verification, explicit scopes, resource limits, expiration,
and mandatory approval policies across all actuators.
"""

from __future__ import annotations

import fnmatch
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes.os.authority")


@dataclass
class AuthorityContext:
    """The authoritative grant issued to a principal or agent."""
    principal: str                          # user:admin, agent:coder, agent:researcher
    scope: list[str] = field(default_factory=lambda: ["read", "workspace"])  # e.g. read, write:code, exec:rlm, network:search
    capabilities: list[str] = field(default_factory=lambda: ["*"])           # explicit allowed tool names
    resource_limits: dict[str, Any] = field(default_factory=lambda: {
        "max_tokens": 500000,
        "max_execution_seconds": 300,
        "max_subagent_depth": 3,
        "max_file_modifications": 50,
    })
    expiration: Optional[float] = None      # epoch timestamp or None for perpetual
    approval_policy: str = "autonomous"     # autonomous, require_human_approval, prompt_on_destructive
    grant_id: str = field(default_factory=lambda: f"auth-{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time or time.time()
        return self.expiration is not None and now >= self.expiration

    def allows_capability(self, capability_name: str) -> bool:
        """Check if capability matches allowed list or glob patterns."""
        for pattern in self.capabilities:
            if fnmatch.fnmatch(capability_name, pattern):
                return True
        return False

    def allows_scope(self, required_scope: str) -> bool:
        """Check if required scope is satisfied."""
        for s in self.scope:
            if s == "*" or fnmatch.fnmatch(required_scope, s):
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "principal": self.principal,
            "scope": self.scope,
            "capabilities": self.capabilities,
            "resource_limits": self.resource_limits,
            "expiration": self.expiration,
            "approval_policy": self.approval_policy,
            "created_at": self.created_at,
        }


class AuthorityGate:
    """
    Evaluates every proposed action against active authority grants.
    Rejects actions that exceed scope, tokens, tool permissions, or lifespan.
    """

    def __init__(self):
        self._grants: dict[str, AuthorityContext] = {}
        self._init_default_grants()

    def _init_default_grants(self):
        # Admin / Master grant
        self.register_grant(AuthorityContext(
            principal="system:master",
            scope=["*"],
            capabilities=["*"],
            resource_limits={"max_tokens": 10000000, "max_execution_seconds": 3600, "max_subagent_depth": 5},
            approval_policy="autonomous",
        ))
        # Worker grant
        self.register_grant(AuthorityContext(
            principal="agent:worker",
            scope=["read", "write:workspace", "exec:rlm", "network:search"],
            capabilities=["python_tool", "rlm_repl", "filesystem_tool", "agent_eye_search"],
            resource_limits={"max_tokens": 200000, "max_execution_seconds": 180, "max_subagent_depth": 2},
            approval_policy="prompt_on_destructive",
        ))

    def register_grant(self, grant: AuthorityContext) -> str:
        self._grants[grant.principal] = grant
        return grant.grant_id

    def get_grant(self, principal: str) -> Optional[AuthorityContext]:
        return self._grants.get(principal)

    def evaluate_authorization(
        self,
        principal: str,
        action_name: str,
        required_scope: str = "read",
        resource_usage: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        Determine if the action is authorized under the principal's grant.
        Returns (authorized: bool, reason: str).
        """
        grant = self._grants.get(principal)
        if not grant:
            return False, f"Unauthorized: No authority grant found for principal '{principal}'"

        if grant.is_expired():
            return False, f"Unauthorized: Authority grant for '{principal}' expired at {grant.expiration}"

        if not grant.allows_scope(required_scope):
            return False, f"Unauthorized: Principal '{principal}' lacks required scope '{required_scope}'"

        if not grant.allows_capability(action_name):
            return False, f"Unauthorized: Action '{action_name}' is not in allowed capabilities for '{principal}'"

        # Check resource quotas
        if resource_usage:
            tokens = resource_usage.get("tokens_used", 0)
            token_limit = grant.resource_limits.get("max_tokens", 1000000)
            if tokens > token_limit:
                return False, f"Quota Exceeded: Requested action would breach token quota ({tokens} > {token_limit})"

        return True, "Authorized"

    def inherit_grant_for_subagent(self, parent_grant: AuthorityContext, subagent_principal: str, child_scope: Optional[list[str]] = None) -> AuthorityContext:
        """
        Child subagent authority must strictly be a subset of parent authority.
        Enforces monotonic attenuation of authority.
        """
        parent_depth = parent_grant.resource_limits.get("max_subagent_depth", 1)
        if parent_depth <= 0:
            raise PermissionError(f"Subagent depth limit reached; '{parent_grant.principal}' cannot spawn further children.")

        scopes = list(child_scope or parent_grant.scope)
        # Ensure child scope is subset of parent
        valid_scopes = [s for s in scopes if parent_grant.allows_scope(s)]

        child = AuthorityContext(
            principal=subagent_principal,
            scope=valid_scopes,
            capabilities=list(parent_grant.capabilities),
            resource_limits={
                "max_tokens": parent_grant.resource_limits.get("max_tokens", 500000) // 2,
                "max_execution_seconds": parent_grant.resource_limits.get("max_execution_seconds", 300) // 2,
                "max_subagent_depth": parent_depth - 1,
            },
            approval_policy=parent_grant.approval_policy,
            expiration=parent_grant.expiration,
        )
        self.register_grant(child)
        return child
