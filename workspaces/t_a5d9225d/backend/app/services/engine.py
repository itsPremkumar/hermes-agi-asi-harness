"""Workflow execution engine for ChainForge."""
from __future__ import annotations

import asyncio
import time
import traceback
from collections import deque
from typing import Any
from datetime import datetime

from app.models.schemas import (
    Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution,
    ExecutionResult, NodeStatus,
)


class ExecutionEngine:
    """Topological-sort-based workflow execution engine."""

    def __init__(self, workflow: Workflow) -> None:
        self.workflow = workflow
        self.results: dict[str, ExecutionResult] = {}
        self.node_map: dict[str, WorkflowNode] = {n.id: n for n in workflow.nodes}
        self.adj: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        self.in_deg: dict[str, int] = {n.id: 0 for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.source in self.adj and edge.target in self.in_deg:
                self.adj[edge.source].append(edge.target)
                self.in_deg[edge.target] += self.in_deg.get(edge.target, 0) + 1 or 1

    def _get_input_values(self, node: WorkflowNode) -> dict[str, Any]:
        """Collect input values from upstream results."""
        inputs: dict[str, Any] = {}
        for edge in self.workflow.edges:
            if edge.target == node.id and edge.source in self.inputs:
                inputs[edge.source] = self.inputs[edge.source]
        return inputs

    async def execute(self, max_steps: int = 500) -> WorkflowExecution:
        """Execute the workflow and return results."""
        execution = WorkflowExecution(
            id=f"exec_{int(time.time())}",
            workflow_id=self.workflow.id,
        )
        self.inputs: dict[str, Any] = {}
        self.results = {}

        start = time.time()
        queue: deque[str] = deque()
        for nid, deg in self.in_deg.items():
            if deg == 0:
                queue.append(nid)

        steps = 0
        while queue and steps < max_steps:
            nid = queue.popleft()
            steps += 1
            node = self.node_map.get(nid)
            if not node:
                continue

            nstart = time.time()
            self.results[nid] = ExecutionResult(
                node_id=nid,
                status=NodeStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            try:
                inputs = self._get_input_values(node)
                output = await self._run_node(node, inputs)
                self.inputs[nid] = output
                self.results[nid].status = NodeStatus.SUCCESS
                self.results[nid].output = output
            except Exception as e:
                self.results[nid].status = NodeStatus.ERROR
                self.results[nid].error = str(e)
                self.results[nid].output = None

            self.results[nid].completed_at = datetime.utcnow()
            self.results[nid].duration_ms = int((time.time() - nstart) * 1000)

            for child in self.adj.get(nid, []):
                self.in_deg[child] -= 1
                if self.in_deg[child] == 0:
                    queue.append(child)

        execution.results = list(self.results.values())
        execution.completed_at = datetime.utcnow()
        execution.total_duration_ms = int((time.time() - start) * 1000)
        if all(r.status == NodeStatus.SUCCESS for r in execution.results):
            execution.status = NodeStatus.SUCCESS
        elif any(r.status == NodeStatus.ERROR for r in execution.results):
            execution.status = NodeStatus.ERROR
        else:
            execution.status = NodeStatus.SUCCESS
        return execution

    async def _run_node(self, node: WorkflowNode, inputs: dict[str, Any]) -> Any:
        """Run a single node's logic."""
        cfg = node.data or {}
        ntype = node.type

        # --- Input nodes ---
        if ntype.startswith("input_"):
            return cfg.get("value")

        # --- Output nodes ---
        if ntype.startswith("output_"):
            values = list(inputs.values())
            return values[0] if values else None

        # --- LLM nodes ---
        if ntype.startswith("llm_"):
            return {"response": f"[{ntype}] Would call LLM with: {inputs}"}

        # --- Tool nodes ---
        if ntype.startswith("tool_"):
            return {"result": f"[{ntype}] Executed tool with: {inputs}"}

        # --- Logic nodes ---
        if ntype == "logic_condition":
            values = list(inputs.values())
            val = values[0] if values else None
            op = cfg.get("operator", "equals")
            cmp = cfg.get("compare_value")
            if op == "equals":
                return val == cmp
            if op == "not_equals":
                return val != cmp
            if op == "greater_than":
                return (val or 0) > (cmp or 0)
            if op == "less_than":
                return (val or 0) < (cmp or 0)
            return True

        if ntype == "logic_loop":
            values = list(inputs.values())
            items = values[0] if values and isinstance(values[0], list) else []
            return items

        if ntype == "logic_merge":
            values = list(inputs.values())
            return values

        if ntype == "logic_delay":
            dur = cfg.get("duration", 1)
            await asyncio.sleep(min(dur, 2))
            values = list(inputs.values())
            return values[0] if values else None

        if ntype == "logic_parallel":
            values = list(inputs.values())
            return values[0] if values else None

        if ntype == "logic_race":
            values = list(inputs.values())
            return values[0] if values else None

        if ntype == "logic_catch":
            values = list(inputs.values())
            return values[0] if values else None

        if ntype == "logic_batch":
            values = list(inputs.values())
            items = values[0] if values and isinstance(values[0], list) else []
            batch_size = cfg.get("batch_size", 10)
            return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

        # --- Transform nodes ---
        if ntype.startswith("transform_"):
            values = list(inputs.values())
            data = values[0] if values else None
            if ntype == "transform_map":
                items = data if isinstance(data, list) else []
                return [item for item in items]
            if ntype == "transform_filter":
                items = data if isinstance(data, list) else []
                return [item for item in items if item]
            if ntype == "transform_reduce":
                items = data if isinstance(data, list) else []
                acc = 0
                for item in items:
                    acc += float(item) if isinstance(item, (int, float)) else 0
                return acc
            if ntype == "transform_sort":
                items = data if isinstance(data, list) else []
                try:
                    return sorted(items)
                except Exception:
                    return items
            if ntype == "transform_flatten":
                items = data if isinstance(data, list) else []
                flat: list[Any] = []
                for item in items:
                    if isinstance(item, list):
                        flat.extend(item)
                    else:
                        flat.append(item)
                return flat
            if ntype == "transform_unique":
                items = data if isinstance(data, list) else []
                seen: set[Any] = set()
                result: list[Any] = []
                for item in items:
                    key = str(item)
                    if key not in seen:
                        seen.add(key)
                        result.append(item)
                return result
            if ntype == "transform_join":
                items = data if isinstance(data, list) else []
                sep = cfg.get("separator", ", ")
                return sep.join(str(i) for i in items)
            if ntype == "transform_split":
                text = str(data or "")
                sep = cfg.get("separator", ",")
                return [p.strip() for p in text.split(sep)]
            if ntype == "transform_template":
                template = cfg.get("template", "{{data}}")
                return template.replace("{{data}}", str(data))
            if ntype == "transform_json_parse":
                import json
                return json.loads(str(data or "{}"))
            if ntype == "transform_json_stringify":
                import json
                return json.dumps(data)
            if ntype == "transform_regex":
                import re
                text = str(data or "")
                pattern = cfg.get("pattern", "")
                action = cfg.get("action", "match")
                if action == "match":
                    return re.findall(pattern, text)
                if action == "replace":
                    return re.sub(pattern, cfg.get("replacement", ""), text)
                return text
            if ntype == "transform_hash":
                import hashlib
                algo = cfg.get("algorithm", "sha256")
                h = hashlib.new(algo)
                h.update(str(data).encode())
                return h.hexdigest()
            return data

        # --- Data nodes ---
        if ntype.startswith("data_"):
            values = list(inputs.values())
            data = values[0] if values else None
            if ntype == "data_csv_parse":
                import csv, io
                text = str(data or "")
                delimiter = (node.data or {}).get("delimiter", ",")
                reader = csv.reader(io.StringIO(text), delimiter=delimiter)
                rows = list(reader)
                if (node.data or {}).get("header", True) and rows:
                    headers = rows[0]
                    return [dict(zip(headers, row)) for row in rows[1:]]
                return rows
            if ntype == "data_base64_encode":
                import base64
                return base64.b64encode(str(data).encode()).decode()
            if ntype == "data_base64_decode":
                import base64
                return base64.b64decode(str(data)).decode()
            if ntype == "data_url_encode":
                from urllib.parse import quote
                return quote(str(data or ""))
            if ntype == "data_url_decode":
                from urllib.parse import unquote
                return unquote(str(data or ""))
            return data

        # --- Agent nodes ---
        if ntype.startswith("agent_"):
            values = list(inputs.values())
            return {"result": f"[{ntype}] Agent executed with: {values}"}

        # --- RAG / Vision / Audio ---
        if ntype.startswith(("rag_", "vision_", "audio_")):
            return {"result": f"[{ntype}] Node executed"}

        # --- Custom ---
        if ntype == "custom_python":
            code = cfg.get("code", "return input")
            values = list(inputs.values())
            inp = values[0] if values else None
            local_ns: dict[str, Any] = {"input": inp}
            exec(f"def _fn(input):\n    return (lambda: {code})()", local_ns)
            return local_ns["_fn"](inp)

        # --- Default passthrough ---
        values = list(inputs.values())
        return values[0] if values else None
