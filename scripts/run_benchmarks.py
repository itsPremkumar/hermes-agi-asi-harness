"""Run actual benchmark evaluations with sample tasks.

Demonstrates the full pipeline: LLM generates → evaluator runs → score computed.
Replace sample tasks with real benchmark datasets when ready.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path FIRST and remove conflicting paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
# Remove any paths that might conflict (kanban workspaces, etc.)
sys.path = [p for p in sys.path if 'kanban' not in p and 'it-company-ops' not in p]
sys.path.insert(0, str(PROJECT_ROOT))

from core.benchmarks import (
    MultiBenchmarkEngine, BenchmarkType,
    HumanEvalAdapter, MBPPAdapter, GPQAAdapter,
)
from core.benchmarks.llm_client import LLMClient, LLMConfig
from core.benchmarks.evaluator import BenchmarkEvaluator


def create_sample_tasks(data_dir: Path):
    """Create sample benchmark tasks for testing."""
    data_dir.mkdir(parents=True, exist_ok=True)

    # HumanEval tasks
    he_dir = data_dir / "human_eval"
    he_dir.mkdir(exist_ok=True)
    he_tasks = [
        {
            "task_id": "HE-001",
            "prompt": "def add(a, b):\n    \"\"\"Add two numbers.\"\"\"\n",
            "canonical_solution": "def add(a, b):\n    return a + b",
            "test": "def check():\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n    assert add(-1, 1) == 0\n    print('PASS')\n",
            "entry_point": "add",
        },
        {
            "task_id": "HE-002",
            "prompt": "def is_even(n):\n    \"\"\"Check if a number is even.\"\"\"\n",
            "canonical_solution": "def is_even(n):\n    return n % 2 == 0",
            "test": "def check():\n    assert is_even(4) == True\n    assert is_even(3) == False\n    assert is_even(0) == True\n    print('PASS')\n",
            "entry_point": "is_even",
        },
        {
            "task_id": "HE-003",
            "prompt": "def factorial(n):\n    \"\"\"Compute factorial of n.\"\"\"\n",
            "canonical_solution": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
            "test": "def check():\n    assert factorial(0) == 1\n    assert factorial(1) == 1\n    assert factorial(5) == 120\n    print('PASS')\n",
            "entry_point": "factorial",
        },
    ]
    for task in he_tasks:
        (he_dir / f"{task['task_id']}.json").write_text(json.dumps(task))

    # MBPP tasks
    mbpp_dir = data_dir / "mbpp"
    mbpp_dir.mkdir(exist_ok=True)
    mbpp_tasks = [
        {
            "task_id": "MB-001",
            "text": "Write a function that adds two numbers.",
            "code": "def add(a, b):\n    return a + b",
            "test_list": [
                "assert add(1, 2) == 3",
                "assert add(0, 0) == 0",
                "assert add(-1, 1) == 0",
            ],
        },
        {
            "task_id": "MB-002",
            "text": "Write a function that checks if a number is positive.",
            "code": "def is_positive(n):\n    return n > 0",
            "test_list": [
                "assert is_positive(5) == True",
                "assert is_positive(-3) == False",
                "assert is_positive(0) == False",
            ],
        },
    ]
    for task in mbpp_tasks:
        (mbpp_dir / f"{task['task_id']}.json").write_text(json.dumps(task))

    # GAIA tasks
    gaia_dir = data_dir / "gaia"
    gaia_dir.mkdir(exist_ok=True)
    gaia_tasks = [
        {
            "task_id": "GA-001",
            "Question": "What is 2 + 2?",
            "Final answer": "4",
            "Level": 1,
        },
        {
            "task_id": "GA-002",
            "Question": "What is the capital of France?",
            "Final answer": "Paris",
            "Level": 1,
        },
        {
            "task_id": "GA-003",
            "Question": "If a train travels 60 mph for 2 hours, how far does it go?",
            "Final answer": "120 miles",
            "Level": 2,
        },
    ]
    for task in gaia_tasks:
        (gaia_dir / f"{task['task_id']}.json").write_text(json.dumps(task))

    # GPQA tasks
    gpqa_dir = data_dir / "gpqa"
    gpqa_dir.mkdir(exist_ok=True)
    gpqa_tasks = [
        {
            "task_id": "GP-001",
            "question": "What is the SI unit of force?",
            "correct_answer": "A",
            "choices": ["A) Newton", "B) Joule", "C) Watt", "D) Pascal"],
            "correct_index": 0,
            "explanation": "Force is measured in Newtons (N).",
        },
        {
            "task_id": "GP-002",
            "question": "What is the speed of light in vacuum?",
            "correct_answer": "C",
            "choices": ["A) 3x10^6 m/s", "B) 3x10^7 m/s", "C) 3x10^8 m/s", "D) 3x10^9 m/s"],
            "correct_index": 2,
            "explanation": "Speed of light is approximately 3x10^8 m/s.",
        },
    ]
    for task in gpqa_tasks:
        (gpqa_dir / f"{task['task_id']}.json").write_text(json.dumps(task))

    return data_dir


def run_benchmarks():
    """Run all benchmarks and report scores."""
    # Create sample tasks
    data_dir = Path.home() / ".hermes" / "benchmarks"
    create_sample_tasks(data_dir)

    # Create LLM client (connects to Hermes proxy)
    llm_config = LLMConfig(
        base_url="http://127.0.0.1:8645/v1",
        model="meituan/longcat-2.0:free",
        max_tokens=2048,
        temperature=0.7,
    )
    llm = LLMClient(llm_config)

    # Check LLM connection
    print("=" * 60)
    print("HERMES AGI/ASI HARNESS — BENCHMARK EVALUATION")
    print("=" * 60)
    print(f"\nLLM: {llm_config.model}")
    print(f"Proxy: {llm_config.base_url}")
    print(f"Connection: {'OK' if llm.check_connection() else 'FAILED'}")

    if not llm.check_connection():
        print("\nERROR: Cannot connect to Hermes proxy.")
        print("Start it with: hermes proxy start")
        return

    # Create engine
    engine = MultiBenchmarkEngine(verbose=True, llm=llm)
    engine.register_adapter(HumanEvalAdapter(data_dir))
    engine.register_adapter(MBPPAdapter(data_dir))
    engine.register_adapter(GAIAAdapter(data_dir))
    engine.register_adapter(GPQAAdapter(data_dir))

    evaluator = BenchmarkEvaluator()

    results = {}

    # Run HumanEval
    print("\n" + "=" * 60)
    print("HUMAN EVAL")
    print("=" * 60)
    he_result = engine.run_benchmark(BenchmarkType.HUMAN_EVAL)
    results["human_eval"] = he_result
    print(f"\nScore: {he_result.avg_score:.2%} ({he_result.completed_tasks}/{he_result.total_tasks})")

    # Run MBPP
    print("\n" + "=" * 60)
    print("MBPP")
    print("=" * 60)
    mbpp_result = engine.run_benchmark(BenchmarkType.MBPP)
    results["mbpp"] = mbpp_result
    print(f"\nScore: {mbpp_result.avg_score:.2%} ({mbpp_result.completed_tasks}/{mbpp_result.total_tasks})")

    # Run GAIA
    print("\n" + "=" * 60)
    print("GAIA")
    print("=" * 60)
    gaia_result = engine.run_benchmark(BenchmarkType.GAIA)
    results["gaia"] = gaia_result
    print(f"\nScore: {gaia_result.avg_score:.2%} ({gaia_result.completed_tasks}/{gaia_result.total_tasks})")

    # Run GPQA
    print("\n" + "=" * 60)
    print("GPQA")
    print("=" * 60)
    gpqa_result = engine.run_benchmark(BenchmarkType.GPQA)
    results["gpqa"] = gpqa_result
    print(f"\nScore: {gpqa_result.avg_score:.2%} ({gpqa_result.completed_tasks}/{gpqa_result.total_tasks})")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in results.items():
        print(f"  {name:20s}: {result.avg_score:6.2%} ({result.completed_tasks}/{result.total_tasks})")

    return results


if __name__ == "__main__":
    run_benchmarks()
