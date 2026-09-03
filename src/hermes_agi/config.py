"""Configuration management for Hermes AGI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Config:
    """Harness configuration."""
    project_path: str = "."
    plugins_dir: str = "plugins"
    profiles_dir: str = "~/.hermes/profiles"
    state_dir: str = "state"
    log_level: str = "INFO"
    debug: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def load_config(project_path: str | None = None) -> Config:
    """Load configuration."""
    if project_path is None:
        project_path = os.getcwd()
    
    project_path = Path(project_path)
    
    # Find project root
    while project_path != project_path.parent:
        if (project_path / "pyproject.toml").exists():
            break
        project_path = project_path.parent
    
    profiles_dir = Path.home() / ".hermes" / "profiles"
    
    return Config(
        project_path=str(project_path),
        plugins_dir=str(project_path / "plugins"),
        profiles_dir=str(profiles_dir),
        state_dir=str(project_path / "state"),
    )
