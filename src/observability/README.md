# Observability & Evaluation Layer

Comprehensive observability, monitoring, and evaluation framework for the
Hermes ASI-Master ecosystem. Provides LangSmith tracing, real-time metrics
aggregation, alerting, dashboard data feeds, and a benchmark framework for
comparing model performance.

## Module Layout

```
src/observability/
├── __init__.py               — Public API exports
├── langsmith_integration.py  — LangSmith Trace SDK + SecretScrubber
├── monitoring_pipeline.py    — Real-time metrics, alerts, dashboard
├── benchmark_engine.py       — Model comparison benchmarks
└── pipeline.py               — Original ObservabilityPipeline (legacy)
```

## Quick Start

```python
from observability import (
    LangSmithTracer, SecretScrubber,
    MonitoringPipeline, AlertRule,
    BenchmarkEngine,
)

# 1. LangSmith Tracing
tracer = LangSmithTracer()
span = tracer.start_span("my_operation", inputs={"x": 1})
# ... do work ...
tracer.end_span(span.span_id, outputs={"y": 2})

# 2. Real-time Monitoring
monitor = MonitoringPipeline()
monitor.add_alert_rule(AlertRule("cpu-high", "cpu", 80.0))
monitor.record_gauge("cpu", 95.0)
alerts = monitor.get_active_alerts()

# 3. Benchmark Engine
engine = BenchmarkEngine()
engine.add_task("t1", "Solve math problem")
engine.register_model("gpt-4", my_executor)
scores = engine.run_benchmark()
leaderboard = engine.get_leaderboard()
```

## Components

### LangSmith Integration (`langsmith_integration.py`)

- `LangSmithTraceConfig` — Configuration (env vars, defaults)
- `LangSmithTracer` — Span lifecycle, cloud/offline fallback
- `SecretScrubber` — Redacts API keys, tokens, passwords from traces
- `TraceSpan` — Individual span with duration, inputs/outputs

### Monitoring Pipeline (`monitoring_pipeline.py`)

- `MonitoringPipeline` — Central metrics + alerting hub
- `MetricsAggregator` — Sliding-window stats (count, avg, min, max, rate)
- `AlertRule` — Threshold alerts (gt/lt/gte/lte) with hysteresis
- `DashboardWidget` — Dashboard data source registration
- `MetricSample` — Single data point with labels

### Benchmark Engine (`benchmark_engine.py`)

- `BenchmarkEngine` — Task registration, model registration, execution
- `BenchmarkTask` — Named task with category/difficulty
- `BenchmarkScore` — Aggregated model score across tasks
- `ModelResult` — Single (model, task) result
- Leaderboard ranking and report generation

## Running Tests

```bash
pytest tests/test_observability.py -v
```

## Design Principles

1. **Zero external dependencies** — Works fully offline without LangSmith SDK
2. **Secret redaction** — All trace data scrubbed before export
3. **Label-based routing** — Metrics, alerts, and widgets use label filtering
4. **Hysteresis** — Alert rules don't flap; they trigger once per breach
