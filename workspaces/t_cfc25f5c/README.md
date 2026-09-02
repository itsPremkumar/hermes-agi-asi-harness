# ContextVault — Agent Long-Term Memory Store

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](pyproject.toml)

**ContextVault** is an open-source agent long-term memory store with hierarchical memory tiers, vector search, consolidation pipelines, and multi-agent access control.

## Features

- **Hierarchical Memory Architecture** — Working, Episodic, Semantic, and Procedural tiers
- **Vector Embedding Store** — FAISS-indexed for fast semantic retrieval (with hash-based fallback)
- **Memory Consolidation Pipeline** — Merge, summarize, and abstract short-term to long-term
- **Relevance Scoring** — Ebbinghaus-inspired forgetting curve with access-based boost
- **Multi-Agent Shared Memory** — Fine-grained access control (private, shared, public, restricted)
- **Hybrid Search** — Semantic + keyword inverted-index search with highlights
- **TTL & Cold Storage** — Automatic expiration and archival to compressed cold storage
- **REST API** — FastAPI-based HTTP server for remote memory operations
- **Kubernetes Operator** — Auto-generated manifests for horizontal scaling
- **Dashboard** — Visualization and debugging for memory state

## Quickstart

### Install

```bash
pip install contextvault
# Or install with HTTP server support:
pip install contextvault[server]
```

### Store and Search Memories

```python
from contextvault import MemoryStore, MemoryType, MemoryTier, MemoryMetadata

# Create a store
store = MemoryStore()

# Store a memory
mem = store.store(
    content="The capital of France is Paris",
    memory_type=MemoryType.FACT,
    tier=MemoryTier.SEMANTIC,
    metadata=MemoryMetadata(agent_id="agent-1", tags=["geography"]),
)

# Search
results = store.search("capital France", top_k=5)
for r in results:
    print(f"  [{r['score']:.3f}] {r['content']}")

# Promote to procedural
store.promote(mem.id, MemoryTier.PROCEDURAL)

# Archive
store.archive(mem.id)
```

### Multi-Agent Access Control

```python
from contextvault import AccessController, AccessLevel, MemoryMetadata

ac = AccessController()
ac.register_agent("agent-1", "Research Agent")
ac.register_agent("agent-2", "Analysis Agent")

# Store a shared memory
mem = store.store(
    content="Shared findings",
    memory_type=MemoryType.FACT,
    tier=MemoryTier.SEMANTIC,
    metadata=MemoryMetadata(
        agent_id="agent-1",
        access_level=AccessLevel.SHARED,
    ),
)

# Grant access
ac.grant_access(mem, "agent-2")

# Check access
assert ac.can_access(mem, "agent-2")  # True
assert not ac.can_access(mem, "agent-3")  # False
```

### Memory Consolidation

```python
from contextvault import ConsolidationPipeline

pipeline = ConsolidationPipeline()

# Create working memories
mems = [
    store.store(f"Observation {i}", MemoryType.FACT, MemoryTier.WORKING)
    for i in range(5)
]

# Consolidate into semantic tier
result = pipeline.consolidate(mems, MemoryTier.SEMANTIC, operation="merge")
print(result.content)  # "[Merged] Observation 0 | Observation 1 | ..."
```

### Start the HTTP Server

```bash
contextvault-server
# Or programmatically:
python -m contextvault.server
```

```bash
# Store via API
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Important fact", "memory_type": "fact", "tier": "semantic"}'

# Search via API
curl "http://localhost:8000/api/v1/search?query=fact&top_k=5"
```

### Self-Test

```bash
contextvault self-test
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                ContextVault                       │
├─────────────────────────────────────────────────┤
│  CLI  │  HTTP API  │  gRPC  │  Dashboard        │
├─────────────────────────────────────────────────┤
│              MemoryStore                         │
│  ┌─────────┬─────────┬──────────┬────────────┐  │
│  │ Working │Episodic │Semantic  │Procedural  │  │
│  └─────────┴─────────┴──────────┴────────────┘  │
├─────────────────────────────────────────────────┤
│  VectorStore (FAISS)  │  Inverted Index        │
├─────────────────────────────────────────────────┤
│  ConsolidationPipeline │  TTLManager │ Cold     │
├─────────────────────────────────────────────────┤
│  AccessController │ RelevanceScorer           │
└─────────────────────────────────────────────────┘
```

## Memory Tiers

| Tier | Description | Retention |
|------|-------------|-----------|
| **Working** | Short-lived, immediate context | Minutes to hours |
| **Episodic** | Event-based memories | Days to weeks |
| **Semantic** | Facts and knowledge | Permanent |
| **Procedural** | Skills and behaviors | Permanent |

## Kubernetes Deployment

```bash
# Generate manifests
python -c "from contextvault.k8s_operator import generate_default_manifests; generate_default_manifests('k8s')"

# Apply
kubectl apply -f k8s/
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=contextvault --cov-report=term-missing
```

## License

MIT License — see [LICENSE](LICENSE) for details.
