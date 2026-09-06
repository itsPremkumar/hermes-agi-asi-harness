"""Server Registry — persistent registry of MCP server configurations.

This module provides CRUD management for MCP server records with JSON-file
persistence, capability tagging, search, and health status tracking.

Usage::

    registry = MCPServerRegistry(config_path="~/.hermes-asi/mcp_servers.json")
    registry.load()
    record = registry.register(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        capabilities=["filesystem", "read"],
    )
    registry.save()
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Record model
# ---------------------------------------------------------------------------

@dataclass
class MCPServerRecord:
    """A single MCP server entry in the registry.

    Attributes
    ----------
    id
        Unique UUID for this record.
    name
        Human-readable name (unique within the registry).
    description
        Short description of what this server provides.
    transport
        Transport kind: ``"stdio"``, ``"http"``, or ``"sse"``.
    command
        For stdio transport — the executable to launch.
    args
        For stdio transport — command-line arguments.
    env
        For stdio transport — environment variables.
    cwd
        For stdio transport — working directory.
    url
        For http/sse transport — the endpoint URL.
    capabilities
        Capability tags (e.g. ``["filesystem", "read"]``).
    metadata
        Free-form metadata dict.
    health_status
        Last known health status: ``"unknown"``, ``"connected"``, ``"error"``.
    last_health_check
        ISO-8601 timestamp of the last health check.
    enabled
        Whether this server is enabled (can be disabled without removing).
    created_at
        ISO-8601 creation timestamp.
    updated_at
        ISO-8601 last-update timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    transport: str = "stdio"  # stdio | http | sse
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    url: str = ""
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "unknown"
    last_health_check: Optional[str] = None
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class MCPServerRegistry:
    """Thread-safe registry for MCP server records.

    Persists to a JSON file so configuration survives restarts.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path.home() / ".hermes-asi" / "mcp_servers.json")
        self._config_path = Path(config_path)
        self._records: Dict[str, MCPServerRecord] = {}  # id -> record
        self._by_name: Dict[str, str] = {}  # name -> id
        self._by_capability: Dict[str, List[str]] = {}  # capability -> [id, ...]
        self._lock = threading.RLock()
        self._loaded = False

    # -- persistence ------------------------------------------------------

    def load(self) -> bool:
        """Load records from the JSON file. Returns True if file existed."""
        with self._lock:
            if not self._config_path.exists():
                log.debug("Registry file not found: %s", self._config_path)
                self._loaded = True
                return False

            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                log.error("Failed to load registry: %s", exc)
                return False

            if isinstance(data, list):
                records_data = data
            elif isinstance(data, dict) and "servers" in data:
                records_data = data["servers"]
            else:
                log.error("Unexpected registry format")
                return False

            self._records.clear()
            self._by_name.clear()
            self._by_capability.clear()

            for rd in records_data:
                record = MCPServerRecord.from_dict(rd)
                self._records[record.id] = record
                self._by_name[record.name] = record.id
                for cap in record.capabilities:
                    self._by_capability.setdefault(cap, []).append(record.id)

            self._loaded = True
            log.info("Loaded %d MCP server records from %s", len(self._records), self._config_path)
            return True

    def save(self) -> None:
        """Persist records to the JSON file."""
        with self._lock:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "servers": [r.to_dict() for r in self._records.values()],
            }
            tmp_path = self._config_path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(self._config_path)
            log.debug("Saved %d MCP server records to %s", len(self._records), self._config_path)

    # -- CRUD -------------------------------------------------------------

    def register(
        self,
        name: str,
        transport: str = "stdio",
        command: str = "",
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        url: str = "",
        description: str = "",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MCPServerRecord:
        """Register a new MCP server."""
        with self._lock:
            if name in self._by_name:
                raise ValueError(f"Server '{name}' already registered")

            record = MCPServerRecord(
                name=name,
                description=description,
                transport=transport,
                command=command,
                args=args or [],
                env=env or {},
                cwd=cwd,
                url=url,
                capabilities=capabilities or [],
                metadata=metadata or {},
            )
            self._records[record.id] = record
            self._by_name[name] = record.id
            for cap in record.capabilities:
                self._by_capability.setdefault(cap, []).append(record.id)

            log.info("Registered MCP server '%s' (%s)", name, transport)
            return record

    def unregister(self, server_id: str) -> bool:
        """Remove a server record by ID."""
        with self._lock:
            record = self._records.pop(server_id, None)
            if record is None:
                return False
            self._by_name.pop(record.name, None)
            for cap in record.capabilities:
                ids = self._by_capability.get(cap, [])
                if server_id in ids:
                    ids.remove(server_id)
            log.info("Unregistered MCP server '%s'", record.name)
            return True

    def update(self, server_id: str, **kwargs) -> MCPServerRecord:
        """Update fields of an existing server record."""
        with self._lock:
            record = self._records.get(server_id)
            if record is None:
                raise KeyError(f"Server ID '{server_id}' not found")

            # Remove old capability index entries
            for cap in record.capabilities:
                ids = self._by_capability.get(cap, [])
                if server_id in ids:
                    ids.remove(server_id)

            for key, value in kwargs.items():
                if key == "id" or key == "created_at":
                    continue  # immutable
                if hasattr(record, key):
                    setattr(record, key, value)

            record.updated_at = datetime.utcnow().isoformat()

            # Re-index capabilities
            for cap in record.capabilities:
                self._by_capability.setdefault(cap, []).append(server_id)

            log.debug("Updated MCP server '%s'", record.name)
            return record

    # -- queries ----------------------------------------------------------

    @property
    def records(self) -> Dict[str, MCPServerRecord]:
        return dict(self._records)

    def get(self, server_id: str) -> Optional[MCPServerRecord]:
        return self._records.get(server_id)

    def get_by_name(self, name: str) -> Optional[MCPServerRecord]:
        sid = self._by_name.get(name)
        return self._records.get(sid) if sid else None

    def list_all(self) -> List[MCPServerRecord]:
        return list(self._records.values())

    def list_enabled(self) -> List[MCPServerRecord]:
        return [r for r in self._records.values() if r.enabled]

    def get_by_capability(self, capability: str) -> List[MCPServerRecord]:
        ids = self._by_capability.get(capability, [])
        return [self._records[i] for i in ids if i in self._records]

    def search(self, query: str) -> List[MCPServerRecord]:
        """Search servers by name, description, or capabilities."""
        q = query.lower()
        results: List[MCPServerRecord] = []
        for r in self._records.values():
            if (q in r.name.lower() or
                q in r.description.lower() or
                any(q in c.lower() for c in r.capabilities)):
                results.append(r)
        return results

    def set_health(self, server_id: str, status: str, check_time: Optional[str] = None) -> None:
        """Update the health status of a server."""
        with self._lock:
            record = self._records.get(server_id)
            if record:
                record.health_status = status
                record.last_health_check = check_time or datetime.utcnow().isoformat()

    def count(self) -> int:
        return len(self._records)

    def is_loaded(self) -> bool:
        return self._loaded

    # -- export -----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "servers": [r.to_dict() for r in self._records.values()],
        }

    def __repr__(self) -> str:
        return f"<MCPServerRegistry records={len(self._records)}>"
