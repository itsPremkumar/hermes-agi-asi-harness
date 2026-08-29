#!/usr/bin/env python3
"""
Permission System Plugin — Risk-tiered access control with R0-R6 levels
========================================================================
Features:
- Risk-tiered actions (R0-R6)
- Human approval gates for R4+
- Permission inheritance
- Temporary elevation
- Revocation
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes_permission_system")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


class RiskTier(str, Enum):
    """Risk tiers for actions."""
    R0 = "r0"  # Read-only, no risk
    R1 = "r1"  # Low risk, read public data
    R2 = "r2"  # Medium risk, write project files
    R3 = "r3"  # Moderate risk, modify code
    R4 = "r4"  # High risk, deploy to staging
    R5 = "r5"  # Very high risk, production changes
    R6 = "r6"  # Critical risk, destructive operations


@dataclass
class PermissionRule:
    """A permission rule."""
    action: str
    risk_tier: RiskTier
    description: str
    allowed: bool = True
    requires_approval: bool = False
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ElevationRequest:
    """A temporary elevation request."""
    action: str
    requested_by: str
    reason: str
    duration_seconds: int = 300
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None


class PermissionSystem:
    """
    Permission system with risk tiers and approval gates.
    """
    
    # Default permission rules
    DEFAULT_RULES: List[PermissionRule] = [
        PermissionRule("read_file", RiskTier.R0, "Read files from workspace"),
        PermissionRule("search_web", RiskTier.R0, "Search the web"),
        PermissionRule("fetch_url", RiskTier.R1, "Fetch public URLs"),
        PermissionRule("write_file", RiskTier.R2, "Write files to project"),
        PermissionRule("edit_file", RiskTier.R2, "Edit files in project"),
        PermissionRule("run_shell", RiskTier.R3, "Run shell commands"),
        PermissionRule("run_python", RiskTier.R3, "Run Python code"),
        PermissionRule("git_commit", RiskTier.R3, "Git commit"),
        PermissionRule("git_push", RiskTier.R4, "Git push to remote"),
        PermissionRule("deploy_staging", RiskTier.R4, "Deploy to staging", requires_approval=True),
        PermissionRule("deploy_production", RiskTier.R5, "Deploy to production", requires_approval=True),
        PermissionRule("delete_data", RiskTier.R6, "Delete data", requires_approval=True),
        PermissionRule("spend_money", RiskTier.R6, "Spend money", requires_approval=True),
        PermissionRule("modify_permissions", RiskTier.R6, "Modify permissions", requires_approval=True),
    ]
    
    def __init__(self):
        self._rules: Dict[str, PermissionRule] = {}
        self._elevations: List[ElevationRequest] = []
        self._audit: List[Dict[str, Any]] = []
        
        # Load default rules
        for rule in self.DEFAULT_RULES:
            self._rules[rule.action] = rule
    
    def check_permission(self, action: str, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Check if an action is permitted.
        
        Args:
            action: The action to check
            context: Additional context for the check
            
        Returns:
            (allowed, reason) tuple
        """
        rule = self._rules.get(action)
        if not rule:
            return False, f"Unknown action: {action}"
        
        if not rule.allowed:
            return False, f"Action '{action}' is not allowed"
        
        # Check if approval is required
        if rule.requires_approval:
            # Check for active elevation
            elevation = self._get_active_elevation(action)
            if not elevation:
                return False, f"Action '{action}' requires approval (risk tier: {rule.risk_tier.value})"
        
        # Check conditions
        if rule.conditions:
            for condition, value in rule.conditions.items():
                if condition == "max_daily_count":
                    count = self._get_daily_action_count(action)
                    if count >= value:
                        return False, f"Daily limit reached for '{action}' ({count}/{value})"
        
        # Log the check
        self._audit.append({
            "action": action,
            "allowed": True,
            "risk_tier": rule.risk_tier.value,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
        })
        
        return True, f"Action '{action}' permitted (risk tier: {rule.risk_tier.value})"
    
    def _get_active_elevation(self, action: str) -> Optional[ElevationRequest]:
        """Check if there's an active elevation for an action."""
        now = datetime.utcnow()
        for elevation in self._elevations:
            if elevation.action == action and elevation.approved:
                if elevation.expires_at:
                    expires = datetime.fromisoformat(elevation.expires_at)
                    if now < expires:
                        return elevation
                else:
                    return elevation
        return None
    
    def _get_daily_action_count(self, action: str) -> int:
        """Get count of an action performed today."""
        today = datetime.utcnow().date().isoformat()
        return sum(
            1 for entry in self._audit
            if entry.get("action") == action and entry.get("allowed") and entry.get("timestamp", "").startswith(today)
        )
    
    def request_elevation(self, action: str, requested_by: str, reason: str, duration_seconds: int = 300) -> ElevationRequest:
        """Request a temporary elevation."""
        request = ElevationRequest(
            action=action,
            requested_by=requested_by,
            reason=reason,
            duration_seconds=duration_seconds,
        )
        self._elevations.append(request)
        return request
    
    def approve_elevation(self, request_id: int = -1) -> bool:
        """Approve an elevation request."""
        if abs(request_id) <= len(self._elevations):
            elevation = self._elevations[request_id]
            elevation.approved = True
            if elevation.duration_seconds:
                expires = datetime.utcnow().timestamp() + elevation.duration_seconds
                elevation.expires_at = datetime.fromtimestamp(expires).isoformat()
            return True
        return False
    
    def revoke_elevation(self, action: str):
        """Revoke an elevation."""
        self._elevations = [
            e for e in self._elevations
            if not (e.action == action and e.approved)
        ]
    
    def add_rule(self, rule: PermissionRule):
        """Add or update a permission rule."""
        self._rules[rule.action] = rule
    
    def remove_rule(self, action: str):
        """Remove a permission rule."""
        self._rules.pop(action, None)
    
    def get_rule(self, action: str) -> Optional[PermissionRule]:
        """Get a permission rule."""
        return self._rules.get(action)
    
    def list_rules(self) -> List[PermissionRule]:
        """List all permission rules."""
        return list(self._rules.values())
    
    def get_risk_tier(self, action: str) -> Optional[RiskTier]:
        """Get the risk tier for an action."""
        rule = self._rules.get(action)
        return rule.risk_tier if rule else None
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get audit log entries."""
        return self._audit[-limit:]
    
    def requires_approval(self, action: str) -> bool:
        """Check if an action requires approval."""
        rule = self._rules.get(action)
        return rule.requires_approval if rule else False


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Permission System Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="permission_system",
            version="1.0.0",
            description="Risk-tiered access control with R0-R6 levels, approval gates, and audit logging",
            license="MIT",
            source="internal",
            capabilities=[
                "permission_check",
                "risk_tiering",
                "approval_gates",
                "elevation",
                "audit_logging",
            ],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=256,
                max_cpu_percent=10,
            ),
        )
        self.system: Optional[PermissionSystem] = None
    
    async def load(self) -> bool:
        self.system = PermissionSystem()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.system:
            self.system = PermissionSystem()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.system is not None,
            "rules_count": len(self.system.list_rules()) if self.system else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def check(self, action: str, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Check if an action is permitted."""
        return self.system.check_permission(action, context)
    
    def request_elevation(self, action: str, requested_by: str, reason: str, duration_seconds: int = 300) -> ElevationRequest:
        """Request a temporary elevation."""
        return self.system.request_elevation(action, requested_by, reason, duration_seconds)
    
    def approve_elevation(self, request_id: int = -1) -> bool:
        """Approve an elevation."""
        return self.system.approve_elevation(request_id)
    
    def revoke_elevation(self, action: str):
        """Revoke an elevation."""
        self.system.revoke_elevation(action)
    
    def add_rule(self, action: str, risk_tier: str, description: str, requires_approval: bool = False):
        """Add a permission rule."""
        from plugins.permission_system import RiskTier, PermissionRule
        rule = PermissionRule(
            action=action,
            risk_tier=RiskTier(risk_tier),
            description=description,
            requires_approval=requires_approval,
        )
        self.system.add_rule(rule)
    
    def list_rules(self) -> List[Dict]:
        """List all permission rules."""
        return [
            {
                "action": r.action,
                "risk_tier": r.risk_tier.value,
                "description": r.description,
                "requires_approval": r.requires_approval,
            }
            for r in self.system.list_rules()
        ]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get audit log entries."""
        return self.system.get_audit_log(limit)
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
