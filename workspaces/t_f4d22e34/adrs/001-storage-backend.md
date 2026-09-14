# ADR-001: Knowledge Graph Storage Backend

## Status
Accepted

## Context
The AI/ML Knowledge Graph needs a storage backend that supports:
- Directed graph structure with typed nodes and edges
- Fast traversal and pathfinding queries
- Cross-vertical relationship modeling
- Agent coordination (concurrent read/write)

We evaluated three options:
1. **NetworkX in-memory + serialization** — Simple, Python-native, good for prototyping
2. **Neo4j graph database** — Production-grade, Cypher query language, requires server
3. **PostgreSQL with recursive CTEs** — Existing infrastructure, less natural for graph ops

## Decision
Use **NetworkX DiGraph** as the primary in-memory graph structure with JSON serialization for persistence.

## Rationale
- Zero external dependencies for core graph ops
- Rich algorithm library (shortest path, cycles, centrality)
- Easy to serialize/deserialize for agent checkpointing
- Can be swapped for Neo4j later via a storage adapter interface

## Consequences
- Positive: Fast development, no infrastructure setup
- Positive: Deterministic and testable
- Negative: Not suitable for very large graphs (>1M nodes) without sharding
- Negative: No built-in persistence or concurrent access

## Migration Path
When the graph outgrows memory, introduce a `GraphStorage` protocol with Neo4j or PostgreSQL implementations.
