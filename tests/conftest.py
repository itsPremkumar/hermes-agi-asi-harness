"""Pytest hooks: exclude helper-reporter functions from collection.

Several test scripts define local helpers named `test_pass(name)` and
`test_fail(name, err)` that tally subcheck results. Pytest would otherwise
mistake them for tests and fail (missing fixtures). Explicitly exclude them
via `pytest_collection_modifyitems`.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _restore_cwd():
    """Some legacy test modules call os.chdir() at import time (e.g. into
    tests/). This fixture guarantees each test runs from the project root so
    cwd never leaks across modules."""
    cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)
    yield
    os.chdir(cwd)


def pytest_collection_modifyitems(items):
    # Drop collected "tests" that are actually report-helpers. We identify
    # them by module pattern + known helper names.
    helper_names = {"test_pass", "test_fail"}
    helper_modules = {
        "test_phase3_4",
        "test_phase5",
        "test_phase6",
        "test_phase7",
        "test_phase8",
    }
    kept = []
    for item in items:
        module = getattr(item, "module", None)
        mod_name = getattr(module, "__name__", "") if module else ""
        mod_short = mod_name.rsplit(".", 1)[-1] if mod_name else ""
        if item.name in helper_names and mod_short in helper_modules:
            continue
        kept.append(item)
    items[:] = kept
