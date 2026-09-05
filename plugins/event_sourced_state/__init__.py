#!/usr/bin/env python3
"""Event-Sourced State Plugin v7 §80"""

import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("hermes.event_sourced_state")


@dataclass(frozen=True)
class Event:
    event_type: str
    data: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "system"
    mission_id: str = None
    task_id: str = None
    agent_id: str = None
    parent_event_id: str = None
    correlation_id: str = None
    tags: list = field(default_factory=list)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "parent_event_id": self.parent_event_id,
            "correlation_id": self.correlation_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            event_type=d["event_type"],
            data=d.get("data", {}),
            event_id=d.get("event_id", str(uuid.uuid4())),
            timestamp=d.get("timestamp", time.time()),
            source=d.get("source", "system"),
            mission_id=d.get("mission_id"),
            task_id=d.get("task_id"),
            agent_id=d.get("agent_id"),
            parent_event_id=d.get("parent_event_id"),
            correlation_id=d.get("correlation_id"),
            tags=d.get("tags", []),
        )


@dataclass
class CausalEdge:
    cause_id: str
    effect_id: str
    relation: str = "triggers"
    strength: float = 0.5


class CausalGraph:
    def __init__(self):
        self._edges = []
        self._children = defaultdict(list)
        self._parents = defaultdict(list)

    def add_edge(self, cause_id, effect_id, relation="triggers", strength=0.5):
        edge = CausalEdge(cause_id=cause_id, effect_id=effect_id, relation=relation, strength=strength)
        self._edges.append(edge)
        self._children[cause_id].append(effect_id)
        self._parents[effect_id].append(cause_id)
        return edge

    def ancestors(self, event_id, max_depth=10):
        visited = set()
        frontier = [event_id]
        depth = 0
        while frontier and depth < max_depth:
            nf = []
            for eid in frontier:
                for pid in self._parents.get(eid, []):
                    if pid not in visited:
                        visited.add(pid)
                        nf.append(pid)
            frontier = nf
            depth += 1
        return list(visited)

    def descendants(self, event_id, max_depth=10):
        visited = set()
        frontier = [event_id]
        depth = 0
        while frontier and depth < max_depth:
            nf = []
            for eid in frontier:
                for cid in self._children.get(eid, []):
                    if cid not in visited:
                        visited.add(cid)
                        nf.append(cid)
            frontier = nf
            depth += 1
        return list(visited)

    def causal_chain(self, from_id, to_id):
        if from_id == to_id:
            return [from_id]
        visited = {from_id}
        queue = [(from_id, [from_id])]
        while queue:
            current, path = queue.pop(0)
            for child in self._children.get(current, []):
                if child == to_id:
                    return path + [child]
                if child not in visited:
                    visited.add(child)
                    queue.append((child, path + [child]))
        return []

    def root_cause_analysis(self, event_id):
        ancestors = self.ancestors(event_id)
        roots = [eid for eid in ancestors if not self._parents.get(eid)]
        return [{"event_id": eid, "depth": self._depth(eid, event_id)} for eid in roots]

    def _depth(self, start, target):
        if start == target:
            return 0
        visited = {start}
        queue = [(start, 0)]
        while queue:
            current, d = queue.pop(0)
            for child in self._children.get(current, []):
                if child == target:
                    return d + 1
                if child not in visited:
                    visited.add(child)
                    queue.append((child, d + 1))
        return -1

    def get_stats(self):
        return {"total_edges": len(self._edges), "nodes_with_children": len(self._children), "nodes_with_parents": len(self._parents)}


@dataclass
class Snapshot:
    snapshot_id: str
    event_index: int
    state: dict
    timestamp: float = field(default_factory=time.time)
    mission_id: str = None

    def to_dict(self):
        return {"snapshot_id": self.snapshot_id, "event_index": self.event_index, "state": self.state, "timestamp": self.timestamp, "mission_id": self.mission_id}


