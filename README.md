# reflexion-eval

A Reflexion-style self-improving agent harness: the agent attempts a task, an
evaluator scores the output, the agent receives verbal feedback and retries —
storing reflections in an episodic memory buffer. Includes a benchmark runner
over a task suite with pass@k curves.

## Architecture

```
agent ←→ [act] → output
  ↓ [evaluate] → score + feedback (rubric-based)
  ↓ [reflect] → store reflection in episodic memory
  ↻ retry (context = task + memory + feedback)
```

- `src/reflexion_eval/loop.py` — the core act → evaluate → reflect → retry cycle.
- `src/reflexion_eval/memory.py` — episodic reflection store (in-memory + serializable).
- `src/reflexion_eval/evaluator.py` — rubric-based scoring prompts + verdict extraction.
- `src/reflexion_eval/bench.py` — task-suite runner that computes pass@k curves.
- `src/reflexion_eval/tasks/` — 20 benchmark tasks as YAML.
- `tests/` — pytest suite with a mocked LLM.

## Quickstart

```bash
pip install -e ".[dev]"

# run the benchmark suite
python -m reflexion_eval.bench --tasks src/reflexion_eval/tasks \
    --max-iterations 3 --k 1,3

# run tests
pytest -q
```

## License

MIT.
