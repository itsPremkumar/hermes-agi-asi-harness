# Aetheria Observability

Observability & Evaluation Layer for hermes-agi-asi-harness.

## Features

- **LangSmith Integration** — Tracing and evaluation for LLM runs
- **Monitoring Pipeline** — Real-time metrics collection and alerting
- **Benchmark Engine** — Model comparison framework with pluggable scorers
- **Structured Logging** — Trace-aware structured logging
- **Health Checks** — System health monitoring

## Quickstart

```python
from observability import Observability, LangSmithClient, MonitoringPipeline, BenchmarkEngine

# Core observability facade
obs = Observability()
obs.metrics.record("cpu_usage", 75.5)
obs.logger.info("System started")
print(obs.report())

# LangSmith tracing
client = LangSmithClient(api_key="your-key", project_name="my-project")
with client.trace("my_chain", inputs={"prompt": "Hello"}) as run:
    # Your LLM logic here
    pass

# Monitoring pipeline
pipeline = MonitoringPipeline()
pipeline.add_alert_rule(AlertRule(name="high_cpu", metric="cpu", threshold=90.0))
pipeline.record("cpu", 95.0)

# Benchmark engine
engine = BenchmarkEngine()
engine.add_case(BenchmarkCase(case_id="1", prompt="What is 2+2?", expected="4"))
engine.register_model("gpt-4", my_model)
results = engine.run_benchmark("gpt-4")
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
