#!/usr/bin/env python3
"""QA harness for ChainForge project."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))


def check_file(path: str) -> bool:
    full = os.path.join(ROOT, path)
    exists = os.path.isfile(full)
    print(f"{'OK' if exists else 'MISSING'}: {path}")
    return exists


def check_dir(path: str) -> bool:
    full = os.path.join(ROOT, path)
    exists = os.path.isdir(full)
    print(f"{'OK' if exists else 'MISSING'}: {path}/")
    return exists


def main() -> int:
    print("=" * 60)
    print("ChainForge QA Harness")
    print("=" * 60)

    required_files = [
        "README.md",
        "LICENSE",
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        ".gitignore",
        "scripts/self-test.py",
        "backend/app/__init__.py",
        "backend/app/main.py",
        "backend/app/api/routes.py",
        "backend/app/core/config.py",
        "backend/app/core/database.py",
        "backend/app/models/schemas.py",
        "backend/app/nodes/registry.py",
        "backend/app/services/engine.py",
        "backend/app/tests/test_api.py",
        "frontend/package.json",
        "frontend/vite.config.ts",
        "frontend/tsconfig.json",
        "frontend/public/index.html",
        "frontend/Dockerfile",
        "frontend/src/main.tsx",
        "frontend/src/App.tsx",
        "frontend/src/index.css",
        "frontend/src/types/index.ts",
        "frontend/src/services/api.ts",
        "frontend/src/store/index.ts",
        "frontend/src/components/Toolbar.tsx",
        "frontend/src/components/NodePalette.tsx",
        "frontend/src/components/PropertiesPanel.tsx",
        "frontend/src/nodes/CustomNode.tsx",
    ]

    required_dirs = [
        "backend/app/api",
        "backend/app/core",
        "backend/app/models",
        "backend/app/nodes",
        "backend/app/services",
        "backend/app/tests",
        "frontend/src/components",
        "frontend/src/nodes",
        "frontend/src/store",
        "frontend/src/services",
        "frontend/src/types",
    ]

    all_ok = True
    print("\n--- Required Files ---")
    for f in required_files:
        if not check_file(f):
            all_ok = False

    print("\n--- Required Directories ---")
    for d in required_dirs:
        if not check_dir(d):
            all_ok = False

    print("\n--- Self-Test ---")
    from app.nodes.registry import get_node_registry
    count = len(get_node_registry())
    print(f"{'OK' if count >= 100 else 'FAIL'}: {count} nodes registered (need 100+)")
    if count < 100:
        all_ok = False

    print("\n--- Node Categories ---")
    from app.nodes.registry import get_nodes_by_category
    cats = get_nodes_by_category()
    print(f"OK: {len(cats)} categories: {list(cats.keys())}")

    print("\n" + "=" * 60)
    if all_ok:
        print("QA HARNESS PASSED")
    else:
        print("QA HARNESS FAILED")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
