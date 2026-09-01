# Benchmark Strategy v2 — Hermes ASI Harness

## Overview

The Hermes ASI Harness benchmark suite evaluates AI agent capabilities across multiple dimensions:
code generation, reasoning, and comprehension. The strategy targets 100% pass rate through
iterative improvement driven by the research module.

## Benchmark Suite

| Benchmark | Problems | Domain | Status |
|-----------|----------|--------|--------|
| HumanEval | 164 | Code generation | ✅ Complete (33 tests) |
| MBPP | 974+ | Code generation | ✅ Complete (31 tests) |
| HellaSwag | 10,000 | Commonsense reasoning | ✅ Complete (30 tests) |
| BoolQ | 1,000 | Boolean QA | ✅ Complete (28 tests) |
| ARC-AGI-3 | 15 levels | Abstract reasoning | ✅ Complete (80 tests) |

## Architecture

All benchmarks follow a plugin-based architecture:

```
src/benchmark/
├── human_eval_benchmark.py    # HumanEval: 164 Python problems
├── mbpp_benchmark.py          # MBPP: 974+ Python problems
├── hellaswag_benchmark.py     # HellaSwag: 10K commonsense problems
├── boolq_benchmark.py         # BoolQ: 1000 boolean QA problems
├── arc_agi_3_levels.py        # ARC-AGI-3: 15 difficulty levels
└── tests/                     # Comprehensive test suite
```

## Common API

All benchmarks implement a consistent interface:

```python
bench = Benchmark()
bench.load_problems()           # Load built-in problems
bench.run_problem(id)           # Run single problem
bench.run_all()                 # Run all problems
bench.get_pass_rate()           # Get pass rate statistics
```

## Improvement Loop

The research module (`src/research/benchmark_research.py`) drives continuous improvement:

1. **Record** benchmark runs
2. **Analyze** performance trends
3. **Generate** improvement recommendations
4. **Apply** strategy/parameter/architecture changes
5. **Re-evaluate** to measure impact

## Target Metrics

- **HumanEval**: 100% pass rate (164/164)
- **MBPP**: 100% pass rate (974/974)
- **HellaSwag**: 100% pass rate (10000/10000)
- **BoolQ**: 100% pass rate (1000/1000)
- **ARC-AGI-3**: 100% pass rate (15/15 levels)

## Daily Improvement

The system runs daily benchmark evaluations via cron, tracking progress and automatically
generating improvement recommendations based on trend analysis.
