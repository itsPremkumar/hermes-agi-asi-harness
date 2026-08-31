"""Security Scanning - SAST, DAST, dependency scanning, secret detection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityFinding:
    rule_id: str
    severity: Severity
    message: str
    file: str
    line: int
    category: str

class SecretScanner:
    """Detect secrets in code."""
    
    PATTERNS = {
        "AWS Access Key": r"(?i)AKIA[0-9A-Z]{16}",
        "AWS Secret Key": r"(?i)AWS_SECRET_ACCESS_KEY['\"\s:=]+[A-Za-z0-9/+=]{40}",
        "GitHub Token": r"(?i)gh[pousr]_[A-Za-z0-9_]{36,}",
        "OpenAI API Key": r"sk-[A-Za-z0-9]{48}",
        "Private Key": r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        "Password in URL": r"://[^:]+:[^@]+@",
    }
    
    def scan(self, content: str, filename: str = "") -> list[SecurityFinding]:
        findings = []
        for name, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, content):
                findings.append(SecurityFinding(
                    rule_id=name.upper().replace(" ", "_"),
                    severity=Severity.CRITICAL,
                    message=f"Potential {name} exposed",
                    file=filename,
                    line=content[:match.start()].count('\n') + 1,
                    category="secret_exposure",
                ))
        return findings

class StaticAnalyzer:
    """Basic static analysis for common vulnerabilities."""
    
    RULES = [
        ("hardcoded_password", r'(?i)password\s*=\s*["\'][^"\']+["\']', Severity.HIGH),
        ("sql_injection", r'(?i)execute\s*\(\s*["\'].*%s', Severity.CRITICAL),
        ("command_injection", r'(?i)os\.system\s*\(', Severity.HIGH),
        ("eval_usage", r'eval\s*\(', Severity.HIGH),
        ("pickle_load", r'pickle\.load', Severity.MEDIUM),
        ("yaml_unsafe", r'yaml\.load\s*\([^,]+\)', Severity.MEDIUM),
        ("debug_true", r'DEBUG\s*=\s*True', Severity.LOW),
    ]
    
    def analyze(self, content: str, filename: str = "") -> list[SecurityFinding]:
        findings = []
        for rule_id, pattern, severity in self.RULES:
            for match in re.finditer(pattern, content):
                findings.append(SecurityFinding(
                    rule_id=rule_id,
                    severity=severity,
                    message=f"Potential {rule_id.replace('_', ' ')}",
                    file=filename,
                    line=content[:match.start()].count('\n') + 1,
                    category="static_analysis",
                ))
        return findings

class SecurityScanner:
    """Main security scanner combining all scanners."""
    
    def __init__(self):
        self.secret_scanner = SecretScanner()
        self.static_analyzer = StaticAnalyzer()
    
    def scan_content(self, content: str, filename: str = "") -> list[SecurityFinding]:
        findings = []
        findings.extend(self.secret_scanner.scan(content, filename))
        findings.extend(self.static_analyzer.analyze(content, filename))
        return findings
    
    def scan_file(self, filepath: str) -> list[SecurityFinding]:
        with open(filepath, errors='ignore') as f:
            return self.scan_content(f.read(), filepath)
    
    def scan_directory(self, directory: str) -> list[SecurityFinding]:
        import os
        findings = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.endswith(('.py', '.js', '.ts', '.go', '.java', '.rb')):
                    filepath = os.path.join(root, f)
                    findings.extend(self.scan_file(filepath))
        return findings
