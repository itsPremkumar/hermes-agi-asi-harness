# Hermes Agent × Harness — One ASI-Level System

This document describes how the **Hermes Agent desktop runtime** and the
**hermes-agi-asi-harness Python runtime** combine into a single autonomous
system: Hermes contributes conversation, tools, memory, skills, cron, and
multi-platform presence; the harness contributes the 22-phase cognitive
compiler, dual-substrate execution with proofs, bot swarms, benchmarks, and
24/7 daemon operation.

```
                        ┌─────────────────────────────┐
  you ──► HERMES AGENT │ chat · tools · memory · cron │◄── skills, bots, gateway
  (any surface)        └──────────────┬──────────────┘
                                      │ MCP stdio (spec-compliant)
                                      ▼
                       ┌──────────────────────────────┐
                       │ HARNESS (`hermes-agi-asi`)    │
                       │ asi → deliberate · execute   │
                       │   · verify · report + proof  │
                       │ bots · benchmarks · daemon   │
                       └──────────────────────────────┘
```

## 1. Connect (2 minutes)

```bash
cd hermes-agi-asi-harness
.venv/Scripts/python -m pip install -e ".[mcp]"
.venv/Scripts/python -m hermes_agi mcp-serve   # smoke: should stay running
```

Register the server with Hermes (needs one restart afterwards):

```yaml
# %LOCALAPPDATA%\hermes\config.yaml  (or $HERMES_HOME/config.yaml)
mcp_servers:
  hermes_harness:
    command: "C:/Users/PREM KUMAR/hermes-agi-asi-harness/.venv/Scripts/python.exe"
    args: ["-m", "hermes_agi", "mcp-serve"]
    timeout: 300
    connect_timeout: 120
```

> Never hand-edit secret-bearing config. This snippet contains no secrets.
> Apply via your usual config workflow, then restart Hermes Agent. Tools
> appear as `mcp_hermes_harness_asi`, `..._run_task`, `..._think`,
> `..._research`, `..._benchmark`, `..._spawn_bot`, `..._discover`,
> `..._allocate`, `..._status`, `..._health`.

Verify from Hermes: *"use mcp_hermes_harness_health and tell me the result."*

## 2. Give any task — the ASI pipeline

From the shell:

```bash
.venv/Scripts/python -m hermes_agi asi "migrate the dashboard to the new API"
```

From Hermes chat: *"use mcp_hermes_harness_asi for <task>"*.

What `asi` does (`Harness.asi()` in `src/hermes_agi/__init__.py`):

1. **Deliberate** — Graph-of-Thought: hypotheses, failure risks, invariants.
2. **Execute** — 22-phase mission compile + dual-substrate waves in isolated
   sandboxes; every wave checkpointed (`ckpt-dual-<mission>-w<N>`).
3. **Verify** — subsystem health + earned proof hash (`proof_hash`).
4. **Report** — one dossier: `{status, stages, proof, duration_s}`.
   Failures are reported, never masked.

Programmatic (Python) access for Hermes-side automation:

```python
from hermes_agi.bridge import HermesBridge
bridge = await HermesBridge.create(None)   # auto-detects your Hermes install
dossier = await bridge.asi("any task")
status = await bridge.status()             # includes "hermes_sidecar" detection
```

## 3. Continuous self-improvement loop

| Loop | Command | Cadence |
|---|---|---|
| Session refine | `python -m hermes_agi refine` | after work sessions |
| Overnight endurance | `python -m hermes_agi overnight "objective" --max-iterations 10` | nightly |
| Evolution | `python -m hermes_agi evolve --cycles 3` | weekly |
| 24/7 daemon | `python -m hermes_agi daemon run --max-iterations 0` | always-on box |
| QA gate | `python scripts/qa_harness.py .` (exit 0 required) | before every commit |
| Reviewer agents | `hermes chat -q '...'` one-shots writing to `.hermes/reviews/` | per milestone |

Findings from reviewer agents land in `.hermes/reviews/agent-*.md` and are
folded back into the code by the maintainer loop above — the system
improves itself with receipts.

## 4. Offline-first guarantees

- `self-test`, `health`, `status`, `think`, daemon, scheduler, checkpoints:
  fully offline, no keys.
- `research` uses web search when network exists, degrades honestly without it.
- LLM reasoning tiers resolve Hermes-first (OAuth/subscription), then free
  `:free` models, then local mocks — never a hard failure for missing keys.
