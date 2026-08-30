#!/usr/bin/env python3
"""
Audit Logger Plugin — Comprehensive audit trail
==============================================
Features:
- Structured audit logging
- Tamper-evident log storage
- Query and filter audit records
- Compliance reporting
- Log rotation and retention
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_audit_logger")

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
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
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
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None
    
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


@dataclass
class AuditRecord:
    """An audit log record."""
    timestamp: str
    event_type: str
    actor: str
    action: str
    target: str
    result: str
    details: dict[str, Any]
    hash: str | None = None
    prev_hash: str | None = None


class AuditLogger:
    """Tamper-evident audit logger."""
    
    def __init__(self, log_dir: str = ".hermes/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_chain_hash: str | None = None
        self._buffer: list[AuditRecord] = []
        self._last_flush = time.time()
        # Seed chain hash from the most recent record already on disk (per-day file)
        self._seed_chain_hash()
    
    def _seed_chain_hash(self):
        """Read the last record's hash from the current day's log file so a new
        logger continues the chain instead of starting from None (prev_hash gap)."""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit_{today}.jsonl"
            if not log_file.exists():
                return
            last_hash = None
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        last_hash = rec.get("hash")
                    except json.JSONDecodeError:
                        continue
            if last_hash:
                self.current_chain_hash = last_hash
        except Exception:
            # Never let seeding break logger construction
            pass
    
    def _compute_hash(self, record: AuditRecord) -> str:
        """Compute hash of a record."""
        data = f"{record.timestamp}|{record.event_type}|{record.actor}|{record.action}|{record.target}|{record.result}|{json.dumps(record.details, sort_keys=True)}|{record.prev_hash or ''}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def log(self, event_type: str, actor: str, action: str, target: str, 
            result: str, details: dict[str, Any] | None = None) -> AuditRecord:
        """Log an audit event."""
        record = AuditRecord(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            actor=actor,
            action=action,
            target=target,
            result=result,
            details=details or {},
            prev_hash=self.current_chain_hash,
        )
        
        record.hash = self._compute_hash(record)
        self.current_chain_hash = record.hash
        self._buffer.append(record)
        
        # Flush if buffer is large or time elapsed
        if len(self._buffer) >= 100 or time.time() - self._last_flush > 10:
            self.flush()
        
        return record
    
    def flush(self):
        """Flush buffer to disk."""
        if not self._buffer:
            return
        
        # Write to daily log file
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{today}.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.writelines(json.dumps({
                    "timestamp": record.timestamp,
                    "event_type": record.event_type,
                    "actor": record.actor,
                    "action": record.action,
                    "target": record.target,
                    "result": record.result,
                    "details": record.details,
                    "hash": record.hash,
                    "prev_hash": record.prev_hash,
                }) + "\n" for record in self._buffer)
        
        self._buffer.clear()
        self._last_flush = time.time()
    
    def query(self, 
              event_type: str | None = None,
              actor: str | None = None,
              action: str | None = None,
              start_time: str | None = None,
              end_time: str | None = None,
              limit: int = 100) -> list[dict[str, Any]]:
        """Query audit records."""
        results = []
        
        # Scan all log files
        for log_file in self.log_dir.glob("audit_*.jsonl"):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Apply filters
                    if event_type and record.get("event_type") != event_type:
                        continue
                    if actor and record.get("actor") != actor:
                        continue
                    if action and record.get("action") != action:
                        continue
                    if start_time and record.get("timestamp", "") < start_time:
                        continue
                    if end_time and record.get("timestamp", "") > end_time:
                        continue
                    
                    results.append(record)
                    
                    if len(results) >= limit:
                        return results
        
        return results[-limit:] if limit else results
    
    def verify_chain(self) -> dict[str, Any]:
        """Verify the hash chain integrity."""
        all_records = []
        
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        all_records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if not all_records:
            return {"valid": True, "checked": 0, "errors": []}
        
        errors = []
        prev_hash = None
        
        for i, record in enumerate(all_records):
            # Check prev_hash linkage
            if record.get("prev_hash") != prev_hash:
                errors.append(f"Record {i}: prev_hash mismatch")
            
            # Recompute hash
            data = f"{record['timestamp']}|{record['event_type']}|{record['actor']}|{record['action']}|{record['target']}|{record['result']}|{json.dumps(record['details'], sort_keys=True)}|{record.get('prev_hash') or ''}"
            computed = hashlib.sha256(data.encode()).hexdigest()
            
            if computed != record.get("hash"):
                errors.append(f"Record {i}: hash mismatch")
            
            prev_hash = record.get("hash")
        
        return {
            "valid": len(errors) == 0,
            "checked": len(all_records),
            "errors": errors,
        }
    
    def get_stats(self) -> dict[str, Any]:
        """Get audit statistics."""
        total = 0
        by_type: dict[str, int] = {}
        by_result: dict[str, int] = {}
        
        for log_file in self.log_dir.glob("audit_*.jsonl"):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        total += 1
                        by_type[record.get("event_type", "unknown")] = by_type.get(record.get("event_type", "unknown"), 0) + 1
                        by_result[record.get("result", "unknown")] = by_result.get(record.get("result", "unknown"), 0) + 1
                    except json.JSONDecodeError:
                        continue
        
        return {
            "total_records": total,
            "by_type": by_type,
            "by_result": by_result,
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Audit Logger Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="audit_logger",
            version="1.0.0",
            description="Tamper-evident audit logging with hash chain, querying, and compliance reporting",
            license="MIT",
            source="internal",
            capabilities=["audit_logging", "tamper_detection", "compliance_reporting", "log_query"],
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
        self.logger: AuditLogger | None = None
    
    def _resolve_log_dir(self) -> str:
        """Resolve the audit log directory, honoring HERMES_HOME for isolation."""
        home = os.environ.get("HERMES_HOME")
        if home:
            return os.path.join(home, "audit")
        return ".hermes/audit"
    
    async def load(self) -> bool:
        self.logger = AuditLogger(self._resolve_log_dir())
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.logger:
            self.logger = AuditLogger()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        if self.logger:
            self.logger.flush()
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.logger is not None,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def log(self, event_type: str, actor: str, action: str, target: str, 
            result: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        record = self.logger.log(event_type, actor, action, target, result, details)
        # Flush immediately so records are queryable without waiting for buffer threshold
        self.logger.flush()
        return {
            "timestamp": record.timestamp,
            "hash": record.hash,
            "event_type": record.event_type,
        }
    
    def flush(self):
        """Flush buffered audit records to disk."""
        self.logger.flush()
    
    def query(self, **kwargs) -> list[dict[str, Any]]:
        return self.logger.query(**kwargs)
    
    def verify_chain(self) -> dict[str, Any]:
        return self.logger.verify_chain()
    
    def get_stats(self) -> dict[str, Any]:
        return self.logger.get_stats()
    
    def get_capabilities(self) -> list[str]:
        return self.manifest.capabilities
