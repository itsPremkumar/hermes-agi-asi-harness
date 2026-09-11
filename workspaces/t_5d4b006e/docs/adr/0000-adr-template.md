# Architecture Decision Record (ADR) Template

**Document ID:** ADR-TEMPLATE-001
**Version:** 1.0.0
**Date:** 2026-09-11
**Author:** fullstack-dev (Hermes Kanban)
**Classification:** Process Template

---

## Purpose

This template defines the standard format for Architecture Decision Records (ADRs) in the AGI/ASI Harness project. ADRs capture significant architectural decisions, their context, and the consequences of choosing one alternative over others.

---

## ADR File Format

Each ADR is a Markdown file stored in `docs/adr/` with the following naming convention:

```
NNNN-title-in-kebab-case.md
```

Where `NNNN` is a zero-padded sequential number (e.g., `0001`, `0002`).

---

## ADR Template

Copy the following template when creating a new ADR:

```markdown
# ADR-NNNN: [Title of the Decision]

**Document ID:** ADR-NNNN
**Date:** YYYY-MM-DD
**Status:** proposed | accepted | deprecated | superseded
**Author:** [name or role]
**Reviewers:** [names or roles]
**Supersedes:** [ADR-ID, if applicable]
**Superseded By:** [ADR-ID, if applicable]
**Related:** [ADR-IDs, if applicable]

---

## Context

Describe the issue motivating this decision. Include:
- What is the problem or constraint we are facing?
- What forces are at play (technical, organizational, temporal)?
- What is the current state (if anything exists)?
- What stakeholders are affected?

**Decision Drivers:**
- [driver 1, e.g., "Must support 10k concurrent agents"]
- [driver 2, e.g., "Must not increase latency beyond 50ms"]
- [driver 3, e.g., "Must be implementable in current sprint"]

---

## Decision

State the decision clearly and concisely. Use active voice:

> We will [chosen approach] to achieve [goal], accepting [trade-offs].

---

## Alternatives Considered

### Alternative 1: [Name]
- **Description:** Brief description of the approach.
- **Pros:**
  - [pro 1]
  - [pro 2]
- **Cons:**
  - [con 1]
  - [con 2]
- **Estimated Effort:** [S / M / L / XL]

### Alternative 2: [Name]
- **Description:** Brief description of the approach.
- **Pros:**
  - [pro 1]
  - [pro 2]
- **Cons:**
  - [con 1]
  - [con 2]
- **Estimated Effort:** [S / M / L / XL]

---

## Consequences

### Positive
- [consequence 1]
- [consequence 2]

### Negative
- [consequence 1]
- [consequence 2]

### Neutral / Trade-offs
- [trade-off 1]
- [trade-off 2]

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk 1] | low/med/high | low/med/high | [mitigation] |
| [risk 2] | low/med/high | low/med/high | [mitigation] |

---

## Implementation Notes

- [ ] [implementation task 1]
- [ ] [implementation task 2]
- [ ] [implementation task 3]

---

## References

- [link to relevant doc]
- [link to discussion or RFC]
- [link to related ADR]
```

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| `proposed` | Decision is drafted, under review, not yet approved |
| `accepted` | Decision approved and active; implementation may be in progress |
| `deprecated` | Decision is no longer current but was once active |
| `superseded` | Decision has been replaced by a newer ADR (link required) |

---

## Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| Document ID | Yes | Unique identifier: `ADR-NNNN` |
| Date | Yes | Date the ADR was created |
| Status | Yes | Current lifecycle status |
| Author | Yes | Person or role who drafted the ADR |
| Reviewers | Yes | People who reviewed and approved |
| Supersedes | No | ADR-ID this replaces |
| Superseded By | No | ADR-ID that replaces this |
| Related | No | Related ADR-IDs for cross-reference |

---

## When to Write an ADR

Write an ADR when:
1. Choosing between two or more viable technical approaches
2. Making a decision that affects multiple components or teams
3. Establishing a new pattern or convention
4. Deprecating or replacing an existing approach
5. Making a decision that is expensive or hard to reverse

Do NOT write an ADR for:
- Routine bug fixes or minor refactors
- Decisions already covered by an existing ADR
- Trivial configuration choices with no architectural impact

---

Author: @fullstack-dev
