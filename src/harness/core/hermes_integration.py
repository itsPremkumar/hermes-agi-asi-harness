"""Hermes Agent integration — profiles, kanban, cron, MCP."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProfileConfig:
    """Hermes Agent profile configuration."""
    name: str
    plugins: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class KanbanCard:
    """A kanban card for task tracking."""
    id: str
    title: str
    status: str = "todo"  # todo | in_progress | done
    plugin_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CronJob:
    """A cron job for scheduled plugin execution."""
    id: str
    plugin_id: str
    action: str
    schedule: str = "*/5 * * * *"
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0


@dataclass
class MCPEndpoint:
    """MCP (Model Context Protocol) endpoint."""
    id: str
    plugin_id: str
    transport: str = "stdio"  # stdio | http
    url: str = ""
    enabled: bool = True


class HermesAgentIntegration:
    """Integrates the plugin framework with Hermes Agent."""

    def __init__(self):
        self._lock = threading.RLock()
        self._profiles: dict[str, ProfileConfig] = {}
        self._kanban: dict[str, KanbanCard] = {}
        self._cron_jobs: dict[str, CronJob] = {}
        self._mcp_endpoints: dict[str, MCPEndpoint] = {}

    # ============== Profiles ==============

    def create_profile(self, profile: ProfileConfig) -> str:
        with self._lock:
            self._profiles[profile.name] = profile
            return profile.name

    def get_profile(self, name: str) -> Optional[ProfileConfig]:
        with self._lock:
            return self._profiles.get(name)

    def update_profile(self, name: str, **kwargs) -> bool:
        with self._lock:
            profile = self._profiles.get(name)
            if not profile:
                return False
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            return True

    def delete_profile(self, name: str) -> bool:
        with self._lock:
            return self._profiles.pop(name, None) is not None

    def list_profiles(self) -> list[ProfileConfig]:
        with self._lock:
            return list(self._profiles.values())

    def list_enabled_profiles(self) -> list[ProfileConfig]:
        with self._lock:
            return [p for p in self._profiles.values() if p.enabled]

    # ============== Kanban ==============

    def create_card(self, card: KanbanCard) -> str:
        with self._lock:
            self._kanban[card.id] = card
            return card.id

    def get_card(self, card_id: str) -> Optional[KanbanCard]:
        with self._lock:
            return self._kanban.get(card_id)

    def move_card(self, card_id: str, status: str) -> bool:
        with self._lock:
            card = self._kanban.get(card_id)
            if card:
                card.status = status
                return True
            return False

    def list_cards(self, status: str | None = None) -> list[KanbanCard]:
        with self._lock:
            cards = list(self._kanban.values())
            if status:
                cards = [c for c in cards if c.status == status]
            return cards

    def delete_card(self, card_id: str) -> bool:
        with self._lock:
            return self._kanban.pop(card_id, None) is not None

    # ============== Cron ==============

    def add_cron_job(self, job: CronJob) -> str:
        with self._lock:
            self._cron_jobs[job.id] = job
            return job.id

    def get_cron_job(self, job_id: str) -> Optional[CronJob]:
        with self._lock:
            return self._cron_jobs.get(job_id)

    def enable_cron_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._cron_jobs.get(job_id)
            if job:
                job.enabled = True
                return True
            return False

    def disable_cron_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._cron_jobs.get(job_id)
            if job:
                job.enabled = False
                return True
            return False

    def list_cron_jobs(self, enabled_only: bool = False) -> list[CronJob]:
        with self._lock:
            jobs = list(self._cron_jobs.values())
            if enabled_only:
                jobs = [j for j in jobs if j.enabled]
            return jobs

    def delete_cron_job(self, job_id: str) -> bool:
        with self._lock:
            return self._cron_jobs.pop(job_id, None) is not None

    # ============== MCP ==============

    def register_endpoint(self, endpoint: MCPEndpoint) -> str:
        with self._lock:
            self._mcp_endpoints[endpoint.id] = endpoint
            return endpoint.id

    def get_endpoint(self, endpoint_id: str) -> Optional[MCPEndpoint]:
        with self._lock:
            return self._mcp_endpoints.get(endpoint_id)

    def list_endpoints(self, transport: str | None = None) -> list[MCPEndpoint]:
        with self._lock:
            endpoints = list(self._mcp_endpoints.values())
            if transport:
                endpoints = [e for e in endpoints if e.transport == transport]
            return endpoints

    def delete_endpoint(self, endpoint_id: str) -> bool:
        with self._lock:
            return self._mcp_endpoints.pop(endpoint_id, None) is not None

    # ============== Status ==============

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "profiles": len(self._profiles),
                "kanban_cards": len(self._kanban),
                "cron_jobs": len(self._cron_jobs),
                "mcp_endpoints": len(self._mcp_endpoints),
                "todo_cards": sum(1 for c in self._kanban.values() if c.status == "todo"),
                "in_progress_cards": sum(1 for c in self._kanban.values() if c.status == "in_progress"),
                "done_cards": sum(1 for c in self._kanban.values() if c.status == "done"),
            }


__all__ = [
    "HermesAgentIntegration",
    "ProfileConfig",
    "KanbanCard",
    "CronJob",
    "MCPEndpoint",
]
