#!/usr/bin/env python3
"""
manifest_schema.py — Pydantic V2 Schema for Hermes Plugins & Capability Contracts
Enforces the 3-Ring Security Model and Zero-Cost verification.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PermissionLevel(str, Enum):
    R0_READ_ONLY = "R0"             # Deterministic read, zero-side-effects
    R1_LOCAL_COMPUTE = "R1"         # Local CPU compute, in-memory transforms
    R2_LOCAL_SANDBOX_WRITE = "R2"   # Sandboxed workspace writes
    R3_LOCAL_EXEC = "R3"            # Subprocess execution in sandbox
    R4_NETWORK_OUTBOUND = "R4"      # Limited outbound network (web search, git)
    R5_CRITICAL_SYSTEM = "R5"       # File deletion, root access (Requires User Approval)

class ToolContract(BaseModel):
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Clear explanation of tool capabilities")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for arguments")
    required_permission: PermissionLevel = PermissionLevel.R1_LOCAL_COMPUTE
    zero_cost_guaranteed: bool = Field(default=True, description="Guaranteed 0 cost / free execution")
    timeout_seconds: int = Field(default=60, description="Max execution duration")

class PluginManifest(BaseModel):
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Semantic version string")
    description: str = Field(..., description="Plugin description")
    author: str = Field(default="Hermes Open Source Collective")
    license: str = Field(default="MIT / Apache-2.0")
    permission_ring: PermissionLevel = PermissionLevel.R2_LOCAL_SANDBOX_WRITE
    tools: List[ToolContract] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
