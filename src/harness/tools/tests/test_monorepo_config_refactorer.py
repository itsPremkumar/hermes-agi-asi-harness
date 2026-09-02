"""Tests for Monorepo Config Refactorer."""

import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from harness.tools.monorepo_config_refactorer import (
    MonorepoConfigRefactorer,
    ConfigFile,
    Duplication,
    RefactorPlan,
)


class TestMonorepoConfigRefactorer:
    def test_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            refactorer = MonorepoConfigRefactorer(tmp)
            assert refactorer is not None

    def test_scan_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            refactorer = MonorepoConfigRefactorer(tmp)
            result = refactorer.scan()
            assert result == []

    def test_scan_finds_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create package.json
            pkg_dir = os.path.join(tmp, "pkg1")
            os.makedirs(pkg_dir)
            with open(os.path.join(pkg_dir, "package.json"), "w") as f:
                json.dump({"name": "pkg1", "version": "1.0.0"}, f)

            refactorer = MonorepoConfigRefactorer(tmp)
            result = refactorer.scan()
            assert len(result) == 1
            assert result[0].package == "pkg1"

    def test_find_duplications(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create two packages with same version
            for pkg in ["pkg1", "pkg2"]:
                pkg_dir = os.path.join(tmp, pkg)
                os.makedirs(pkg_dir)
                with open(os.path.join(pkg_dir, "package.json"), "w") as f:
                    json.dump({"name": pkg, "version": "1.0.0"}, f)

            refactorer = MonorepoConfigRefactorer(tmp)
            duplications = refactorer.find_duplications()
            assert len(duplications) >= 1
            assert any(d.key == "version" for d in duplications)

    def test_create_refactor_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pkg in ["pkg1", "pkg2"]:
                pkg_dir = os.path.join(tmp, pkg)
                os.makedirs(pkg_dir)
                with open(os.path.join(pkg_dir, "package.json"), "w") as f:
                    json.dump({"name": pkg, "version": "1.0.0", "private": True}, f)

            refactorer = MonorepoConfigRefactorer(tmp)
            plan = refactorer.create_refactor_plan()
            assert isinstance(plan, RefactorPlan)
            assert "version" in plan.shared_config
            assert len(plan.files_to_modify) >= 2

    def test_find_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg_dir = os.path.join(tmp, "mypkg")
            os.makedirs(pkg_dir)
            with open(os.path.join(pkg_dir, "package.json"), "w") as f:
                json.dump({"name": "my-package"}, f)

            refactorer = MonorepoConfigRefactorer(tmp)
            name = refactorer._find_package(pkg_dir)
            assert name == "my-package"


class TestConfigFile:
    def test_create(self):
        cf = ConfigFile("path", "json", {"key": "value"}, "pkg")
        assert cf.path == "path"
        assert cf.config_type == "json"


class TestDuplication:
    def test_create(self):
        dup = Duplication("key", ["f1", "f2"], ["v1", "v2"], "consolidate")
        assert dup.key == "key"
        assert dup.recommended_action == "consolidate"


class TestRefactorPlan:
    def test_create(self):
        plan = RefactorPlan([], {}, [], [])
        assert plan.duplications == []
        assert plan.shared_config == {}
