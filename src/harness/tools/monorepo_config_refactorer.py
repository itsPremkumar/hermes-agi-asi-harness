"""Monorepo Config Refactorer.

Detects config duplication across packages and consolidates into shared config.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ConfigFile:
    path: str
    config_type: str  # json, yaml, toml, env
    content: dict[str, Any]
    package: str


@dataclass
class Duplication:
    key: str
    files: list[str]
    values: list[Any]
    recommended_action: str


@dataclass
class RefactorPlan:
    duplications: list[Duplication]
    shared_config: dict[str, Any]
    files_to_modify: list[str]
    files_to_create: list[str]


class MonorepoConfigRefactorer:
    """Detect and consolidate duplicated configs."""

    def __init__(self, root_path: str):
        self._root = root_path
        self._config_files: list[ConfigFile] = []

    def scan(self) -> list[ConfigFile]:
        """Scan for config files."""
        self._config_files = []
        for dirpath, dirnames, filenames in os.walk(self._root):
            # Skip node_modules, .git, __pycache__
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__", ".venv")]
            for fname in filenames:
                if fname in ("package.json", "tsconfig.json", ".eslintrc.json", "pyproject.toml"):
                    full_path = os.path.join(dirpath, fname)
                    package = self._find_package(dirpath)
                    config_type = fname.split(".")[-1] if "." in fname else "json"
                    try:
                        with open(full_path, "r") as f:
                            content = f.read()
                        if config_type == "json":
                            parsed = json.loads(content)
                        else:
                            parsed = {"raw": content}
                        self._config_files.append(
                            ConfigFile(
                                path=full_path,
                                config_type=config_type,
                                content=parsed,
                                package=package,
                            )
                        )
                    except (json.JSONDecodeError, OSError):
                        pass
        return self._config_files

    def find_duplications(self) -> list[Duplication]:
        """Find duplicated config keys across packages."""
        if not self._config_files:
            self.scan()

        # Group by config type
        by_type: dict[str, list[ConfigFile]] = {}
        for cf in self._config_files:
            by_type.setdefault(cf.config_type, []).append(cf)

        duplications = []
        for config_type, files in by_type.items():
            if len(files) < 2:
                continue
            # Find common keys
            all_keys = set()
            for cf in files:
                if isinstance(cf.content, dict):
                    all_keys.update(cf.content.keys())

            for key in all_keys:
                values = []
                file_paths = []
                for cf in files:
                    if isinstance(cf.content, dict) and key in cf.content:
                        values.append(cf.content[key])
                        file_paths.append(cf.path)

                if len(values) > 1:
                    # Check if values are the same
                    if all(str(v) == str(values[0]) for v in values):
                        duplications.append(Duplication(
                            key=key,
                            files=file_paths,
                            values=values,
                            recommended_action="consolidate",
                        ))
                    else:
                        duplications.append(Duplication(
                            key=key,
                            files=file_paths,
                            values=values,
                            recommended_action="review",
                        ))

        return duplications

    def create_refactor_plan(self) -> RefactorPlan:
        """Create a plan to consolidate configs."""
        duplications = self.find_duplications()
        shared_config = {}
        files_to_modify = set()

        for dup in duplications:
            if dup.recommended_action == "consolidate":
                shared_config[dup.key] = dup.values[0]
                files_to_modify.update(dup.files)

        return RefactorPlan(
            duplications=duplications,
            shared_config=shared_config,
            files_to_modify=list(files_to_modify),
            files_to_create=["shared-config.json"],
        )

    def _find_package(self, dirpath: str) -> str:
        """Find the package name for a directory."""
        path = Path(dirpath)
        # Look for package.json or pyproject.toml
        for parent in [path] + list(path.parents):
            pkg_json = parent / "package.json"
            if pkg_json.exists():
                try:
                    with open(pkg_json, "r") as f:
                        data = json.load(f)
                    return data.get("name", parent.name)
                except (json.JSONDecodeError, OSError):
                    return parent.name
        return path.name
