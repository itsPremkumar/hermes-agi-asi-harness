"""Tests for the read-only Hermes-home mirror (one-system depth)."""

from __future__ import annotations

import json
from pathlib import Path

from harness.core.hermes_integration import HermesAgentIntegration


def _fake_home(tmp_path: Path) -> Path:
    (tmp_path / "profiles" / "agent-builder").mkdir(parents=True)
    (tmp_path / "profiles" / "agent-builder" / "config.yaml").write_text("x: 1")
    (tmp_path / "cron").mkdir()
    (tmp_path / "cron" / "jobs.json").write_text(
        json.dumps({"jobs": [{"id": "j1", "name": "demo", "command": "echo hi", "enabled": True}]})
    )
    (tmp_path / "skills" / "demo-skill").mkdir(parents=True)
    (tmp_path / "skills" / "demo-skill" / "SKILL.md").write_text("# demo")
    (tmp_path / "kanban" / "boards" / "demo-board").mkdir(parents=True)
    return tmp_path


def test_mirror_fake_home(tmp_path):
    integ = HermesAgentIntegration()
    summary = integ.mirror_hermes_home(str(_fake_home(tmp_path)))
    assert summary["profiles"] == 1, summary
    assert summary["cron_jobs"] == 1, summary
    assert summary["skills"] == 1, summary
    assert summary["boards"] == 1, summary
    assert integ.get_profile("agent-builder") is not None
    job = integ.get_cron_job("j1")
    assert job is not None and job.action == "echo hi", job
    assert integ.list_mirrored_skills() == ["demo-skill"]
    assert integ.list_mirrored_boards() == ["demo-board"]


def test_mirror_missing_home_is_empty(tmp_path):
    integ = HermesAgentIntegration()
    summary = integ.mirror_hermes_home(str(tmp_path / "does-not-exist"))
    assert summary == {"home": "", "profiles": 0, "cron_jobs": 0, "skills": 0, "boards": 0}


def test_mirror_never_writes(tmp_path):
    home = _fake_home(tmp_path)
    before = sorted(p.stat().st_mtime_ns for p in home.rglob("*") if p.is_file())
    HermesAgentIntegration().mirror_hermes_home(str(home))
    after = sorted(p.stat().st_mtime_ns for p in home.rglob("*") if p.is_file())
    assert before == after


def test_mirror_real_home_sees_agent_builder():
    home = HermesAgentIntegration.resolve_hermes_home()
    if home is None:  # CI machines without Hermes installed
        return
    integ = HermesAgentIntegration()
    summary = integ.mirror_hermes_home()
    assert summary["profiles"] >= 1, summary
    assert integ.get_profile("agent-builder") is not None
