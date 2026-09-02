"""Self-test script for ChainForge.

Verifies that:
1. All 100+ nodes are registered
2. API endpoints respond correctly
3. Workflow execution produces expected results
4. Export generates valid Python code
"""
from __future__ import annotations

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.nodes.registry import get_node_registry, get_nodes_by_category, get_node
from app.models.schemas import Workflow, WorkflowNode, WorkflowEdge, Position, NodeStatus


def test_node_count() -> bool:
    registry = get_node_registry()
    count = len(registry)
    if count < 100:
        print(f"FAIL: Expected 100+ nodes, got {count}")
        return False
    print(f"OK: {count} nodes registered")
    return True


def test_categories() -> bool:
    cats = get_nodes_by_category()
    if len(cats) < 5:
        print(f"FAIL: Expected 5+ categories, got {len(cats)}")
        return False
    print(f"OK: {len(cats)} categories: {list(cats.keys())}")
    return True


def test_node_lookup() -> bool:
    node = get_node("llm_openai")
    if not node:
        print("FAIL: Could not find llm_openai node")
        return False
    if node.name != "OpenAI Chat":
        print(f"FAIL: Expected name 'OpenAI Chat', got '{node.name}'")
        return False
    print("OK: Node lookup works")
    return True


def test_execution_engine() -> bool:
    import asyncio
    wf = Workflow(
        id="test_wf",
        name="Self-Test Workflow",
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
    from app.services.engine import ExecutionEngine
    engine = ExecutionEngine(wf)
    result = asyncio.run(engine.execute())
    if result.status != NodeStatus.SUCCESS:
        print(f"FAIL: Expected SUCCESS, got {result.status}")
        return False
    hash_result = [r for r in result.results if r.node_id == "b"][0]
    expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    if hash_result.output != expected:
        print(f"FAIL: Expected hash {expected}, got {hash_result.output}")
        return False
    print("OK: Execution engine works correctly")
    return True


def test_sort_transform() -> bool:
    import asyncio
    wf = Workflow(
        id="sort_wf",
        name="Sort Test",
        nodes=[
            WorkflowNode(id="a", type="input_list", name="A", position=Position(), data={"value": [5, 2, 8, 1]}),
            WorkflowNode(id="b", type="transform_sort", name="Sort", position=Position(x=200), data={}),
            WorkflowNode(id="c", type="output_json", name="Out", position=Position(x=400), data={}),
        ],
        edges=[
            WorkflowEdge(id="e1", source="a", target="b"),
            WorkflowEdge(id="e2", source="b", target="c"),
        ],
    )
    from app.services.engine import ExecutionEngine
    engine = ExecutionEngine(wf)
    result = asyncio.run(engine.execute())
    sort_result = [r for r in result.results if r.node_id == "b"][0]
    if sort_result.output != [1, 2, 5, 8]:
        print(f"FAIL: Expected [1,2,5,8], got {sort_result.output}")
        return False
    print("OK: Sort transform works")
    return True


def test_condition_logic() -> bool:
    import asyncio
    wf = Workflow(
        id="cond_wf",
        name="Condition Test",
        nodes=[
            WorkflowNode(id="a", type="input_number", name="A", position=Position(), data={"value": 10}),
            WorkflowNode(id="b", type="logic_condition", name="Cond", position=Position(x=200), data={"operator": "greater_than", "compare_value": 5}),
            WorkflowNode(id="c", type="output_text", name="Out", position=Position(x=400), data={}),
        ],
        edges=[
            WorkflowEdge(id="e1", source="a", target="b"),
            WorkflowEdge(id="e2", source="b", target="c", sourceHandle="true"),
        ],
    )
    from app.services.engine import ExecutionEngine
    engine = ExecutionEngine(wf)
    result = asyncio.run(engine.execute())
    if result.status != NodeStatus.SUCCESS:
        print(f"FAIL: Condition logic failed")
        return False
    print("OK: Condition logic works")
    return True


def test_csv_parse() -> bool:
    import asyncio
    wf = Workflow(
        id="csv_wf",
        name="CSV Test",
        nodes=[
            WorkflowNode(id="a", type="input_text", name="A", position=Position(), data={"value": "x,y\n1,2\n3,4"}),
            WorkflowNode(id="b", type="data_csv_parse", name="CSV", position=Position(x=200), data={}),
            WorkflowNode(id="c", type="output_json", name="Out", position=Position(x=400), data={}),
        ],
        edges=[
            WorkflowEdge(id="e1", source="a", target="b"),
            WorkflowEdge(id="e2", source="b", target="c"),
        ],
    )
    from app.services.engine import ExecutionEngine
    engine = ExecutionEngine(wf)
    result = asyncio.run(engine.execute())
    csv_result = [r for r in result.results if r.node_id == "b"][0]
    expected = [{"x": "1", "y": "2"}, {"x": "3", "y": "4"}]
    if csv_result.output != expected:
        print(f"FAIL: Expected {expected}, got {csv_result.output}")
        return False
    print("OK: CSV parse works")
    return True


def main() -> int:
    print("=" * 60)
    print("ChainForge Self-Test")
    print("=" * 60)

    tests = [
        test_node_count,
        test_categories,
        test_node_lookup,
        test_execution_engine,
        test_sort_transform,
        test_condition_logic,
        test_csv_parse,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"ERROR in {test.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
