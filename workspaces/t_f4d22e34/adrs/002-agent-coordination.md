# ADR-002: Agent Coordination Protocol

## Status
Accepted

## Context
Multiple AI agents need to interact with the Knowledge Graph simultaneously. We need a protocol for:
- Agent registration and capability discovery
- Message passing between agents
- Conflict resolution for concurrent edits
- Action dispatch and routing

## Decision
Implement a **message-passing coordination protocol** with typed messages, agent roles, and capability-based dispatch.

## Key Design Choices

### 1. Agent Roles
Six roles: `graph_builder`, `validator`, `query_engine`, `orchestrator`, `learner`, `curator`. Each agent declares its role at registration.

### 2. Message Structure
```python
class CoordinationMessage:
    sender: str
    recipient: str  # or "broadcast"
    action: str
    payload: dict
    trace_id: str
```

### 3. Capability-Based Dispatch
Agents declare capabilities. The registry routes messages only to agents that can handle the requested action.

### 4. Conflict Resolution
Default strategy: **last-writer-wins** with optional human review for critical verticals.

## Consequences
- Positive: Decoupled agents, easy to add new agent types
- Positive: Broadcast enables fan-out patterns
- Negative: No built-in message ordering guarantees
- Negative: Broadcast can be expensive with many agents

## Alternatives Considered
- **Shared memory with locks**: Too coarse-grained for agent autonomy
- **Event sourcing**: Overkill for current scale, can be added later
- **Actor model (Akka/Pyro)**: Heavy dependency, Python ecosystem mismatch
