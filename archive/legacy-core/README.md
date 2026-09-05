# Legacy core orphans (read-only)

`src/core/*` modules with zero importers anywhere (verified by import-graph
scan with re-export fixpoint, `src.`-prefix and relative-import handling).
Kept in `src/core/`: everything imported by tests or runtime (`coding/`,
`dashboard/`, `cicd/`, `benchmark/`, `runtime/`, `verification/`, …).

Salvaged counterparts live in `src/hermes_os/` (`cognitive_compiler`,
`safety_kernel`, `strategy_search`, `recovery`, `tool_env`, …).
