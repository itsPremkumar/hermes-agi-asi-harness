"""Tests for swe_bench_verified_benchmark.py — SWE-bench Verified Benchmark."""
import pytest
import os
import tempfile
import json

from benchmark.swe_bench_verified_benchmark import (
    SWETask, SWEResult, SWEBenchmarkReport, SWESummary,
    SWEBenchVerifiedLoader, SWEBenchVerifiedBenchmark,
)


def _create_temp_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


def _sample_data():
    return [
        {
            "instance_id": "django__django-1",
            "repo": "django/django",
            "base_commit": "abc",
            "issue_title": "Fix view",
            "issue_description": "Views broken",
            "patch": "def fix():\n    pass",
            "test_patch": "def test():\n    pass",
            "difficulty": "easy",
        },
        {
            "instance_id": "sympy/sympy-2",
            "repo": "sympy/sympy",
            "base_commit": "def",
            "issue_title": "Fix integral",
            "issue_description": "Integral wrong",
            "patch": "def integral():\n    pass",
            "test_patch": "def test():\n    pass",
            "difficulty": "hard",
        },
    ]


class TestSWETask:
    def test_create(self):
        t = SWETask(instance_id="id1", repo="r", base_commit="c", issue_title="t", issue_description="d", patch="p", test_patch="tp")
        assert t.instance_id == "id1"
        assert t.repo == "r"

    def test_from_dict(self):
        d = {"instance_id": "id2", "repo": "r", "base_commit": "c", "issue_title": "t", "issue_description": "d", "patch": "p", "test_patch": "tp", "difficulty": "hard"}
        t = SWETask.from_dict(d)
        assert t.difficulty == "hard"


class TestSWEResult:
    def test_create(self):
        r = SWEResult(id="r1", instance_id="i1", success=True, score=1.0)
        assert r.success is True

    def test_to_dict(self):
        r = SWEResult(id="r1", instance_id="i1", success=True, score=1.0)
        d = r.to_dict()
        assert d["success"] is True


class TestSWEBenchVerifiedLoader:
    def test_load_empty(self):
        loader = SWEBenchVerifiedLoader()
        assert len(loader.tasks) == 0

    def test_load(self):
        path = _create_temp_json(_sample_data())
        loader = SWEBenchVerifiedLoader()
        tasks = loader.load(path)
        assert len(tasks) == 2
        os.unlink(path)

    def test_get(self):
        path = _create_temp_json(_sample_data())
        loader = SWEBenchVerifiedLoader()
        loader.load(path)
        assert loader.get("django__django-1") is not None
        os.unlink(path)

    def test_get_by_repo(self):
        path = _create_temp_json(_sample_data())
        loader = SWEBenchVerifiedLoader()
        loader.load(path)
        tasks = loader.get_by_repo("django/django")
        assert len(tasks) == 1
        os.unlink(path)

    def test_get_by_difficulty(self):
        path = _create_temp_json(_sample_data())
        loader = SWEBenchVerifiedLoader()
        loader.load(path)
        tasks = loader.get_by_difficulty("easy")
        assert len(tasks) == 1
        os.unlink(path)


class TestSWEBenchVerifiedBenchmark:
    def test_load(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        assert len(b.loader.get_all()) == 2
        os.unlink(path)

    def test_run(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        r = b.run("django__django-1", "patch", {"t1": True, "t2": True})
        assert r is not None
        assert r.success is True
        os.unlink(path)

    def test_run_missing(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        r = b.run("nonexistent", "patch", {"t1": True})
        assert r is None
        os.unlink(path)

    def test_run_partial(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        r = b.run("django__django-1", "patch", {"t1": True, "t2": False})
        assert r is not None
        assert r.score == 0.5
        os.unlink(path)

    def test_run_sample(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        results = b.run_sample(2, random_seed=42)
        assert len(results) == 2
        os.unlink(path)

    def test_get_resolution_rate(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        b.run("django__django-1", "patch", {"t1": True, "t2": True})
        b.run("sympy/sympy-2", "patch", {"t1": False})
        rate = b.get_resolution_rate()
        assert rate == 0.5
        os.unlink(path)

    def test_get_report(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        b.run("django__django-1", "patch", {"t1": True, "t2": True})
        b.run("sympy/sympy-2", "patch", {"t1": False})
        report = b.get_report()
        assert report.total_tasks == 2
        assert report.resolved == 1
        assert report.unresolved == 1
        assert report.resolution_rate == 0.5
        os.unlink(path)

    def test_get_results_by_repo(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        b.run("django__django-1", "patch", {"t1": True})
        b.run("sympy/sympy-2", "patch", {"t1": True})
        by_repo = b.get_results_by_repo()
        assert "django/django" in by_repo
        assert "sympy/sympy" in by_repo
        os.unlink(path)

    def test_get_results_by_difficulty(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        b.run("django__django-1", "patch", {"t1": True})
        b.run("sympy/sympy-2", "patch", {"t1": True})
        by_diff = b.get_results_by_difficulty()
        assert "easy" in by_diff
        assert "hard" in by_diff
        os.unlink(path)

    def test_clear_results(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        b.run("django__django-1", "patch", {"t1": True})
        b.clear_results()
        assert len(b.results) == 0
        os.unlink(path)

    def test_empty_resolution_rate(self):
        b = SWEBenchVerifiedBenchmark()
        assert b.get_resolution_rate() == 0.0

    def test_empty_report(self):
        b = SWEBenchVerifiedBenchmark()
        report = b.get_report()
        assert report.total_tasks == 0
        assert report.resolution_rate == 0.0

    def test_report_to_dict(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        b.run("django__django-1", "patch", {"t1": True})
        report = b.get_report()
        d = report.to_dict()
        assert "total_tasks" in d
        assert "resolution_rate" in d
        os.unlink(path)

    def test_sample_larger_than_n(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        results = b.run_sample(100, random_seed=42)
        assert len(results) == 2
        os.unlink(path)

    def test_success_threshold(self):
        path = _create_temp_json(_sample_data())
        b = SWEBenchVerifiedBenchmark()
        b.load(path)
        # Exactly 0.8 should be success
        r = b.run("django__django-1", "patch", {"t1": True, "t2": True, "t3": True, "t4": True, "t5": False})
        assert r.score == 0.8
        assert r.success is True
        os.unlink(path)
