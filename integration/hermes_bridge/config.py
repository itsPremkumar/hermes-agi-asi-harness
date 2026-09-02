"""
Config loader for Hermes Bridge.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def load_config(project_path: str | None = None) -> dict:
    """Load configuration for the bridge."""
    if project_path is None:
        project_path = os.getcwd()
    
    project_path = Path(project_path)
    
    # Find project root (where pyproject.toml is)
    while project_path != project_path.parent:
        if (project_path / "pyproject.toml").exists():
            break
        project_path = project_path.parent
    
    profiles_dir = Path.home() / ".hermes" / "profiles"
    
    return {
        "project_path": str(project_path),
        "plugins_dir": str(project_path / "plugins"),
        "profiles_dir": str(profiles_dir),
        "state_dir": str(project_path / "state"),
        "log_level": "INFO",
    }
