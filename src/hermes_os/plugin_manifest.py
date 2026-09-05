"""
HERMES — PLUGIN MANIFEST + PERMISSION RINGS (super-harness pattern)
===================================================================
R0_CORE_KERNEL (in-process, reviewed) / R1_SANDBOX_LOCAL (fs, no net)
R2_NETWORK_EXTERNAL (net allowed) / R3_UNRESTRICTED (human approval).
Manifest validated at install/enable; ring enforced before tool calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PermissionRing(str, Enum):
    R0_CORE_KERNEL = "R0"
    R1_SANDBOX_LOCAL = "R1"
    R2_NETWORK_EXTERNAL = "R2"
    R3_UNRESTRICTED = "R3"


@dataclass
class PluginManifest:
    name: str
    version: str = "0.1.0"
    ring: PermissionRing = PermissionRing.R1_SANDBOX_LOCAL
    cost: str = "free"  # free | optional-paid
    tools: List[str] = field(default_factory=list)
    needs_network: bool = False
    needs_shell: bool = False

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.name:
            errors.append("name required")
        if self.needs_network and self.ring in (
            PermissionRing.R0_CORE_KERNEL,
            PermissionRing.R1_SANDBOX_LOCAL,
        ):
            errors.append(f"network needs R2+, got {self.ring.value}")
        if self.needs_shell and self.ring == PermissionRing.R0_CORE_KERNEL:
            errors.append("R0 must not need shell")
        if self.cost not in ("free", "optional-paid"):
            errors.append("cost must be free|optional-paid")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "ring": self.ring.value,
            "cost": self.cost,
            "tools": self.tools,
            "needs_network": self.needs_network,
            "needs_shell": self.needs_shell,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        ring = data.get("ring", "R1")
        try:
            ring_e = PermissionRing(ring)
        except Exception:
            ring_e = PermissionRing.R1_SANDBOX_LOCAL
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            ring=ring_e,
            cost=data.get("cost", "free"),
            tools=list(data.get("tools", [])),
            needs_network=bool(data.get("needs_network", False)),
            needs_shell=bool(data.get("needs_shell", False)),
        )


def load_manifest(plugin_dir: str) -> Optional[PluginManifest]:
    for fname in ("manifest.json", "plugin.yaml", "plugin.json"):
        p = Path(plugin_dir) / fname
        if p.exists() and p.suffix == ".json":
            try:
                return PluginManifest.from_dict(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                return None
    return None


def ring_allows(ring: PermissionRing, action_type: str, args: Dict[str, Any]) -> tuple[bool, str]:
    """Enforce ring at tool-call time."""
    if ring == PermissionRing.R3_UNRESTRICTED:
        return True, ""
    if action_type in ("execute_shell",) and ring in (PermissionRing.R0_CORE_KERNEL,):
        return False, "R0 forbids shell"
    cmd = str((args or {}).get("command", ""))[:500].lower()
    if ring in (PermissionRing.R0_CORE_KERNEL, PermissionRing.R1_SANDBOX_LOCAL):
        if any(k in cmd for k in ("curl ", "wget ", "invoke-webrequest", "http://", "https://")):
            return False, f"Ring {ring.value} forbids network"
    return True, ""


def check_free_gate(manifest: PluginManifest, zero_cost: bool) -> tuple[bool, str]:
    if zero_cost and manifest.cost != "free":
        return False, f"Plugin '{manifest.name}' is {manifest.cost}; blocked by --zero-cost"
    return True, ""
