# Legacy runtime duplicates (read-only)

Superseded subsystems with zero importers. Salvaged counterparts live in
`src/hermes_os/` (all covered by `tests/test_new_subsystems.py`).

| Archived | Salvaged into |
|---|---|
| `hermes_asi_master/runtime/cron.py` | `src/hermes_os/cron_expr.py` + `ContinuousScheduler.register_cron()` |
| `hermes_asi_master/runtime/watchdog.py` | `src/hermes_os/process_guard.py` + `HermesController.run_guarded()` |
| `hermes_asi_master/runtime/scheduler.py` | _nothing — ours already covers it_ |
| `hermes_asi_master/runtime/harness.py` | _nothing — thin dup of the kernel_ |
| `training/pipeline.py` | _nothing — simulated fine-tuner + random-mutation GA (the exact anti-pattern); real evolution is `evolution_lab.py` + `arch_search.py` |
| `test_pipeline.py` (moved from `tests/`) | tests the archived simulated pipeline; excluded from pytest collection by move |
