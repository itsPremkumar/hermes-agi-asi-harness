# Skill: safe-refactor

AST-guided refactoring that preserves behavior and passes the suite.

## Triggers

refactor, cleanup, modernize, restructure, rename

## Procedure

1. Snapshot: `git status` clean (or checkpoint first); record baseline `pytest -q`.
2. Small surgical edits (`edit_file`), one behavior per change.
3. Re-run suite after each edit; on red, revert that edit immediately.
4. Final `git diff --stat` review + OUTPUT LAW check (no silent no-ops).

## Verify

Suite green before AND after; diff shows only intended hunks.
