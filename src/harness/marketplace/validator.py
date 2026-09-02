"""Plugin validator stub."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = None

@dataclass
class SecurityScan:
    passed: bool
    issues: list[str] = None

class PluginValidator:
    def validate(self, path: str) -> ValidationResult:
        return ValidationResult(valid=True)

    def scan(self, path: str) -> SecurityScan:
        return SecurityScan(passed=True)
