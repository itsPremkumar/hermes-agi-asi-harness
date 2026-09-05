# Hermes Continuous Operations (24/7 ASI Harness)

How to install, run, monitor, and stop the always-on harness on Windows.
All runtime state lives under `.hermes/` (git-ignored). Source of truth for
commands: `python -m hermes_agi --help`.

## 1. Install (one time)

```powershell
cd hermes-agi-asi-harness
C:\Users\PREM KUMAR\AppData\Local\Programs\Python\Python312\python.exe -m pip install -e . --no-deps
```

Verify the install resolves to this checkout (not a stale copy):

```powershell
python -c "import hermes_agi.__main__ as m; print(m.__file__)"
# must print ...\hermes-agi-asi-harness-clone\src\hermes_agi\__main__.py
```

## 2. Auto-start on boot (Task Scheduler)

```powershell
# Run PowerShell as Administrator for a machine-level task
.\scripts\install_daemon_task.ps1
.\scripts\uninstall_daemon_task.ps1   # to remove
```

What it does: creates task `HermesAGI-Daemon` (boot trigger, restart on
failure every 5 min) running `daemon run` in this directory. Logs go to
`.hermes\daemon-task.log`.

## 3. Daily operation

```powershell
python -m hermes_agi daemon enqueue "refactor auth module, verify tests"
python -m hermes_agi daemon run                 # infinite loop; Ctrl+C stops
python -m hermes_agi daemon status              # queue + checkpoints + scheduler
python -m hermes_agi daemon stop                # graceful stop request
python -m hermes_agi hermes health              # worker lifecycle
python -m hermes_agi consolidate                # P22 memory sleep cycle
python -m hermes_agi invariants                 # 22 safety invariants
python -m hermes_agi killswitch status          # engage | release
python -m hermes_agi llm status                 # Hermes-first chain tiers
python -m hermes_agi api serve                  # status API on 127.0.0.1:8471
```

## 4. Model chain (Hermes-first)

Order: `H1` Hermes managed router → `H2` fingerprinted llama-server →
`L` Ollama/LM Studio → `C` cloud (OpenRouter/OpenAI) → `D` deterministic.
Probes cached 5 min (`HERMES_LLM_PROBE_TTL`). Cloud has a circuit breaker
(`HERMES_LLM_CB_FAILS=3`, `HERMES_LLM_CB_COOLDOWN=600`): after N consecutive
failures the tier is skipped until cooldown, killing the 404 latency tax.

```powershell
$env:OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"  # paid slug
$env:HERMES_LLM_ORDER = "H1,H2,L,C"                          # reorder/subset
python -m hermes_agi llm refresh
python -m hermes_agi llm status --ask "summarize mission state"
```

No key at all = fully offline deterministic mode (all tests pass this way).

## 5. Monitoring

| Signal | Location |
|---|---|
| Event audit trail | `.hermes/events/audit.jsonl` |
| Mission checkpoints | `.hermes/checkpoints/*.json` |
| Daemon queue (crash-safe) | `.hermes/daemon_queue.json` |
| Token/cost ledger | `.hermes/memory/economic_ledger.jsonl` |
| Watchdog forensics | `.hermes/forensics/watchdog-*.json` |
| Human approvals | `.hermes/approvals/*.json` |
| Kill switch | `.hermes/KILL` (presence halts mutations) |
| Dashboard | `python scripts/build_dashboard.py` → `.hermes/dashboard.html` |
| LangSmith cloud | set `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true`; otherwise air-gap local spans |

Key invariants to watch: daemon `pending` draining, `in_progress` returning to 0,
Hermes `live`/`stale` at 0 between jobs, ledger cost trend, `forensics/` empty.

## 6. Recovery

* Crash mid-mission → restart `daemon run`: `requeue_interrupted()` re-enqueues
  `in_progress` checkpoints automatically.
* Wedged workers → `hermes health` shows live/stale; background leases
  (default 300s) expire them; `kill <iid>` for immediate.
* Bad queue entries → drain with `scripts/drain_queue.py` equivalent
  (`PersistentDaemonRuntime.pop_next_mission()` until empty).
* Emergency → `killswitch engage` (blocks all mutations via invariant gate),
  `daemon stop`, investigate forensics, `killswitch release`.
