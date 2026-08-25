# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-25

### Added
- `src/reflexion_eval/memory.py` — Episodic reflection store (`MemoryStore`, `Reflection`)
  with add/get/clear/serialize and `format_history` for prompt injection.
- `src/reflexion_eval/evaluator.py` — Rubric-based scoring system (`Rubric`, `Score`)
  with `build_eval_prompt` and `parse_score_response` supporting multiple output formats.
- `src/reflexion_eval/loop.py` — Core Reflexion act → evaluate → reflect → retry cycle
  (`run_reflexion`, `Task`, `LoopResult`, `LLM` Protocol).
- `src/reflexion_eval/bench.py` — Benchmark runner with pass@k computation
  (`run_benchmark`, `load_suite`, `pass_at_k`, CLI entry point).
- `src/reflexion_eval/tasks/` — 20 benchmark tasks as YAML files (math, string,
  sorting, search, regex, algorithm problems).
- `tests/` — 81 pytest tests across 4 modules with mocked LLM callables.
- `pyproject.toml` — Project configuration with hatchling build backend.
- `README.md` — Project documentation with architecture and quickstart.
- `LICENSE` — MIT License.
- `.gitignore` — Python and common IDE ignore patterns.

### Features
- Agent attempts task → evaluator scores output → agent receives feedback and retries.
- Episodic memory buffer stores reflections for improved subsequent attempts.
- Benchmark suite computes pass@k curves over a task suite.
- Tolerant score parser handles `FINAL SCORE: X`, `X/1`, and standalone floats.
- Short-circuit on first passing attempt to save compute.
