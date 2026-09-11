# ADR Governance Process

**Document ID:** ADR-GOVERNANCE-001
**Version:** 1.0.0
**Date:** 2026-09-11
**Author:** fullstack-dev (Hermes Kanban)
**Classification:** Process

---

## Purpose

This document defines the governance process for Architecture Decision Records (ADRs) in the AGI/ASI Harness project. It establishes how decisions are proposed, reviewed, approved, and maintained over time.

---

## Scope

This process applies to:
- All architectural decisions affecting the AGI/ASI Harness
- Decisions that impact multiple components, teams, or subsystems
- Decisions that establish new patterns or deprecate existing ones
- Decisions that are expensive or hard to reverse

---

## Roles

| Role | Responsibility | Who |
|------|---------------|-----|
| **Proposer** | Drafts the ADR, gathers context, identifies alternatives | Engineer, architect, or team lead |
| **Reviewer(s)** | Evaluates the decision, provides feedback, approves | Peers, architects, or domain experts |
| **Approver** | Has authority to accept or reject the ADR | Tech lead, architect, or governance board |
| **Stakeholder** | Affected by the decision; provides input | Engineers, operators, security team |
| **Maintainer** | Keeps ADRs up to date, archives superseded records | Original proposer or designated owner |

---

## Decision Classification

Classify each decision by impact to determine the review path:

### Level 1: Team Decision
- **Scope:** Single component or team
- **Reversibility:** Easy to reverse within a sprint
- **Review:** 1 reviewer required
- **Approver:** Team lead
- **Examples:** Library choice within a component, internal API shape

### Level 2: Cross-Cutting Decision
- **Scope:** Multiple components or teams
- **Reversibility:** Moderate effort to reverse
- **Review:** 2 reviewers required (one from affected team)
- **Approver:** Tech lead or architect
- **Examples:** New integration pattern, shared data model, protocol choice

### Level 3: Strategic Decision
- **Scope:** System-wide or long-term architectural direction
- **Reversibility:** Hard or expensive to reverse
- **Review:** 3+ reviewers, including security and operations
- **Approver:** Governance board or CTO
- **Examples:** Core architecture change, safety model revision, major technology adoption

---

## Process Flow

### Step 1: Identify the Need

A decision need arises when:
- A new feature requires choosing between approaches
- An existing approach is no longer adequate
- A cross-team alignment is needed
- A significant technical debt or risk is identified

**Output:** Decision need documented (issue, RFC, or discussion thread).

### Step 2: Draft the ADR

The Proposer creates a new ADR file in `docs/adr/` using the template:

```bash
cp docs/adr/0000-adr-template.md docs/adr/NNNN-title-in-kebab-case.md
```

The Proposer fills in:
- **Context** — Why is this decision needed? What forces are at play?
- **Decision Drivers** — What constraints or requirements shape the decision?
- **Alternatives** — What options were considered? What are the trade-offs?
- **Decision** — What was chosen and why?
- **Consequences** — What are the expected outcomes (positive, negative, risks)?

**Output:** Draft ADR with status `proposed`.

### Step 3: Review

The Proposer shares the draft with Reviewers. Reviewers evaluate:

1. **Completeness** — Are all sections filled in? Are alternatives fairly presented?
2. **Soundness** — Is the reasoning sound? Are trade-offs honestly assessed?
3. **Alignment** — Does this align with existing ADRs and architectural principles?
4. **Risk** — Are risks identified and mitigated?
5. **Feasibility** — Can the team implement this with available resources?

Reviewers provide feedback via comments or inline suggestions. The Proposer iterates until Reviewers approve.

**Output:** Review feedback addressed; Reviewers sign off.

### Step 4: Approve

The Approver reviews the final draft and:
- **Accepts** — Changes status to `accepted`
- **Requests changes** — Returns to Step 3 with specific feedback
- **Rejects** — Documents rationale; ADR remains `proposed` or is closed

