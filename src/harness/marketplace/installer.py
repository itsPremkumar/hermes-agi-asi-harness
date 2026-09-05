"""Plugin installer stub."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InstallStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class InstallResult:
    status: InstallStatus
    message: str = ""

@dataclass
class UninstallResult:
    status: InstallStatus
    message: str = ""

class PluginInstaller:
    def install(self, path: str) -> InstallResult:
        return InstallResult(InstallStatus.SUCCESS)

    def uninstall(self, plugin_id: str) -> UninstallResult:
        return UninstallResult(InstallStatus.SUCCESS)
