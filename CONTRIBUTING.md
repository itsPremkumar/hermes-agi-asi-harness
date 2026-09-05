# Contributing to hermes-agi-asi-harness

One branch per task. Green QA or it doesn't merge.

## Setup

```bash
git clone https://github.com/itsPremkumar/hermes-agi-asi-harness.git
cd hermes-agi-asi-harness
python -m venv .venv && .venv/Scripts/activate  # Windows; use bin/activate on POSIX
pip install -e ".[all]"   # runtime + api + mcp + dev suite
```

## Before you push (mandatory)

```bash
python -m hermes_agi self-test        # offline self-test, REAL asserts
python scripts/qa_harness.py .        # 8 gates: CLI, pytest subset, imports,
                                      # canonical map, ruff scope, dep sync
```

`qa_harness.py` must print `QA HARNESS GREEN` (exit 0). For full proof,
run the whole suite: `python -m pytest tests/ -q -p no:cacheprovider`.

## Branch & merge bar

- One branch per task (`agent-builder/<slice>`); merge to `main` only with QA green.
- Fast-forward when possible; remote `main` must stay ancestor-clean.
- Commit messages: `feat|fix|docs|chore(scope): imperative summary`.

## Hard-won rules (violations broke the suite before)

1. **Single import root.** `tests/conftest.py` puts `src/` on `sys.path`, so
   import bare packages: `from harness.errors import NodeError` — never
   `from src.harness.errors import ...`. The `src.`-prefixed twin creates a
   duplicate module object and `pytest.raises` silently stops matching.
2. **Never prepend to `sys.path` at module import time.** `sys.path.insert(0,
   <pkg-dir>)` inside an imported module shadows canonical sibling packages
   for the whole session (this once hid `src/memory` behind `src/core/memory`
   after kernel boot). Append a fallback, guarded, or don't touch it.
3. **Optional deps stay optional.** Gate their tests with
   `pytest.importorskip("fastapi")` (see the `[api]` extra in
   `pyproject.toml`); the suite must pass with and without extras installed.
4. **Blocking servers can't run inside `asyncio.run`.** The CLI dispatches
   inside a running loop — serve with `await uvicorn.Server(...).serve()`,
   never `uvicorn.run()`.
5. **Tests encode live contracts, not magic numbers.** If the implementation
   grades honestly (e.g. single-backend evidence scores 0.65), assert the
   documented bounds (`0.6 <= conf <= 0.9`), not a stale threshold.

## Project standards

- Offline-first; free-tier models only. No network in tests (use tmp dirs).
- Never commit secrets — `.env.example` placeholders only.
- Keep `requirements.txt` ↔ `pyproject.toml` `[project.dependencies]` in sync
  (the QA deps-sync gate enforces it); extras live in
  `[project.optional-dependencies]`.
- Every user-facing command needs a README example that you ran yourself.
