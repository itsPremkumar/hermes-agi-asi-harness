---
name: hermes-agi-asi-harness
description: "ASI-grade: full analysis, critical gap fixes, and improvements applied"
triggers:
  - hermes-agi-asi-harness
  - harnix improvements
  - agent harness analysis
  - ASI safety improvements
---

# hermes-agi-asi-harness — Improvement Notes

## Project Overview
- 751 Python files, 100K+ lines, 135 plugins, 88 test files
- AGI/ASI harness with LangGraph StateGraph, multi-agent orchestration
- Plugin-based architecture with safety-first design

## Critical Gaps Fixed
1. **pyproject.toml dependencies** — Fixed all missing imports
2. **agents/ duplication** — Merged into core/agents/
3. **7 entry points** → 1 unified CLI (hermes_agi_v2.py)
4. **No safety tests** → Added test_safety_validation.py with 16 real injection prompts
5. **No self-model** → Built self_model plugin (capability measurement, calibration, Brier score)
6. **No event sourcing** → Built event_sourced_state plugin (replay, causal chain, mission reconstruction)

## Architecture Rules
- Single entry point: hermes_agi_v2.py
- Plugins in plugins/<name>/ with __init__.py + plugin.yaml
- State changes through event store, not direct mutation
- Self-model reports after every task
- Safety modules must have validation tests

## Plugin List (key)
- self_model — Capability measurement, calibration tracking
- event_sourced_state — Append-only event log, replay, causal debugging
- safety_gates — R0-R6 action gate enforcement
- self_replicate_guard — Anti-self-replication
- injection_defense — Prompt injection detection

## Testing
```bash
python -m pytest tests/ -v
python -m pytest tests/test_safety_validation.py -v
```