class EventStore:
    def __init__(self, state_dir=None, snapshot_interval=100):
        self._events = []
        self._state = {}
        self._reducers = {}
        self._causal = CausalGraph()
        self._missions = defaultdict(list)
        self._snapshots = []
        self._snapshot_interval = snapshot_interval
        self._state_dir = Path(state_dir) if state_dir else Path("state/events")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._event_log_file = self._state_dir / "event_log.jsonl"
        self._snapshot_file = self._state_dir / "snapshots.jsonl"
        self._load_persistent()

    def _load_persistent(self):
        if self._event_log_file.exists():
            try:
                with open(self._event_log_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._events.append(Event.from_dict(json.loads(line)))
                logger.info("Loaded %d events from disk", len(self._events))
            except Exception as e:
                logger.error("Failed to load event log: %s", e)
        if self._snapshot_file.exists():
            try:
                with open(self._snapshot_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            sd = json.loads(line)
                            snap = Snapshot(snapshot_id=sd["snapshot_id"], event_index=sd["event_index"], state=sd["state"], timestamp=sd.get("timestamp", 0), mission_id=sd.get("mission_id"))
                            self._snapshots.append(snap)
                logger.info("Loaded %d snapshots from disk", len(self._snapshots))
            except Exception as e:
                logger.error("Failed to load snapshots: %s", e)
        for evt in self._events:
            if evt.parent_event_id:
                self._causal.add_edge(evt.parent_event_id, evt.event_id, "triggers")
            if evt.mission_id:
                self._missions[evt.mission_id].append(evt.event_id)

    def _persist_event(self, event):
        try:
            with open(self._event_log_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error("Failed to persist event: %s", e)

    def _persist_snapshot(self, snapshot):
        try:
            with open(self._snapshot_file, "a") as f:
                f.write(json.dumps(snapshot.to_dict()) + "\n")
        except Exception as e:
            logger.error("Failed to persist snapshot: %s", e)

    def register_reducer(self, event_type, reducer):
        self._reducers[event_type] = reducer

    def emit(self, event_type, data=None, **kwargs):
        event = Event(event_type=event_type, data=data or {}, **kwargs)
        self._events.append(event)
        if event_type in self._reducers:
            try:
                self._state = self._reducers[event_type](self._state, event)
            except Exception as e:
                logger.error("Reducer error for %s: %s", event_type, e)
        if event.parent_event_id:
            self._causal.add_edge(event.parent_event_id, event.event_id, "triggers")
        if event.mission_id:
            self._missions[event.mission_id].append(event.event_id)
        self._persist_event(event)
        if len(self._events) % self._snapshot_interval == 0:
            self._take_snapshot(event.mission_id)
        return event

    def _take_snapshot(self, mission_id=None):
        snap = Snapshot(snapshot_id="snap-%d-%s" % (len(self._events), uuid.uuid4().hex[:6]), event_index=len(self._events), state=dict(self._state), mission_id=mission_id)
        self._snapshots.append(snap)
        self._persist_snapshot(snap)

    def get_events(self, event_type=None, mission_id=None, task_id=None, agent_id=None, source=None, since=None, until=None, tags=None, limit=100, offset=0):
        results = self._events
        if event_type: results = [e for e in results if e.event_type == event_type]
        if mission_id: results = [e for e in results if e.mission_id == mission_id]
        if task_id: results = [e for e in results if e.task_id == task_id]
        if agent_id: results = [e for e in results if e.agent_id == agent_id]
        if source: results = [e for e in results if e.source == source]
        if since is not None: results = [e for e in results if e.timestamp >= since]
        if until is not None: results = [e for e in results if e.timestamp <= until]
        if tags:
            for tag in tags: results = [e for e in results if tag in e.tags]
        return results[offset:offset + limit]

    def get_event(self, event_id):
        for e in self._events:
            if e.event_id == event_id: return e
        return None

    def replay(self, event_type=None, mission_id=None, from_index=0, to_index=None):
        events = self._events[from_index:to_index]
        if event_type: events = [e for e in events if e.event_type == event_type]
        if mission_id: events = [e for e in events if e.mission_id == mission_id]
        return events

    def replay_from_snapshot(self, snapshot_id=None, mission_id=None):
        snap = None
        if snapshot_id:
            for s in reversed(self._snapshots):
                if s.snapshot_id == snapshot_id: snap = s; break
        elif mission_id:
            for s in reversed(self._snapshots):
                if s.mission_id == mission_id: snap = s; break
        else:
            snap = self._snapshots[-1] if self._snapshots else None
        start_idx = snap.event_index if snap else 0
        initial_state = dict(snap.state) if snap else {}
        return initial_state, self._events[start_idx:]

    def causal_debug(self, event_id):
        event = self.get_event(event_id)
        if not event: return {"error": "Event %s not found" % event_id}
        ancestors = self._causal.ancestors(event_id)
        descendants = self._causal.descendants(event_id)
        roots = self._causal.root_cause_analysis(event_id)
        related = []
        if event.correlation_id:
            related = [e for e in self._events if e.correlation_id == event.correlation_id and e.event_id != event_id]
        return {"target_event": event.to_dict(), "ancestor_count": len(ancestors), "descendant_count": len(descendants), "ancestors": ancestors, "descendants": descendants, "root_causes": roots, "related_by_correlation": [e.event_id for e in related], "causal_stats": self._causal.get_stats()}

    def causal_trace(self, mission_id):
        mission_events = self.get_events(mission_id=mission_id)
        if not mission_events: return []
        trace = []
        for evt in mission_events:
            trace.append({"event_id": evt.event_id, "event_type": evt.event_type, "timestamp": evt.timestamp, "ancestors": len(self._causal.ancestors(evt.event_id)), "descendants": len(self._causal.descendants(evt.event_id)), "parent": evt.parent_event_id})
        return trace

    def reconstruct_mission(self, mission_id):
        mission_events = self.get_events(mission_id=mission_id)
        if not mission_events: return {"mission_id": mission_id, "error": "No events found"}
        mission_state = {}
        for evt in mission_events:
            if evt.event_type in self._reducers:
                try: mission_state = self._reducers[evt.event_type](mission_state, evt)
                except Exception: pass
        causal_chain = []
        last_event_id = None
        for evt in mission_events:
            if last_event_id:
                chain = self._causal.causal_chain(last_event_id, evt.event_id)
                if chain: causal_chain.extend(chain)
            last_event_id = evt.event_id
        seen = set(); unique_chain = []
        for eid in causal_chain:
            if eid not in seen: seen.add(eid); unique_chain.append(eid)
        return {"mission_id": mission_id, "event_count": len(mission_events), "first_event": mission_events[0].event_id, "last_event": mission_events[-1].event_id, "duration": mission_events[-1].timestamp - mission_events[0].timestamp, "event_types": list({e.event_type for e in mission_events}), "agents_involved": list({e.agent_id for e in mission_events if e.agent_id}), "causal_chain": unique_chain, "reconstructed_state": mission_state}

    def reconstruct_all_missions(self):
        return {mid: self.reconstruct_mission(mid) for mid in self._missions}

    def counterfactual(self, remove_event_id=None, inject_event=None, mission_id=None):
        baseline_state = dict(self._state)
        removed_state = {}
        if remove_event_id:
            removed_events = [e for e in self._events if e.event_id != remove_event_id]
            for evt in removed_events:
                if evt.event_type in self._reducers:
                    try: removed_state = self._reducers[evt.event_type](removed_state, evt)
                    except Exception: pass
        injected_state = dict(self._state)
        if inject_event:
            if inject_event.event_type in self._reducers:
                try: injected_state = self._reducers[inject_event.event_type](injected_state, inject_event)
                except Exception: pass
        return {"baseline_state": baseline_state, "without_event": removed_state if remove_event_id else None, "with_injection": injected_state if inject_event else None, "diff_remove": self._diff_states(baseline_state, removed_state) if remove_event_id else None, "diff_inject": self._diff_states(baseline_state, injected_state) if inject_event else None}

    @staticmethod
    def _diff_states(before, after):
        diff = {"added": {}, "removed": {}, "changed": {}}
        all_keys = set(before.keys()) | set(after.keys())
        for key in all_keys:
            bv = before.get(key); av = after.get(key)
            if bv == av: continue
            if key not in before: diff["added"][key] = av
            elif key not in after: diff["removed"][key] = bv
            else: diff["changed"][key] = {"before": bv, "after": av}
        return diff

    def audit_diff(self, from_time=None, to_time=None, from_index=None, to_index=None):
        events = self._events
        if from_index is not None: from_events = events[:from_index]
        elif from_time is not None: from_events = [e for e in events if e.timestamp <= from_time]
        else: from_events = []
        if to_index is not None: to_events = events[:to_index]
        elif to_time is not None: to_events = [e for e in events if e.timestamp <= to_time]
        else: to_events = events
        from_state = {}
        for evt in from_events:
            if evt.event_type in self._reducers:
                try: from_state = self._reducers[evt.event_type](from_state, evt)
                except Exception: pass
        to_state = {}
        for evt in to_events:
            if evt.event_type in self._reducers:
                try: to_state = self._reducers[evt.event_type](to_state, evt)
                except Exception: pass
        return {"from_index": len(from_events), "to_index": len(to_events), "from_state": from_state, "to_state": to_state, "diff": self._diff_states(from_state, to_state)}

    def take_snapshot(self, mission_id=None):
        snap = Snapshot(snapshot_id="snap-manual-%s" % uuid.uuid4().hex[:6], event_index=len(self._events), state=dict(self._state), mission_id=mission_id)
        self._snapshots.append(snap)
        self._persist_snapshot(snap)
        return snap

    def list_snapshots(self, mission_id=None):
        if mission_id: return [s for s in self._snapshots if s.mission_id == mission_id]
        return list(self._snapshots)

    def get_stats(self):
        return {"total_events": len(self._events), "state_keys": len(self._state), "registered_reducers": len(self._reducers), "missions": len(self._missions), "snapshots": len(self._snapshots), "causal_edges": len(self._causal._edges), "log_file": str(self._event_log_file), "snapshot_file": str(self._snapshot_file)}


class EventSourcedStatePlugin:
    def __init__(self, state_dir=None, snapshot_interval=100):
        self.store = EventStore(state_dir=state_dir, snapshot_interval=snapshot_interval)
        self._kernel = None

    async def load(self):
        logger.info("EventSourcedStatePlugin loaded")
        return True

    async def start(self):
        logger.info("EventSourcedStatePlugin started")
        return True

    async def stop(self):
        logger.info("EventSourcedStatePlugin stopped")
        return True

    async def health(self):
        return {"status": "healthy", "type": "event_sourced_state", **self.store.get_stats()}

    async def emit(self, event_type, data=None, **kwargs):
        return self.store.emit(event_type, data or {}, **kwargs)

    async def replay(self, **kwargs):
        return self.store.replay(**kwargs)

    async def causal_debug(self, event_id):
        return self.store.causal_debug(event_id)

    async def reconstruct_mission(self, mission_id):
        return self.store.reconstruct_mission(mission_id)

    async def counterfactual(self, **kwargs):
        return self.store.counterfactual(**kwargs)

    async def audit_diff(self, **kwargs):
        return self.store.audit_diff(**kwargs)


async def create(kernel=None):
    plugin = EventSourcedStatePlugin()
    if kernel: plugin._kernel = kernel
    return plugin