# AI/ML Knowledge Graph

A comprehensive 16-vertical AI/ML Knowledge Graph with schema validation, agent coordination protocols, and Architecture Decision Records.

## 16 Verticals

| # | Vertical | Description |
|---|----------|-------------|
| 1 | ML Algorithms | Core supervised/unsupervised learning algorithms |
| 2 | Deep Learning | Neural network architectures (CNN, RNN, Transformer) |
| 3 | NLP | Natural language processing and understanding |
| 4 | Computer Vision | Image classification, detection, segmentation |
| 5 | Reinforcement Learning | Learning via environment interaction |
| 6 | Data Engineering | Data pipelines, feature stores, quality |
| 7 | MLOps | Model deployment, monitoring, drift detection |
| 8 | AI Ethics | Fairness, bias, explainability, governance |
| 9 | Knowledge Representation | Ontologies, semantic web, reasoning |
| 10 | Neural Foundations | Backprop, gradient descent, regularization |
| 11 | Generative AI | LLMs, diffusion models, prompt engineering |
| 12 | Robotics | SLAM, path planning, manipulation |
| 13 | AI Safety | Alignment, interpretability, red teaming |
| 14 | Optimization | Convex, Bayesian, evolutionary optimization |
| 15 | Probabilistic Methods | Bayesian inference, MCMC, graphical models |
| 16 | Multi-Agent Systems | Coordination, negotiation, consensus |

## Architecture

```
┌─────────────────────────────────────────────┐
│              Agent Registry                  │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ Graph    │ │Validator │ │Query Engine │ │
│  │ Builder  │ │ Agent    │ │ Agent       │ │
│  └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
│       │             │              │         │
│       └─────────────┼──────────────┘         │
│                     │                        │
│              ┌──────┴──────┐                 │
│              │ Coordination │                 │
│              │   Protocol   │                 │
│              └──────┬──────┘                 │
│                     │                        │
│         ┌───────────┴───────────┐            │
│         │   AI/ML Knowledge     │            │
│         │       Graph           │            │
│         │  (NetworkX DiGraph)   │            │
│         └───────────────────────┘            │
└─────────────────────────────────────────────┘
```

## Quickstart

```python
from kg import create_empty_graph, seed_graph, get_vertical_summary
from kg.coordination import GraphBuilderAgent, ValidatorAgent, QueryEngineAgent

# Create and seed the graph
g = create_empty_graph()
seed_graph(g)

# Check vertical distribution
summary = get_vertical_summary(g)
for vertical, count in summary.items():
    print(f"{vertical}: {count} nodes")

# Use agent coordination
from kg.coordination import create_agent_registry, register_agent, dispatch_message

registry = create_agent_registry()
register_agent(registry, GraphBuilderAgent("builder", g))
register_agent(registry, ValidatorAgent("validator", g))
register_agent(registry, QueryEngineAgent("query", g))

# Query via agent
from kg.coordination import CoordinationMessage
msg = CoordinationMessage(
    sender="user",
    recipient="query",
    action="get_verticals",
)
result = dispatch_message(registry, msg)
print(result)
```

## Schema

### Node Types (10)
`concept`, `algorithm`, `framework`, `paper`, `dataset`, `metric`, `task`, `architecture`, `technique`, `protocol`

### Edge Types (10)
`depends_on`, `extends`, `implements`, `evaluated_by`, `applied_to`, `derived_from`, `competes_with`, `complements`, `version_of`, `protocol_for`

## Testing

```bash
cd workspaces/t_f4d22e34
uv pip install -e ".[dev]"
pytest tests/ -v
```

## ADRs

- [ADR-001: Storage Backend](adrs/001-storage-backend.md) — NetworkX in-memory graph
- [ADR-002: Agent Coordination](adrs/002-agent-coordination.md) — Message-passing protocol

## License

MIT
