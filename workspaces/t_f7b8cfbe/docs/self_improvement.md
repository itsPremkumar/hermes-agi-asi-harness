# SelfImprovement Engine v1.0.0

Autonomous continuous improvement loop for the hermes-agi-asi-harness. The harness improves itself over time using agent feedback and test results.

## Architecture

The SelfImprovement Engine consists of six modules that work together in a continuous feedback loop:

```
┌─────────────────────────────────────────────────────────────┐
│                    EvolutionEngine                           │
│  Orchestrates the full evolution cycle: analyze → plan →    │
│  optimize → validate → deploy → monitor                     │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
     ┌─────▼────┐ ┌───▼────┐ ┌──▼───┐ ┌───▼──────────┐
     │ Analyzer │ │Optimizer│ │Healer│ │ Performance  │
     │          │ │        │ │      │ │   Tracker    │
     └──────────┘ └────────┘ └──────┘ └──────────────┘
                                         │
                                  ┌──────▼──────┐
                                  │FeedbackLoop │
                                  └─────────────┘
```

## Modules

### 1. ImprovementAnalyzer (`analyzer.py`)

Analyzes test results, code quality metrics, and agent performance.

**Key classes:**
- `TestResult` — single test execution result
- `TestSuite` — collection of test results with aggregate statistics
- `CodeQualityMetrics` — code quality measurements (complexity, duplication, etc.)
- `AgentPerformanceMetrics` — per-agent performance tracking
- `AnalysisReport` — comprehensive analysis output

**Usage:**
```python
from src.harness.improvement import ImprovementAnalyzer, TestSuite, TestResult

analyzer = ImprovementAnalyzer(project_root="/path/to/project")
suite = TestSuite(results=[
    TestResult(name="test_one", passed=True, duration_ms=50.0),
    TestResult(name="test_two", passed=False, error_message="Failed"),
])
report = analyzer.generate_report(suite)
print(f"Health: {report.overall_health_score}")
```

### 2. AutoOptimizer (`optimizer.py`)

Automatically optimizes code based on analyzer findings.

**Key classes:**
- `OptimizationPlan` — plan of optimizations to apply
- `OptimizationResult` — result of an optimization pass

**Usage:**
```python
from src.harness.improvement import AutoOptimizer

optimizer = AutoOptimizer(dry_run=False)
results = optimizer.apply_optimizations(plans)
summary = optimizer.get_optimization_summary()
print(f"Lines saved: {summary['lines_saved']}")
```

### 3. SelfHealer (`healer.py`)

Detects and fixes common code issues automatically.

**Detects and fixes:**
- Bare except clauses
- Deprecated `.has_key()` usage
- Comparisons to `True`/`False`/`None`
- Python 2 syntax
- Inconsistent indentation
- Mutable default arguments (detected, not auto-fixed)
- Unused imports (detected)

**Usage:**
```python
from src.harness.improvement import SelfHealer

healer = SelfHealer()
results = healer.heal_project()
summary = healer.get_healing_summary()
print(f"Fixed: {summary['issues_fixed']}/{summary['issues_detected']}")
```

### 4. PerformanceTracker (`tracker.py`)

Tracks improvements over time with A/B comparisons and trend analysis.

**Key classes:**
- `MetricSnapshot` — single metric measurement
- `ABTest` — A/B test configuration and results
- `TrendAnalysis` — linear regression trend analysis

**Usage:**
```python
from src.harness.improvement import PerformanceTracker, MetricType

tracker = PerformanceTracker()
tracker.record_metric("latency", 100.0, MetricType.LATENCY)
tracker.set_baseline("latency", 120.0)
comparison = tracker.compare_to_baseline("latency")
print(f"Improvement: {comparison['pct_change']:.1f}%")
```

### 5. FeedbackLoop (`feedback.py`)

Structured feedback collection from all agents.

**Key classes:**
- `FeedbackItem` — single feedback entry
- `FeedbackSummary` — aggregated feedback statistics

**Usage:**
```python
from src.harness.improvement import FeedbackLoop, FeedbackCategory, FeedbackPriority

loop = FeedbackLoop()
item = loop.submit_feedback("agent1", FeedbackCategory.BUG, "Found issue", FeedbackPriority.HIGH)
actionable = loop.get_actionable_items()
```

### 6. EvolutionEngine (`evolution.py`)

Drives the harness through continuous evolution cycles.

**Evolution cycle phases:**
1. **Analyze** — run ImprovementAnalyzer on current state
2. **Plan** — create optimization plans from findings
3. **Optimize** — apply AutoOptimizer
4. **Validate** — verify pass rate hasn't dropped
5. **Deploy** — record metrics
6. **Monitor** — track health over time

**Usage:**
```python
from src.harness.improvement import EvolutionEngine, EvolutionConfig

config = EvolutionConfig(auto_optimize=True, rollback_on_regression=True)
engine = EvolutionEngine(config=config)
cycle = engine.run_cycle(test_suite)
print(f"Health: {cycle.health_before:.2f} → {cycle.health_after:.2f}")
```

## Configuration

The `EvolutionConfig` dataclass controls engine behavior:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `auto_optimize` | `True` | Enable automatic optimization |
| `auto_heal` | `True` | Enable self-healing |
| `require_validation` | `True` | Require test validation after optimization |
| `max_optimization_attempts` | `3` | Max attempts per optimization |
| `health_improvement_threshold` | `0.01` | Minimum health improvement required |
| `rollback_on_regression` | `True` | Roll back if tests regress |
| `min_cycles_before_deploy` | `2` | Minimum cycles before considering deploy |
| `feedback_integration` | `True` | Integrate agent feedback |

## Installation

```bash
pip install -e .
```

## Running Tests

```bash
pytest tests/ -v
```

## License

MIT
