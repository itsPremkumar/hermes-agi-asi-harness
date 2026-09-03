"""
Tests for Overnight Engine (gnhf architecture).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from hermes_agi.overnight import (
    GitManager,
    NotesCurator,
    OvernightConfig,
    OvernightLoopController,
    OvernightSummary,
)


class TestGitManager:
    """Test GitManager operations."""

    def test_git_manager_init(self):
        gm = GitManager()
        assert gm.workspace_root is not None
        assert gm.is_git_repo() is True

    def test_get_current_branch(self):
        gm = GitManager()
        branch = gm.get_current_branch()
        assert isinstance(branch, str)
        assert len(branch) > 0


class TestNotesCurator:
    """Test NotesCurator logging and context compaction."""

    def test_notes_creation_and_logging(self, tmp_path):
        curator = NotesCurator(run_dir=tmp_path, objective="Refactor telemetry")
        assert curator.path.exists()

        curator.record_success(
            iteration=1,
            description="Created telemetry models",
            commit_info="hermes: iter 1",
            findings=["Fast pydantic v2 serialization confirmed"],
        )
        curator.record_failure(
            iteration=2,
            error_message="ImportError: module missing",
            diagnosis="Rolled back to iter 1",
        )

        ctx = curator.get_prompt_context()
        assert "Iteration 1 succeeded" in ctx
        assert "Iteration 2 failed" in ctx


class TestOvernightController:
    """Test OvernightLoopController execution and summaries."""

    def test_overnight_summary_structure(self):
        summary = OvernightSummary(
            status="completed",
            objective="test objective",
            base_branch="main",
            working_branch="hermes/overnight-test",
            iterations_completed=2,
            commits_made=2,
            consecutive_failures=0,
            elapsed_seconds=5.2,
            diff_stats=" 1 file changed, 10 insertions(+)",
            review_command="git diff main...hermes/overnight-test",
            notes_path="notes.md",
        )
        d = summary.to_dict()
        assert d["status"] == "completed"
        assert d["commits_made"] == 2
        assert "git diff" in d["review_command"]