For Level 3 decisions, a formal review meeting may be required.

**Output:** ADR status changed to `accepted`.

### Step 5: Communicate

Once accepted:
1. Update the ADR index (`docs/adr/README.md`)
2. Link the ADR from relevant documentation
3. Announce in the project's communication channel
4. Add implementation tasks to the project tracker

**Output:** Decision is discoverable and actionable.

### Step 6: Implement

The team implements the decision:
- Track implementation tasks in the ADR's "Implementation Notes" section
- Update the ADR if implementation reveals new information
- Link related PRs or commits to the ADR

**Output:** Decision is realized in code and infrastructure.

### Step 7: Maintain

Over time:
- **Supersede** — If a better approach emerges, write a new ADR and update the old one's status to `superseded`
- **Deprecate** — If the decision is no longer relevant, mark as `deprecated` with a reason
- **Review periodically** — Revisit ADRs during architecture reviews to ensure they remain valid

**Output:** ADR archive stays current and trustworthy.

---

## Review Checklist

Use this checklist during Step 3 (Review):

- [ ] The problem statement is clear and specific
- [ ] Decision drivers are explicitly listed
- [ ] At least two alternatives are considered
- [ ] Alternatives are evaluated fairly (not strawman arguments)
- [ ] The chosen approach is stated unambiguously
- [ ] Trade-offs are honestly assessed (no "perfect" solutions)
- [ ] Risks are identified with likelihood, impact, and mitigation
- [ ] Implementation notes are actionable
- [ ] The ADR aligns with existing decisions and principles
- [ ] The ADR follows the template format
- [ ] The ADR is tagged with the correct category
- [ ] Stakeholders have been consulted

---

## Escalation Path

If consensus cannot be reached:

1. **Team level** → Escalate to Tech Lead
2. **Cross-team level** → Escalate to Architect
3. **Strategic level** → Escalate to Governance Board

The escalation should include:
- The ADR in question
- Points of disagreement
- Options for resolution
- Recommended path forward

---

## ADR Lifecycle Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Identified│────▶│  Drafted  │────▶│ Reviewed │
└──────────┘     └──────────┘     └──────────┘
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼            ▼
                    ┌──────────┐ ┌──────────┐ ┌──────────┐
                    │ Accepted │ │ Rejected │ │ Revised  │
                    └──────────┘ └──────────┘ └──────────┘
                          │                         │
                          ▼                         │
                    ┌──────────┐                    │
                    │Implemented│───────────────────┘
                    └──────────┘
                          │
                ┌─────────┼─────────┐
                ▼         ▼         ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │Superseded│ │Deprecated│ │  Active  │
          └──────────┘ └──────────┘ └──────────┘
```

---

## Templates and Tools

- **ADR Template:** `docs/adr/0000-adr-template.md`
- **ADR Index:** `docs/adr/README.md`
- **This Process:** `docs/adr/ADR-GOVERNANCE-001.md`

---

## Metrics

Track these metrics to assess ADR process health:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to accept | < 5 business days (L1), < 10 (L2), < 20 (L3) | Draft date → Accept date |
| Review iterations | < 2 rounds | Count of review cycles |
| ADR coverage | 100% of L2+ decisions | Audit quarterly |
| Staleness | < 10% of ADRs outdated | Annual review |

---

## Exceptions

In rare cases, a decision may need to be made before the full process can be completed (e.g., critical security fix, production outage). In such cases:

1. Document the decision retroactively as an ADR
2. Mark status as `accepted` with a note explaining the expedited process
3. Complete the full review within 5 business days
4. Update or reverse the decision if the review warrants it

---

## Related Documents

- [ADR Template](0000-adr-template.md) — Format for new ADRs
- [ADR Archive Index](README.md) — Current state of all ADRs
- [Architecture Principles](../architecture/architecture.md) — Guiding principles for decisions
- [Contributing Guide](../contributing.md) — General contribution process

---

Author: @fullstack-dev
