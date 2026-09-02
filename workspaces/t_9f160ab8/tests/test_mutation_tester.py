"""Tests for mutation_tester.py — 8 tests."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testing.mutation_tester import (
    MutationType,
    mutate,
    run_mutation_test,
)


def test_mutate_replace_operator():
    """Test replace_operator mutation."""
    source = "def add(a, b): return a + b"
    mutated = mutate(source, "replace_operator")
    assert mutated != source, "Mutation should change the code"
    assert "+" not in mutated or "-" in mutated, "Operator should be replaced"


def test_mutate_replace_constant():
    """Test replace_constant mutation."""
    source = "x = 5"
    mutated = mutate(source, "replace_constant")
    assert mutated != source, "Mutation should change the code"
    assert "6" in mutated, "Constant should be incremented"


def test_mutate_swap_arguments():
    """Test swap_arguments mutation."""
    source = "x = a + b"
    mutated = mutate(source, "swap_arguments")
    assert mutated != source, "Mutation should change the code"


def test_mutate_negate_condition():
    """Test negate_condition mutation."""
    source = "if x > 0: pass"
    mutated = mutate(source, "negate_condition")
    assert mutated != source, "Mutation should change the code"


def test_mutate_replace_return():
    """Test replace_return mutation."""
    source = "def foo(): return 42"
    mutated = mutate(source, "replace_return")
    assert "None" in mutated, "Return should be replaced with None"


def test_mutate_invert_increment():
    """Test invert_increment mutation."""
    source = "x += 1"
    mutated = mutate(source, "invert_increment")
    assert "-=" in mutated, "Increment should be inverted"


def test_run_mutation_test_kills_mutations():
    """Test that run_mutation_test catches mutations."""
    source = "def add(a, b): return a + b"
    # Test code that will fail when + is mutated to -
    test_code = "if add(1, 2) != 3: raise ValueError('test failed')"
    report = run_mutation_test(source, test_code, mutations=["replace_operator"])
    assert report.total > 0, "Should have at least one result"
    assert report.killed > 0, f"Should have killed at least one mutation, got: {report.results}"


def test_run_mutation_test_all_mutations():
    """Test that all mutation types run without errors."""
    source = "def multiply(x, y): return x * y"
    test_code = "def test_multiply(): assert multiply(2, 3) == 6"
    mutations = [
        "replace_operator",
        "replace_constant",
        "swap_arguments",
        "replace_return",
    ]
    report = run_mutation_test(source, test_code, mutations=mutations)
    assert report.total == len(mutations), f"Expected {len(mutations)} results, got {report.total}"
    assert report.mutation_score >= 0, "Mutation score should be non-negative"



