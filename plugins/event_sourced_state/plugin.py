#!/usr/bin/env python3
"""event_sourced_state — PluginBase adapter for event-sourced state store."""

from core.runtime.plugin_base import PluginBase, PluginManifest
from . import EventSourcedStatePlugin


class Plugin(PluginBase):
    def __init__(self):
        self.manifest = PluginManifest(
            name="event_sourced_state",
            version="2.0.0",
            description="Append-only event log with replay, causal debugging, mission reconstruction",
            license="MIT",
            source="internal",
            capabilities=[
                "event.emit",
                "event.replay",
                "event.causal_debug",
                "mission.reconstruct",
                "mission.trace",
                "counterfactual.evaluate",
                "audit.diff",
                "state.snapshot",
            ],
            cost="free",
            permissions=None,
        )
        self._impl = EventSourcedStatePlugin()

    async def load(self) -> bool:
        return await self._impl.load()

    async def start(self) -> bool:
        return await self._impl.start()

    async def stop(self) -> bool:
        return await self._impl.stop()

    async def health(self) -> dict:
        return await self._impl.health()

    async def emit(self, event_type, data=None, **kwargs):
        return await self._impl.emit(event_type, data, **kwargs)

    async def replay(self, **kwargs):
        return await self._impl.replay(**kwargs)

    async def causal_debug(self, event_id):
        return await self._impl.causal_debug(event_id)

    async def reconstruct_mission(self, mission_id):
        return await self._impl.reconstruct_mission(mission_id)

    async def counterfactual(self, **kwargs):
        return await self._impl.counterfactual(**kwargs)

    async def audit_diff(self, **kwargs):
        return await self._impl.audit_diff(**kwargs)
