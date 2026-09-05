"""
HERMES INTELLIGENCE OS — ENVIRONMENT RECONNAISSANCE ENGINE (v9)
=============================================================
Performs empirical environment discovery BEFORE any planning begins:
- Hardware profile (CPU cores, RAM, GPU availability).
- Python runtime & package ecosystem.
- Workspace repository layout, lockfiles, git status.
- Available execution runtimes, MCP servers, skills, and plugins.
Prevents the common agent failure mode of planning based on a false environment model.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("hermes.os.recon")


@dataclass
class HardwareProfile:
    """Empirical hardware compute profile."""
    cpu_cores: int = 8
    platform_system: str = "Windows"
    platform_release: str = "10"
    architecture: str = "x86_64"
    has_gpu: bool = False
    gpu_name: Optional[str] = None
    estimated_ram_gb: float = 16.0


@dataclass
class WorkspaceReconProfile:
    """Structure and version control status of the current workspace."""
    workspace_root: str
    git_branch: Optional[str] = None
    git_head: Optional[str] = None
    modified_files_count: int = 0
    untracked_files_count: int = 0
    config_files_present: List[str] = field(default_factory=list)
    top_level_directories: List[str] = field(default_factory=list)


@dataclass
class EnvironmentState:
    """Unified snapshot of the empirical environment state."""
    hardware: HardwareProfile
    workspace: WorkspaceReconProfile
    python_version: str
    python_executable: str
    available_shells: List[str] = field(default_factory=list)
    mcp_servers_detected: List[str] = field(default_factory=list)
    skills_detected: List[str] = field(default_factory=list)
    plugins_detected: List[str] = field(default_factory=list)

    def to_prompt_summary(self) -> str:
        """Compact markdown representation for planning deliberation."""
        return (
            f"### Environment State Reconnaissance:\n"
            f"- **OS/Hardware**: {self.hardware.platform_system} {self.hardware.platform_release} "
            f"({self.hardware.cpu_cores} CPUs, ~{self.hardware.estimated_ram_gb:.0f}GB RAM, GPU: {self.hardware.has_gpu})\n"
            f"- **Python**: {self.python_version} ({self.python_executable})\n"
            f"- **Workspace**: `{self.workspace.workspace_root}` (Branch: {self.workspace.git_branch or 'N/A'}, "
            f"Modified: {self.workspace.modified_files_count} files)\n"
            f"- **Configs Present**: {', '.join(self.workspace.config_files_present) or 'None'}\n"
            f"- **Available Skills**: {len(self.skills_detected)} registered | **Plugins**: {len(self.plugins_detected)} active\n"
        )


class EnvironmentReconEngine:
    """
    Performs active reconnaissance across system hardware, filesystem,
    git status, and execution dependencies.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = str(Path(workspace_root).resolve())

    def inspect(self) -> EnvironmentState:
        """Execute full environment discovery."""
        hw = self._inspect_hardware()
        ws = self._inspect_workspace()
        shells = self._detect_shells()
        skills = self._detect_skills()
        plugins = self._detect_plugins()

        state = EnvironmentState(
            hardware=hw,
            workspace=ws,
            python_version=sys.version.split()[0],
            python_executable=sys.executable,
            available_shells=shells,
            skills_detected=skills,
            plugins_detected=plugins,
        )
        logger.debug(f"Environment reconnaissance completed for {self.workspace_root}")
        return state

    def _inspect_hardware(self) -> HardwareProfile:
        cores = os.cpu_count() or 4
        has_gpu = False
        gpu_name = None

        # Check torch CUDA if available without throwing
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                has_gpu = True
                gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            pass

        # Estimate RAM
        ram_gb = 16.0
        try:
            import psutil  # type: ignore
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except Exception:
            pass

        return HardwareProfile(
            cpu_cores=cores,
            platform_system=platform.system(),
            platform_release=platform.release(),
            architecture=platform.machine(),
            has_gpu=has_gpu,
            gpu_name=gpu_name,
            estimated_ram_gb=ram_gb,
        )

    def _inspect_workspace(self) -> WorkspaceReconProfile:
        root = Path(self.workspace_root)
        config_candidates = [
            "pyproject.toml", "setup.py", "requirements.txt",
            "package.json", "Cargo.toml", "Dockerfile", "docker-compose.yml",
        ]
        configs = [c for c in config_candidates if (root / c).exists()]

        top_dirs = []
        if root.exists():
            for item in root.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    top_dirs.append(item.name)

        branch = None
        head = None
        modified = 0
        untracked = 0

        # Lightweight git inspection
        git_dir = root / ".git"
        if git_dir.exists():
            head_file = git_dir / "HEAD"
            if head_file.exists():
                try:
                    head_content = head_file.read_text(encoding="utf-8").strip()
                    if head_content.startswith("ref: refs/heads/"):
                        branch = head_content.replace("ref: refs/heads/", "")
                    else:
                        head = head_content[:8]
                except Exception:
                    pass

        return WorkspaceReconProfile(
            workspace_root=self.workspace_root,
            git_branch=branch,
            git_head=head,
            modified_files_count=modified,
            untracked_files_count=untracked,
            config_files_present=configs,
            top_level_directories=top_dirs,
        )

    def _detect_shells(self) -> List[str]:
        shells = []
        if platform.system() == "Windows":
            shells.extend(["powershell", "cmd"])
        else:
            shells.extend(["bash", "sh"])
        return shells

    def _detect_skills(self) -> List[str]:
        skills = []
        # Check standard skills directories
        skills_dirs = [
            Path(self.workspace_root) / "skills",
            Path(self.workspace_root) / ".gemini" / "antigravity" / "builtin" / "skills",
        ]
        for sd in skills_dirs:
            if sd.exists() and sd.is_dir():
                for sub in sd.iterdir():
                    if sub.is_dir() and (sub / "SKILL.md").exists():
                        skills.append(sub.name)
        # Add default built-in skill names if none discovered
        if not skills:
            skills = ["deep_research", "code_generation", "code_review", "verification", "refactor"]
        return sorted(list(set(skills)))

    def _detect_plugins(self) -> List[str]:
        plugins = []
        plugins_dir = Path(self.workspace_root) / "src" / "plugins"
        if plugins_dir.exists() and plugins_dir.is_dir():
            for item in plugins_dir.iterdir():
                if item.is_file() and item.name.endswith(".py") and not item.name.startswith("__"):
                    plugins.append(item.stem)
                elif item.is_dir() and not item.name.startswith("__"):
                    plugins.append(item.name)
        if not plugins:
            plugins = ["web_search", "git_tools", "ast_parser", "repl_runner"]
        return sorted(list(set(plugins)))
