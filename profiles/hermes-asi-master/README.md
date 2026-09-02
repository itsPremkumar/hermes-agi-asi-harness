# Hermes ASI Master — Phase 8: Evolution Engine

Controlled self-improvement layer for agentic AI. Builds on Phase 7 learning.

## Features

- **GEPA** (Generate → Evaluate → Pareto → Select → Safety → Promote): prompt/strategy evolution engine
- **Benchmarks**: run task suites, measure score/latency/cost/failure rate, track baselines
- **Strategy Search**: grid, random, evolutionary, and beam search over strategy space
- **Evolution Loop**: observe weakness → hypothesis → sandbox → benchmark → safety gate → promote/rollback
- **Plugin System**: all evolutions are pluggable modules with a registry
- **Approval Gate**: Level 10 modifications require human approval

## Quickstart

```bash
# Run all tests
python -m pytest profiles/hermes-asi-master/src/evolution/tests/ -v

# Run self-test directly
python profiles/hermes-asi-master/src/evolution/tests/test_evolution.py
python profiles/hermes-asi-master/src/evolution/tests/test_plugin_approval.py
```

## Architecture

```
src/evolution/
├── __init__.py          # Package init
├── gepa.py              # Prompt/strategy evolution engine
├── benchmarks.py        # Capability benchmarks with baseline tracking
├── strategy_search.py   # Systematic strategy space exploration
├── evolution_loop.py    # Controlled self-improvement with sandbox+rollback
├── plugin.py            # Plugin system for pluggable evolution modules
├── approval.py          # Human approval gate for Level 10 modifications
└── tests/
    ├── test_evolution.py        # 96 tests for core modules
    └── test_plugin_approval.py  # 43 tests for plugin & approval
```

## Module API

### GEPA — Prompt/Strategy Evolution

```python
from evolution.gepa import GEPA, Strategy, SafetyValidator, Pareto
from evolution.benchmarks import Benchmark, quick_suite

suite = quick_suite("my_suite", [("a", "A"), ("b", "B")])
bench = Benchmark(suite)
gepa = GEPA(seed=42)
strategy = Strategy(name="s1", template="Convert to uppercase.")
step = gepa.evolve(base_strategy=strategy, benchmark=bench, runner=str.upper, n_variants=10)
print(step.promoted, step.selected_score)
```

### Benchmarks — Capability Benchmarks

```python
from evolution.benchmarks import Benchmark, TaskSuite, Task, BaselineTracker

suite = TaskSuite("my_suite")
suite.add(Task("t1", input="hello", expected="HELLO"))
bench = Benchmark(suite)
result = bench.run(runner=str.upper)
print(result.avg_score, result.success_rate)

tracker = BaselineTracker()
tracker.record(result)
report = tracker.check_regression(result)
```

### Strategy Search

```python
from evolution.strategy_search import SearchSpace, run_search

space = SearchSpace()
space.add_param("temperature", [0.1, 0.5, 0.9])
space.add_param("max_tokens", [100, 500, 1000])

def evaluate(cfg):
    return cfg.with_score(float(cfg.get("temperature", 0)))

result = run_search("grid", space, evaluate)
print(result.best.score)
```

### Evolution Loop

```python
from evolution.evolution_loop import EvolutionLoop, Hypothesis

loop = EvolutionLoop(initial_state={"x": 1})
loop.set_benchmark_fn(lambda s: float(s.get("x", 0)))
loop.set_hypothesis_fn(lambda state: Hypothesis(
    hypothesis_id="h1",
    description="increase x",
    target_module="strategy",
    changes={"x": state.current_strategy.get("x", 0) + 1},
))
loop.set_safety_fn(lambda s: (True, []))
result = loop.run(max_iterations=10)
print(result["best_score"])
```

### Plugin System

```python
from evolution.plugin import PluginBase, PluginRegistry, plugin

@plugin(name="my_plugin", version="1.0.0", description="My evolution plugin")
class MyPlugin(PluginBase):
    def run(self, state):
        # evolution logic
        return state

registry = PluginRegistry()
registry.register(MyPlugin)
p = registry.get("my_plugin")
result = p.run({"x": 1})
```

### Approval Gate

```python
from evolution.approval import ApprovalGate

gate = ApprovalGate()
req = gate.request_approval("my_plugin", "risky change", {"x": 100}, risk_level=10)
# Human reviews...
gate.approve(req.request_id, "operator")
if gate.is_approved(req.request_id):
    # Apply changes
    pass
```

## Safety

- **SafetyValidator**: checks strategies for prohibited content before promotion
- **ApprovalGate**: Level 10 modifications require explicit human approval
- **Sandbox**: all hypotheses are tested in isolation before promotion
- **Rollback**: automatic rollback on regression

## License

MIT License — see LICENSE file for details.
