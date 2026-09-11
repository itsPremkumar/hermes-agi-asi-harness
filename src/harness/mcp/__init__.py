"""MCP Integration Layer for the AGI/ASI harness.

This package provides the bridge between MCP servers and the harness runtime:

- MCPRegistry: server registration, health tracking, capability discovery
- MCPClient: connection management, tool invocation, error handling
- MCPBridge: maps MCP tools to harness tool calls
- MCPAuth: authentication, authorization, credential management
- MCPStreaming: streaming responses, progress updates
- MCPAudit: logging, tracing, compliance tracking
"""

from .registry import MCPRegistry, MCPServerInfo, ServerStatus
from .client import MCPClient, MCPConnectionError, MCPTimeoutError
from .bridge import MCPBridge, ToolMapping
from .auth import MCPAuth, AuthMethod, CredentialStore
from .streaming import MCPStream, StreamEvent, StreamState
from .audit import MCPAudit, AuditEvent, AuditLevel

__all__ = [
    "MCPRegistry",
    "MCPServerInfo",
    "ServerStatus",
    "MCPClient",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPBridge",
    "ToolMapping",
    "MCPAuth",
    "AuthMethod",
    "CredentialStore",
    "MCPStream",
    "StreamEvent",
    "StreamState",
    "MCPAudit",
    "AuditEvent",
    "AuditLevel",
]
