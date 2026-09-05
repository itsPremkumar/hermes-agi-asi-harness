# Legacy eval plugins (read-only)

Unreferenced plugin dirs moved out of `src/plugins/`. The live plugin
surface is `src/hermes_agi/plugins/` (manager, core, real) plus
`src/harness/plugins/` — nothing scans `src/plugins/`, and none of these
appear in the 21 working-plugin tests.

| Archived | Live counterpart (if any) |
|---|---|
| `benchmarks/`, `benchmark_db/`, `judge_bench/` | `benchmarks/` annex + `src/hermes_agi/benchmarks/runner.py` |
| `evaluation/` | `src/verification/vnext.py` (L0–L6) |
| `self_evaluation/` | `LoopEngine.execute_learning_loop`, capability calibration |
| `sandbox_architecture/` | `src/hermes_os/docker_sandbox.py` |

Also archived in `../legacy-eval/`: `core_research_v6.py`
(dead v6 research engine; live research is `src/deep_research/` +
`src/hermes_agi/research/`) and `agents_researcher.py` (zero importers).
