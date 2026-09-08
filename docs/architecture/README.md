# AGI/ASI Harness

A unified control plane for orchestrating, monitoring, and governing advanced AI systems.

## Overview

The AGI/ASI Harness provides executive function above individual agent runtimes, delivering:
- **Safety guarantees** — Multi-layer safety gates with human oversight
- **Resource allocation** — Hierarchical budget management across agents
- **Plugin extensibility** — Add capabilities without modifying core code
- **Hermes integration** — Native bridge to the Hermes agent framework

## Architecture

The harness is composed of three main subsystems:

### Executive Control Plane
- **Scheduler** — Priority-based task dispatch with preemption
- **Resource Manager** — Token budgets, wall time, memory limits
- **Safety Governor** — Gate pipeline for action authorization

### Plugin System
- **Plugin Registry** — Discovery, loading, lifecycle management
- **Plugin Sandbox** — Isolated execution with resource limits
- **Provider Manager** — External service integration (LLM, search, storage)

### Integration Layer
- **Hermes Bridge** — Translate harness protocols to Hermes APIs
- **Event Bus** — Durable, ordered, partitioned event streaming
- **External Connectors** — LLM providers, web search, observability

## Documentation

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | Complete system architecture |
| [component-design.md](component-design.md) | Component design specifications |
| [integration-patterns.md](integration-patterns.md) | Integration patterns and protocols |
| [deployment-architecture.md](deployment-architecture.md) | Deployment models and infrastructure |

## Quick Start

### Single-Node Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your settings

# Run
python -m harness --config config.yaml
```

### Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace harness-system

# Deploy
kubectl apply -f k8s/

# Verify
kubectl get pods -n harness-system
```

## API

### Submit a Task

```bash
curl -X POST https://harness.example.com/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "research",
    "payload": {"query": "..."},
    "priority": 5,
    "deadline": "2026-08-31T12:00:00Z"
  }'
```

### Get Task Status

```bash
curl https://harness.example.com/v1/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"
```

## Configuration

```yaml
harness:
  name: production-harness
  version: 1.0.0

  scheduler:
    algorithm: edf
    max_concurrent_tasks: 100
    preemption_enabled: true

  resources:
    llm_tokens_per_minute: 1000000
    max_agents: 50
    max_memory_gb: 128
    emergency_reserve_pct: 5

  safety:
    default_policy: deny
    escalation_timeout_seconds: 300
    gates:
      - name: scope
        priority: 0
        enabled: true
      - name: resource
        priority: 10
        enabled: true
      - name: rate
        priority: 20
        enabled: true
      - name: content
        priority: 30
        enabled: true
      - name: privacy
        priority: 40
        enabled: true
      - name: consent
        priority: 50
        enabled: true
      - name: impact
        priority: 60
        enabled: true

  plugins:
    auto_load: true
    sandbox_enabled: true
    allowed_sources:
      - builtin
      - pypi
      - npm

  hermes:
    endpoint: https://hermes.internal/api
    timeout_seconds: 30
    retry_policy:
      max_retries: 3
      backoff: exponential

  observability:
    log_level: info
    metrics_enabled: true
    tracing_enabled: true
    export_endpoint: https://observability.internal/api
```

## Safety

The harness implements a multi-layer safety model:

1. **Input validation** — Schema validation, injection detection
2. **Action constraints** — Scope, resource, and rate gates
3. **Output filtering** — Content scanning, PII redaction
4. **Behavioral monitoring** — Anomaly detection, audit logging
5. **Human oversight** — Escalation for high-impact actions

### Emergency Stop

```bash
# Trigger e-stop
curl -X POST https://harness.example.com/v1/safety/estop \
  -H "Authorization: Bearer $TOKEN"

# Reset e-stop (requires manual confirmation)
curl -X POST https://harness.example.com/v1/safety/estop/reset \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"confirmation": "I have reviewed the root cause"}'
```

## Development

### Project Structure

```
harness/
├── src/
│   ├── control_plane/
│   │   ├── scheduler.py
│   │   ├── resource_manager.py
│   │   └── safety_governor.py
│   ├── plugins/
│   │   ├── registry.py
│   │   ├── sandbox.py
│   │   └── provider_manager.py
│   ├── integration/
│   │   ├── hermes_bridge.py
│   │   ├── event_bus.py
│   │   └── connectors/
│   ├── storage/
│   │   ├── checkpoint_store.py
│   │   ├── event_log.py
│   │   └── metrics_store.py
│   └── observability/
│       ├── logger.py
│       ├── metrics.py
│       └── tracing.py
├── tests/
├── k8s/
├── docs/
└── config/
```

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## References

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
- [Anthropic Responsible Scaling Policy](https://www.anthropic.com/news/anthropics-responsible-scaling-policy)
- [OpenAI Preparedness Framework](https://openai.com/preparedness/)
- [Google AI Principles](https://ai.google/principles/)
