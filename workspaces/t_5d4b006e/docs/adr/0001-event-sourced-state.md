# ADR-0001: Event-Sourced State Architecture

**Document ID:** ADR-0001
**Date:** 2026-09-11
**Status:** accepted
**Author:** fullstack-dev (Hermes Kanban)
**Reviewers:** agent-architect, cto
**Supersedes:** —
**Superseded By:** —
**Related:** ADR-0002
**Category:** architecture

---

## Context

The AGI/ASI Harness executive control plane needs to track state changes across multiple subsystems (scheduler, resource manager, safety governor, plugin registry). We need a mechanism that provides:

- Full auditability of every state change
- Ability to reconstruct state at any point in time
- Support for multiple concurrent readers (projections)
- Tamper-evident history for compliance

The current approach (direct state mutation with periodic snapshots) loses granular history and makes it impossible to replay events for debugging or compliance audits.

**Decision Drivers:**
- Must support full audit trail for safety-critical operations
- Must enable state reconstruction at arbitrary points in time
- Must support multiple read models (projections) without blocking writes
- Must handle 10k+ events per second without data loss
- Must be implementable with existing infrastructure (no new database required)

---

## Decision

> We will adopt an event-sourced architecture where all state changes are captured as immutable events on a durable, ordered, event bus. Current state is derived by projecting (folding) the event stream.

Key aspects:
- Events are the source of truth; current state is a projection
- Events are immutable and never deleted
- Event bus is partitioned by aggregate ID for parallelism
- Projections are eventually consistent and can be rebuilt from the event log

---

## Alternatives Considered

### Alternative 1: Direct State Mutation with Audit Log
- **Description:** Mutate state directly in a database, write audit log entries alongside.
- **Pros:**
  - Simple to implement
  - Familiar pattern for most engineers
  - Strong consistency on current state
- **Cons:**
  - Audit log is secondary (can be skipped or desynchronized)
  - Cannot reconstruct intermediate states
  - Audit log and state can diverge
  - Hard to build new read models retroactively
- **Estimated Effort:** M

### Alternative 2: CQRS with Separate Read/Write Models
- **Description:** Separate the write model (normalized) from read model (denormalized), sync via change data capture.
- **Pros:**
  - Optimized read and write paths
  - Scales reads independently
  - Familiar to many teams
- **Cons:**
  - Does not inherently provide event history
  - CDC adds complexity and latency
  - Still mutates state (no immutable history)
- **Estimated Effort:** L

### Alternative 3: Full Blockchain
- **Description:** Use a blockchain for all state transitions with consensus.
- **Pros:**
  - Tamper-proof by design
  - Full history
  - Decentralized trust
- **Cons:**
  - Massive overhead (latency, storage, compute)
  - Overkill for a single-organization system
  - Hard to query and project
  - Operational complexity
- **Estimated Effort:** XL

---

## Consequences

### Positive
- Complete audit trail of every state change by design
- Can rebuild state at any point in time by replaying events
- New read models can be built retroactively from the event log
- Natural fit for compliance and regulatory requirements
- Enables time-travel debugging for complex issues

### Negative
- Event schema evolution requires careful versioning
- Eventually consistent projections may lag behind writes
- Storage grows unboundedly (requires retention policies)
- More complex mental model for developers unfamiliar with event sourcing

### Neutral / Trade-offs
- Read performance depends on projection freshness
- Event store becomes a critical dependency (requires backup and DR)
- Debugging requires understanding event streams, not just current state

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Event schema breaks compatibility | med | high | Versioned events; upcasters for old formats |
| Projection lag causes stale reads | low | med | Monitor lag; alert if > threshold |
| Event store grows too large | med | med | Retention policy; snapshotting; archival |
| Team unfamiliarity slows development | med | med | Training; documentation; pair programming |

---

## Implementation Notes

- [ ] Define event schema with versioning strategy
- [ ] Implement event bus with partitioning by aggregate ID
- [ ] Build projection framework (fold/reduce over event stream)
- [ ] Create snapshotting mechanism for fast state reconstruction
- [ ] Define retention and archival policies
- [ ] Add monitoring for event throughput and projection lag
- [ ] Write developer guide for event-sourced patterns
- [ ] Integrate with existing audit trail system

---

## References

- [System Architecture Overview](../architecture/architecture.md) — Section 1.4: Key Design Decisions
- [Component Design Specs](../architecture/component-design.md) — Event Bus component
- [Martin Fowler: Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Young: Versioning in an Event Sourced System](https://leanpub.com/versioning-in-an-event-sourced-system)

---

Author: @fullstack-dev
