"""Persistent State Store package — re-exports from persistent_state module."""
import json
import os
import shutil
import tempfile
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class StateFile(str, Enum):
    WORLD_STATE = "world_state.json"
    SELF_MODEL = "self_model.json"
    BELIEF_GRAPH = "belief_graph.json"
    MISSION_GRAPH = "mission_graph.json"
    FINANCIAL_LEDGER = "financial_ledger.json"
    EVOLUTION_BENCHMARKS = "evolution_benchmarks.json"
    ACTIVE_TASKS = "active_tasks.json"
    CAPABILITY_REGISTRY = "capability_registry.json"
    TOOL_REGISTRY = "tool_registry.json"
    AGENT_REGISTRY = "agent_registry.json"
    HEALTH_STATE = "health_state.json"

    def __str__(self):
        return self.value


class StateValidationError(Exception):
    pass


class PersistentStateStore:
    """Atomic state store with read-validate-modify-validate-write-backup."""

    DEFAULT_STATES = {
        StateFile.WORLD_STATE: {"entities": [], "relations": [], "updated_at": None},
        StateFile.SELF_MODEL: {"capabilities": {}, "limitations": [], "updated_at": None},
        StateFile.BELIEF_GRAPH: {"nodes": [], "edges": [], "updated_at": None},
        StateFile.MISSION_GRAPH: {"nodes": [], "edges": [], "active_missions": [], "updated_at": None},
        StateFile.FINANCIAL_LEDGER: {"token_costs": [], "api_costs": [], "compute_costs": [], "total": 0.0, "updated_at": None},
        StateFile.EVOLUTION_BENCHMARKS: {"experiments": [], "baseline": {}, "updated_at": None},
        StateFile.ACTIVE_TASKS: {"tasks": [], "updated_at": None},
        StateFile.CAPABILITY_REGISTRY: {"capabilities": {}, "updated_at": None},
        StateFile.TOOL_REGISTRY: {"tools": {}, "updated_at": None},
        StateFile.AGENT_REGISTRY: {"agents": {}, "updated_at": None},
        StateFile.HEALTH_STATE: {"plugins": {}, "overall": "unknown", "updated_at": None},
    }

    def __init__(self, state_dir: str | None = None):
        self.state_dir = Path(state_dir or os.environ.get("HERMES_STATE_DIR", "state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, bool] = {}
        self._init_state_files()

    def _init_state_files(self):
        for state_file, default_data in self.DEFAULT_STATES.items():
            filepath = self.state_dir / state_file
            if not filepath.exists():
                self._write_atomic(state_file, default_data, skip_backup=True)

    def _write_atomic(self, state_file: StateFile, data: dict[str, Any], skip_backup: bool = False) -> dict[str, Any]:
        self._validate_state(state_file, data)

        filepath = self.state_dir / state_file
        data["updated_at"] = time.time()

        if not skip_backup and filepath.exists():
            backup_path = self.state_dir / f".{state_file}.bak"
            shutil.copy2(filepath, backup_path)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', dir=self.state_dir, delete=False) as f:
            json.dump(data, f, indent=2, default=str)
            temp_path = f.name

        os.replace(temp_path, filepath)
        return data

    def _validate_state(self, state_file: StateFile, data: dict[str, Any]) -> None:
        required_keys = {
            StateFile.WORLD_STATE: ["entities", "relations"],
            StateFile.SELF_MODEL: ["capabilities"],
            StateFile.MISSION_GRAPH: ["nodes", "edges", "active_missions"],
            StateFile.FINANCIAL_LEDGER: ["token_costs", "total"],
            StateFile.ACTIVE_TASKS: ["tasks"],
            StateFile.CAPABILITY_REGISTRY: ["capabilities"],
            StateFile.TOOL_REGISTRY: ["tools"],
            StateFile.AGENT_REGISTRY: ["agents"],
            StateFile.HEALTH_STATE: ["plugins", "overall"],
        }

        key = StateFile(state_file)
        if key in required_keys:
            for req_key in required_keys[key]:
                if req_key not in data:
                    raise StateValidationError(f"State file {state_file} missing required key: {req_key}")

    def read(self, state_file: StateFile) -> dict[str, Any]:
        filepath = self.state_dir / state_file
        if not filepath.exists():
            return self.DEFAULT_STATES[state_file].copy()
        with open(filepath, 'r') as f:
            return json.load(f)

    def read_modify_write(self, state_file: StateFile, modifier) -> dict[str, Any]:
        data = self.read(state_file)
        modified = modifier(data)
        return self._write_atomic(state_file, modified)

    def update_entity(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            entities = state.get("entities", [])
            found = False
            for i, entity in enumerate(entities):
                if entity.get("id") == entity_id:
                    entity.update(data)
                    entities[i]["updated_at"] = time.time()
                    found = True
                    break
            if not found:
                entities.append({"id": entity_id, **data, "created_at": time.time(), "updated_at": time.time()})
            state["entities"] = entities
            return state
        return self.read_modify_write(StateFile.WORLD_STATE, modifier)

    def add_mission(self, mission: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            nodes = state.get("nodes", [])
            active = state.get("active_missions", [])
            mission_id = mission.get("id", f"mission-{len(nodes)}")
            mission["id"] = mission_id
            mission["created_at"] = time.time()
            mission["status"] = "active"
            nodes.append(mission)
            active.append(mission_id)
            state["nodes"] = nodes
            state["active_missions"] = active
            return state
        return self.read_modify_write(StateFile.MISSION_GRAPH, modifier)

    def add_task(self, task: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            tasks = state.get("tasks", [])
            task["created_at"] = time.time()
            task["status"] = task.get("status", "pending")
            tasks.append(task)
            state["tasks"] = tasks
            return state
        return self.read_modify_write(StateFile.ACTIVE_TASKS, modifier)

    def update_task_status(self, task_id: str, status: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            tasks = state.get("tasks", [])
            for task in tasks:
                if task.get("id") == task_id:
                    task["status"] = status
                    task["updated_at"] = time.time()
                    if result:
                        task["result"] = result
                    break
            state["tasks"] = tasks
            return state
        return self.read_modify_write(StateFile.ACTIVE_TASKS, modifier)

    def record_token_cost(self, model: str, tokens: int, cost: float) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            entry = {"model": model, "tokens": tokens, "cost": cost, "timestamp": time.time()}
            state["token_costs"].append(entry)
            state["total"] = state.get("total", 0.0) + cost
            state["updated_at"] = time.time()
            return state
        return self.read_modify_write(StateFile.FINANCIAL_LEDGER, modifier)

    def update_capability(self, capability_name: str, data: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            caps = state.get("capabilities", {})
            caps[capability_name] = {**data, "updated_at": time.time()}
            state["capabilities"] = caps
            return state
        return self.read_modify_write(StateFile.CAPABILITY_REGISTRY, modifier)

    def get_capability(self, capability_name: str) -> dict[str, Any] | None:
        state = self.read(StateFile.CAPABILITY_REGISTRY)
        return state.get("capabilities", {}).get(capability_name)

    def update_tool_registration(self, tool_name: str, data: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            tools = state.get("tools", {})
            tools[tool_name] = {**data, "updated_at": time.time()}
            state["tools"] = tools
            return state
        return self.read_modify_write(StateFile.TOOL_REGISTRY, modifier)

    def update_agent_registration(self, agent_name: str, data: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            agents = state.get("agents", {})
            agents[agent_name] = {**data, "updated_at": time.time()}
            state["agents"] = agents
            return state
        return self.read_modify_write(StateFile.AGENT_REGISTRY, modifier)

    def update_health(self, plugin_name: str, health_data: dict[str, Any]) -> dict[str, Any]:
        def modifier(state: dict[str, Any]) -> dict[str, Any]:
            plugins = state.get("plugins", {})
            plugins[plugin_name] = {**health_data, "updated_at": time.time()}
            state["plugins"] = plugins
            state["updated_at"] = time.time()
            all_healthy = all(p.get("status") == "healthy" for p in plugins.values())
            state["overall"] = "healthy" if all_healthy else "degraded"
            return state
        return self.read_modify_write(StateFile.HEALTH_STATE, modifier)

    def get_all_state_files(self) -> list[str]:
        return [f.value for f in StateFile]

    def get_state_summary(self) -> dict[str, Any]:
        return {
            "state_dir": str(self.state_dir),
            "files": {f.value: (self.state_dir / f.value).exists() for f in StateFile},
            "sizes": {f.value: (self.state_dir / f.value).stat().st_size for f in StateFile if (self.state_dir / f.value).exists()},
        }


async def create(kernel=None):
    """Async factory — creates the persistent state store."""
    state_dir = None
    if kernel:
        state_dir = os.path.join(kernel._state_dir, "state")
    return PersistentStateStore(state_dir)
