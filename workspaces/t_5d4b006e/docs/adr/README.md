# Architecture Decision Records — Archive Index

**Document ID:** ADR-INDEX-001
**Version:** 1.0.0
**Date:** 2026-09-11
**Author:** fullstack-dev (Hermes Kanban)
**Classification:** Archive

---

## Overview

This index tracks all Architecture Decision Records (ADRs) for the AGI/ASI Harness project. ADRs are stored in `docs/adr/` and follow the format defined in [0000-adr-template.md](0000-adr-template.md).

---

## How to Use This Archive

1. **Browse** — Scan the tables below by status, category, or date.
2. **Search** — Use `grep` or your editor to search within `docs/adr/`.
3. **Reference** — Link to ADRs from other docs using their Document ID.
4. **Track** — Update status fields when decisions evolve.

---

## Active ADRs (Accepted)

| ID | Title | Date | Author | Status |
|----|-------|------|--------|--------|
| ADR-0001 | [Event-Sourced State Architecture](0001-event-sourced-state.md) | 2026-09-11 | fullstack-dev | accepted |

---

## Proposed ADRs

| ID | Title | Date | Author | Status |
|----|-------|------|--------|--------|
| — | — | — | — | — |

---

## Superseded ADRs

| ID | Title | Superseded By | Date |
|----|-------|---------------|------|
| — | — | — | — |

---

## Deprecated ADRs

| ID | Title | Date Deprecated | Reason |
|----|-------|-----------------|--------|
| — | — | — | — |

---

## ADR Statistics

| Metric | Count |
|--------|-------|
| Total ADRs | 1 |
| Accepted | 1 |
| Proposed | 0 |
| Superseded | 0 |
| Deprecated | 0 |

---

## Categories

ADRs are tagged with categories for filtering:

| Category | Description |
|----------|-------------|
| `architecture` | System-level structural decisions |
| `safety` | Safety gate, guardrail, or oversight decisions |
| `integration` | External system or protocol decisions |
| `data` | Data model, storage, or persistence decisions |
| `performance` | Latency, throughput, or scaling decisions |
| `governance` | Policy, compliance, or process decisions |
| `security` | Authentication, authorization, or encryption decisions |

---

## File Naming Convention

```
docs/adr/NNNN-title-in-kebab-case.md
```

- `NNNN` — Zero-padded sequential number (0001, 0002, ...)
- `title-in-kebab-case` — Short, descriptive title
- `.md` — Markdown format

---

## Quick Reference

```bash
# List all ADRs
ls docs/adr/

# Search ADRs by keyword
grep -r "keyword" docs/adr/

# Find ADRs by status
grep -r "Status: accepted" docs/adr/

# Find ADRs by category
grep -r "Category: safety" docs/adr/
```

---

Author: @fullstack-dev
