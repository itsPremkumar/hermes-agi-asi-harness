"""Tests for ChainForge backend."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nodes.registry import get_node_registry, get_nodes_by_category, get_node
from app.models.schemas import Workflow, WorkflowNode, WorkflowEdge, Position, NodeStatus
from app.services.engine import ExecutionEngine


client = TestClient(app)


# --- Node Registry Tests ---

class TestNodeRegistry:
    def test_registry_has_100_nodes(self):
        registry = get_node_registry()
        assert len(registry) >= 100, f"Expected 100+ nodes, got {len(registry)}"

    def test_registry_has_categories(self):
        cats = get_nodes_by_category()
        assert len(cats) >= 5

    def test_get_node(self):
        node = get_node("llm_openai")
        assert node is not None
        assert node.name == "OpenAI Chat"

    def test_get_nonexistent_node(self):
        assert get_node("nonexistent") is None

    def test_all_nodes_have_type(self):
        registry = get_node_registry()
        for ntype, node in registry.items():
            assert node.type == ntype
            assert node.name
            assert node.category


# --- API Tests ---

class TestAPI:
    def test_health(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ChainForge"

    def test_list_nodes(self):
        resp = client.get("/api/v1/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5

    def test_get_node(self):
        resp = client.get("/api/v1/nodes/llm_openai")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "llm_openai"
        assert data["name"] == "OpenAI Chat"
        assert "inputs" in data
        assert "outputs" in data

    def test_get_nonexistent_node(self):
        resp = client.get("/api/v1/nodes/nonexistent")
        assert resp.status_code == 404

    def test_create_workflow(self):
        resp = client.post("/api/v1/workflows", json={"name": "Test Workflow"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Workflow"
        assert "id" in data

    def test_list_workflows(self):
        resp = client.get("/api/v1/workflows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_workflow(self):
        created = client.post("/api/v1/workflows", json={"name": "Get Test"}).json()
        wf_id = created["id"]
        resp = client.get(f"/api/v1/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == wf_id

    def test_get_nonexistent_workflow(self):
        resp = client.get("/api/v1/workflows/nonexistent")
        assert resp.status_code == 404

    def test_update_workflow(self):
        created = client.post("/api/v1/workflows", json={"name": "Update Test"}).json()
        wf_id = created["id"]
        resp = client.put(f"/api/v1/workflows/{wf_id}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_workflow(self):
        created = client.post("/api/v1/workflows", json={"name": "Delete Test"}).json()
        wf_id = created["id"]
        resp = client.delete(f"/api/v1/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_export_python(self):
        created = client.post("/api/v1/workflows", json={"name": "Export Test"}).json()
        wf_id = created["id"]
        resp = client.post("/api/v1/export", json={"workflow_id": wf_id, "format": "python"})
        assert resp.status_code == 200
        assert resp.json()["format"] == "python"
        assert "code" in resp.json()

    def test_deploy(self):
        created = client.post("/api/v1/workflows", json={"name": "Deploy Test"}).json()
        wf_id = created["id"]
        resp = client.post("/api/v1/deploy", json={"workflow_id": wf_id, "target": "docker"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "deployed"

    def test_execute_workflow(self):
        """Test basic workflow execution with input -> output."""
        resp = client.post("/api/v1/workflows", json={"name": "Exec Test"})
        wf_id = resp.json()["id"]
        update_resp = client.put(f"/api/v1/workflows/{wf_id}", json={
            "nodes": [
                {"id": "n1", "type": "input_text", "name": "Start", "position": {"x": 0, "y": 0}, "data": {"value": "hello"}},
                {"id": "n2", "type": "output_text", "name": "End", "position": {"x": 200, "y": 0}, "data": {}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2"},
            ],
        })
        assert update_resp.status_code == 200
        exec_resp = client.post(f"/api/v1/workflows/{wf_id}/execute")
        assert exec_resp.status_code == 200
        data = exec_resp.json()
        assert data["status"] == "success"
        assert len(data["results"]) == 2


# --- Engine Tests ---

class TestEngine:
    def test_simple_execution(self):
        wf = Workflow(
            id="test_wf",
            name="Test",
            nodes=[
                WorkflowNode(id="a", type="input_text", name="A", position=Position(), data={"value": 42}),
                WorkflowNode(id="b", type="output_text", name="B", position=Position(x=200), data={}),
            ],
            edges=[WorkflowEdge(id="e1", source="a", target="b")],
        )
        engine = ExecutionEngine(wf)
        import asyncio
        result = asyncio.run(engine.execute())
        assert result.status == NodeStatus.SUCCESS
        assert len(result.results) == 2

    def test_condition_true(self):
        wf = Workflow(
            id="cond_wf",
            name="Cond",
            nodes=[
                WorkflowNode(id="a", type="input_text", name="A", position=Position(), data={"value": 10}),
                WorkflowNode(id="b", type="logic_condition", name="Cond", position=Position(x=200), data={"operator": "greater_than", "compare_value": 5}),
                WorkflowNode(id="c", type="output_text", name="Out", position=Position(x=400), data={}),
            ],
            edges=[
                WorkflowEdge(id="e1", source="a", target="b"),
                WorkflowEdge(id="e2", source="b", target="c", sourceHandle="true"),
            ],
        )
        engine = ExecutionEngine(wf)
        import asyncio
        result = asyncio.run(engine.execute())
        assert result.status == NodeStatus.SUCCESS

    def test_transform_sort(self):
        wf = Workflow(
            id="sort_wf",
            name="Sort",
            nodes=[
                WorkflowNode(id="a", type="input_list", name="A", position=Position(), data={"value": [3, 1, 2]}),
                WorkflowNode(id="b", type="transform_sort", name="Sort", position=Position(x=200), data={}),
                WorkflowNode(id="c", type="output_json", name="Out", position=Position(x=400), data={}),
            ],
            edges=[
                WorkflowEdge(id="e1", source="a", target="b"),
                WorkflowEdge(id="e2", source="b", target="c"),
            ],
        )
        engine = ExecutionEngine(wf)
        import asyncio
        result = asyncio.run(engine.execute())
        assert result.status == NodeStatus.SUCCESS
        sort_result = [r for r in result.results if r.node_id == "b"][0]
        assert sort_result.output == [1, 2, 3]

    def test_hash_transform(self):
        wf = Workflow(
            id="hash_wf",
            name="Hash",
            nodes=[
                WorkflowNode(id="a", type="input_text", name="A", position=Position(), data={"value": "hello"}),
                WorkflowNode(id="b", type="transform_hash", name="Hash", position=Position(x=200), data={"algorithm": "sha256"}),
                WorkflowNode(id="c", type="output_text", name="Out", position=Position(x=400), data={}),
            ],
            edges=[
                WorkflowEdge(id="e1", source="a", target="b"),
                WorkflowEdge(id="e2", source="b", target="c"),
            ],
        )
        engine = ExecutionEngine(wf)
        import asyncio
        result = asyncio.run(engine.execute())
        assert result.status == NodeStatus.SUCCESS
        hash_result = [r for r in result.results if r.node_id == "b"][0]
        assert hash_result.output == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_csv_parse(self):
        wf = Workflow(
            id="csv_wf",
            name="CSV",
            nodes=[
                WorkflowNode(id="a", type="input_text", name="A", position=Position(), data={"value": "name,age\nAlice,30\nBob,25"}),
                WorkflowNode(id="b", type="data_csv_parse", name="CSV", position=Position(x=200), data={}),
                WorkflowNode(id="c", type="output_json", name="Out", position=Position(x=400), data={}),
            ],
            edges=[
                WorkflowEdge(id="e1", source="a", target="b"),
                WorkflowEdge(id="e2", source="b", target="c"),
            ],
        )
        engine = ExecutionEngine(wf)
        import asyncio
        result = asyncio.run(engine.execute())
        assert result.status == NodeStatus.SUCCESS
        csv_result = [r for r in result.results if r.node_id == "b"][0]
        assert csv_result.output == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
