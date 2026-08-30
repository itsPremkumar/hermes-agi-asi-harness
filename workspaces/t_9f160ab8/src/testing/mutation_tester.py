"""Mutation tester — mutate source code and verify tests catch the mutations.

Usage:
    from testing.mutation_tester import mutate, run_mutation_test
    
    # Mutate a function and run its tests
    result = run_mutation_test(
        source_code="def add(a, b): return a + b",
        test_code="def test_add(): assert add(1, 2) == 3",
        mutations=["replace_operator", "replace_constant"]
    )
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class MutationType(str, Enum):
    """Types of mutations to apply."""
    REPLACE_OPERATOR = "replace_operator"
    REPLACE_CONSTANT = "replace_constant"
    REMOVE_STATEMENT = "remove_statement"
    SWAP_ARGUMENTS = "swap_arguments"
    NEGATE_CONDITION = "negate_condition"
    REMOVE_DEFAULT_ARG = "remove_default_arg"
    REPLACE_RETURN = "replace_return"
    INVERT_INCREMENT = "invert_increment"


@dataclass
class MutationResult:
    """Result of a single mutation test."""
    mutation_type: str
    mutated_code: str
    killed: bool  # True if the test caught the mutation
    error: str | None = None


@dataclass
class MutationReport:
    """Report for a full mutation testing run."""
    source_code: str
    test_code: str
    results: list[MutationResult] = field(default_factory=list)
    
    @property
    def total(self) -> int:
        return len(self.results)
    
    @property
    def killed(self) -> int:
        return sum(1 for r in self.results if r.killed)
    
    @property
    def survived(self) -> int:
        return sum(1 for r in self.results if not r.killed)
    
    @property
    def mutation_score(self) -> float:
        return (self.killed / self.total * 100) if self.total > 0 else 0.0


def _get_operators() -> dict[str, str]:
    """Return mapping of operators to their mutations."""
    return {
        "+": "-",
        "-": "+",
        "*": "/",
        "/": "*",
        "==": "!=",
        "!=": "==",
        ">": "<",
        "<": ">",
        ">=": "<=",
        "<=": ">=",
        "and": "or",
        "or": "and",
    }


def replace_operator(source: str) -> str:
    """Replace arithmetic/comparison operators with alternatives."""
    operators = _get_operators()
    result = source
    for op, replacement in operators.items():
        if op in result:
            result = result.replace(op, replacement, 1)
            break
    return result


def replace_constant(source: str) -> str:
    """Replace numeric constants with different values."""
    result = re.sub(r'(\d+)', lambda m: str(int(m.group(1)) + 1), source, count=1)
    return result


def remove_statement(source: str) -> str:
    """Remove the first non-trivial statement."""
    lines = source.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('def ') and not stripped.startswith('class ') and not stripped.startswith('import ') and not stripped.startswith('from '):
            lines[i] = ''
            break
    return '\n'.join(lines)


def swap_arguments(source: str) -> str:
    """Swap function arguments (for binary operations)."""
    result = re.sub(r'(\w+)\s*(\+|-|\*|/)\s*(\w+)', r'\3 \2 \1', source, count=1)
    return result


def negate_condition(source: str) -> str:
    """Negate the first condition found."""
    result = source.replace('if not ', 'if ', 1)
    if result == source:
        result = source.replace('if ', 'if not ', 1)
    return result


def remove_default_arg(source: str) -> str:
    """Remove a default argument value."""
    result = re.sub(r'(\w+)=(\w+)', r'\1', source, count=1)
    return result


def replace_return(source: str) -> str:
    """Replace return value with None or 0."""
    result = re.sub(r'return\s+\w+', 'return None', source, count=1)
    return result


def invert_increment(source: str) -> str:
    """Invert increment/decrement operations."""
    result = source.replace('+= 1', '-= 1', 1)
    if result == source:
        result = source.replace('-= 1', '+= 1', 1)
    return result


# Map mutation types to functions
MUTATION_FUNCS: dict[str, Callable[[str], str]] = {
    "replace_operator": replace_operator,
    "replace_constant": replace_constant,
    "remove_statement": remove_statement,
    "swap_arguments": swap_arguments,
    "negate_condition": negate_condition,
    "remove_default_arg": remove_default_arg,
    "replace_return": replace_return,
    "invert_increment": invert_increment,
}


def mutate(source_code: str, mutation_type: str) -> str:
    """Apply a single mutation to source code.
    
    Args:
        source_code: Python source code string
        mutation_type: Type of mutation to apply
        
    Returns:
        Mutated source code
    """
    if mutation_type not in MUTATION_FUNCS:
        raise ValueError(f"Unknown mutation type: {mutation_type}")
    
    return MUTATION_FUNCS[mutation_type](source_code)


def run_mutation_test(
    source_code: str,
    test_code: str,
    mutations: list[str] | None = None,
) -> MutationReport:
    """Run mutation testing on source code.
    
    Args:
        source_code: Python source code to mutate
        test_code: Test code that should catch mutations
        mutations: List of mutation types to apply (default: all)
        
    Returns:
        MutationReport with results for each mutation
    """
    if mutations is None:
        mutations = list(MUTATION_FUNCS.keys())
    
    report = MutationReport(source_code=source_code, test_code=test_code)
    
    for mut_type in mutations:
        try:
            mutated = mutate(source_code, mut_type)
            killed = _test_mutation(source_code, mutated, test_code)
            report.results.append(MutationResult(
                mutation_type=mut_type,
                mutated_code=mutated,
                killed=killed,
            ))
        except Exception as e:
            report.results.append(MutationResult(
                mutation_type=mut_type,
                mutated_code=source_code,
                killed=False,
                error=str(e),
            ))
    
    return report


def _test_mutation(original_code: str, mutated_code: str, test_code: str) -> bool:
    """Run test code against original and mutated source.
    
    Returns:
        True if the mutation was killed (test fails on mutated code)
    """
    original_passes = _run_code(original_code, test_code)
    mutated_passes = _run_code(mutated_code, test_code)
    
    # Mutation is killed if:
    # 1. Original passes AND mutated fails
    if original_passes and not mutated_passes:
        return True
    
    # 2. Both pass but outputs differ (subtle mutation)
    if original_passes and mutated_passes:
        orig_result = _exec_with_result(original_code, test_code)
        mut_result = _exec_with_result(mutated_code, test_code)
        if orig_result != mut_result:
            return True
    
    return False


def _run_code(source_code: str, test_code: str) -> bool:
    """Execute source + test code and return True if tests pass."""
    namespace: dict[str, Any] = {}
    try:
        exec(source_code, namespace)
        exec(test_code, namespace)
        return True
    except Exception:
        return False


def _exec_with_result(source_code: str, test_code: str) -> Any:
    """Execute code and return the result of the last expression if possible."""
    namespace: dict[str, Any] = {}
    try:
        exec(source_code, namespace)
        
        tree = ast.parse(test_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if func_name.startswith('test_'):
                    modified_test = test_code + f"\n_result = {func_name}()"
                    ns2 = dict(namespace)
                    exec(modified_test, ns2)
                    if '_result' in ns2:
                        return ns2['_result']
                    return None
        return None
    except Exception:
        return None
