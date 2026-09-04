# Skill: tdd-pytest

Test-driven pytest workflow for Python services.

## Triggers

pytest, TDD, test suite, test-driven, unit tests

## Procedure

1. Write failing tests first (`test_*.py`, one behavior per test).
2. Implement the minimal module to green the suite.
3. Run `python -m pytest <path> -q`; require exit 0 and no skips.
4. Record provenance for each artifact; attach the suite log as evidence.

## Verify

`verify_output_law` + `pytest -q` green + L5 deterministic-oracle proof.
