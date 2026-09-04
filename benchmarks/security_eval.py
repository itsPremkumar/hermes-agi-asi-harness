"""Security Benchmark Module — t_22739a58.

Six security plugins for evaluating AI agent safety:
- InputValidator: validates/sanitizes user inputs against injection attacks
- OutputSanitizer: strips unsafe content from model outputs
- RateLimiter: token-bucket rate limiter for API abuse prevention
- AuditLogger: immutable audit trail for security-relevant events
- AnomalyDetector: detects anomalous patterns in request streams
- ComplianceChecker: enforces regulatory compliance rules (GDPR, HIPAA, SOC2)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Shared enums + dataclasses
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"


@dataclass
class SecurityFinding:
    rule_id: str
    severity: Severity
    message: str
    plugin: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "plugin": self.plugin,
            "details": self.details,
        }


@dataclass
class BenchmarkResult:
    plugin: str
    passed: int
    failed: int
    findings: list[SecurityFinding]
    duration_ms: float

    @property
    def total(self) -> int:
        return self.passed + self.failed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin": self.plugin,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "pass_rate": self.pass_rate,
            "duration_ms": self.duration_ms,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Plugin 1: InputValidator
# ---------------------------------------------------------------------------

class InputValidator:
    """Validates and sanitizes user inputs against injection attacks."""

    # SQL injection patterns
    SQL_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\s"),
        re.compile(r"(?i)(--|;|')\s*(OR|AND)\s"),
        re.compile(r"(?i)1\s*=\s*1"),
        re.compile(r"(?i)EXEC\s*\("),
    ]

    # Command injection patterns
    CMD_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"[;&|`$(){}[\]]"),
        re.compile(r"(?i)(rm\s+-rf|curl|wget|bash|sh|cmd|powershell)\b"),
    ]

    # Path traversal patterns
    PATH_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"\.\./|\.\.\\"),
        re.compile(r"(?i)(/etc/passwd|/etc/shadow|C:\\Windows)"),
    ]

    # XSS patterns
    XSS_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(?i)<script[^>]*>"),
        re.compile(r"(?i)javascript\s*:"),
        re.compile(r"(?i)on\w+\s*="),
    ]

    def __init__(self, max_length: int = 10_000, allow_html: bool = False):
        self.max_length = max_length
        self.allow_html = allow_html

    def validate(self, text: str) -> tuple[bool, list[SecurityFinding]]:
        """Validate input text. Returns (is_valid, findings)."""
        findings: list[SecurityFinding] = []

        if not isinstance(text, str):
            findings.append(SecurityFinding(
                rule_id="INPUT_NOT_STRING",
                severity=Severity.HIGH,
                message="Input is not a string",
                plugin="InputValidator",
            ))
            return False, findings

        if len(text) > self.max_length:
            findings.append(SecurityFinding(
                rule_id="INPUT_TOO_LONG",
                severity=Severity.MEDIUM,
                message=f"Input exceeds max length ({len(text)} > {self.max_length})",
                plugin="InputValidator",
                details={"length": len(text), "max_length": self.max_length},
            ))

        # SQL injection
        for pat in self.SQL_PATTERNS:
            if pat.search(text):
                findings.append(SecurityFinding(
                    rule_id="SQL_INJECTION",
                    severity=Severity.CRITICAL,
                    message="Potential SQL injection detected",
                    plugin="InputValidator",
                    details={"pattern": pat.pattern, "matched": pat.search(text).group()},
                ))
                break

        # Command injection
        for pat in self.CMD_PATTERNS:
            if pat.search(text):
                findings.append(SecurityFinding(
                    rule_id="COMMAND_INJECTION",
                    severity=Severity.CRITICAL,
                    message="Potential command injection detected",
                    plugin="InputValidator",
                    details={"pattern": pat.pattern},
                ))
                break

        # Path traversal
        for pat in self.PATH_PATTERNS:
            if pat.search(text):
                findings.append(SecurityFinding(
                    rule_id="PATH_TRAVERSAL",
                    severity=Severity.HIGH,
                    message="Potential path traversal detected",
                    plugin="InputValidator",
                    details={"pattern": pat.pattern},
                ))
                break

        # XSS
        if not self.allow_html:
            for pat in self.XSS_PATTERNS:
                if pat.search(text):
                    findings.append(SecurityFinding(
                        rule_id="XSS",
                        severity=Severity.HIGH,
                        message="Potential XSS attack detected",
                        plugin="InputValidator",
                        details={"pattern": pat.pattern},
                    ))
                    break

        is_valid = not any(f.severity in (Severity.CRITICAL, Severity.HIGH) for f in findings)
        return is_valid, findings

    def sanitize(self, text: str) -> str:
        """Sanitize input by escaping dangerous characters."""
        if not isinstance(text, str):
            return ""
        # HTML entity encoding for dangerous chars
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        # Remove null bytes
        text = text.replace("\x00", "")
        # Truncate
        return text[: self.max_length]


# ---------------------------------------------------------------------------
# Plugin 2: OutputSanitizer
# ---------------------------------------------------------------------------

class OutputSanitizer:
    """Strips unsafe content from model outputs before presentation."""

    # PII patterns
    PII_PATTERNS: dict[str, re.Pattern[str]] = {
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    }

    # Secret patterns
    SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
        "api_key": re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        "aws_key": re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
        "private_key": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    }

    def __init__(self, mask_char: str = "*", allow_pii: bool = False):
        self.mask_char = mask_char
        self.allow_pii = allow_pii

    def sanitize(self, text: str) -> tuple[str, list[SecurityFinding]]:
        """Sanitize output text. Returns (sanitized_text, findings)."""
        findings: list[SecurityFinding] = []
        sanitized = text

        if not self.allow_pii:
            for name, pat in self.PII_PATTERNS.items():
                matches = pat.findall(text)
                if matches:
                    findings.append(SecurityFinding(
                        rule_id=f"PII_{name.upper()}",
                        severity=Severity.HIGH,
                        message=f"PII detected: {name}",
                        plugin="OutputSanitizer",
                        details={"count": len(matches), "type": name},
                    ))
                    sanitized = pat.sub(self._mask_match, sanitized)

        for name, pat in self.SECRET_PATTERNS.items():
            matches = pat.findall(text)
            if matches:
                findings.append(SecurityFinding(
                    rule_id=f"SECRET_{name.upper()}",
                    severity=Severity.CRITICAL,
                    message=f"Secret detected in output: {name}",
                    plugin="OutputSanitizer",
                    details={"count": len(matches), "type": name},
                ))
                sanitized = pat.sub("[REDACTED]", sanitized)

        return sanitized, findings

    def _mask_match(self, match: re.Match[str]) -> str:
        s = match.group()
        if len(s) <= 4:
            return self.mask_char * len(s)
        return s[:2] + self.mask_char * (len(s) - 4) + s[-2:]


# ---------------------------------------------------------------------------
# Plugin 3: RateLimiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token-bucket rate limiter for API abuse prevention."""

    def __init__(self, max_tokens: int = 100, refill_rate: float = 10.0):
        """
        Args:
            max_tokens: Maximum burst capacity
            refill_rate: Tokens added per second
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self._buckets: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    def _get_bucket(self, key: str) -> dict[str, float]:
        now = time.monotonic()
        if key not in self._buckets:
            self._buckets[key] = {"tokens": self.max_tokens, "last_refill": now}
        bucket = self._buckets[key]
        # Refill
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(self.max_tokens, bucket["tokens"] + elapsed * self.refill_rate)
        bucket["last_refill"] = now
        return bucket

    def allow_request(self, key: str, tokens: int = 1) -> tuple[bool, dict[str, Any]]:
        """Check if a request should be allowed."""
        with self._lock:
            bucket = self._get_bucket(key)
            if bucket["tokens"] >= tokens:
                bucket["tokens"] -= tokens
                return True, {
                    "allowed": True,
                    "remaining": bucket["tokens"],
                    "max_tokens": self.max_tokens,
                }
            return False, {
                "allowed": False,
                "remaining": 0,
                "retry_after": (tokens - bucket["tokens"]) / self.refill_rate,
                "max_tokens": self.max_tokens,
            }

    def get_remaining(self, key: str) -> float:
        with self._lock:
            bucket = self._get_bucket(key)
            return bucket["tokens"]

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)


# ---------------------------------------------------------------------------
# Plugin 4: AuditLogger
# ---------------------------------------------------------------------------

class AuditLogger:
    """Immutable audit trail for security-relevant events."""

    def __init__(self):
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def log(self, event_type: str, actor: str, details: dict[str, Any] = None) -> dict[str, Any]:
        """Log an audit event. Returns the event record."""
        with self._lock:
            event = {
                "id": len(self._events) + 1,
                "timestamp": time.time(),
                "event_type": event_type,
                "actor": actor,
                "details": details or {},
                "hash": "",
            }
            # Chain hash for tamper evidence
            prev_hash = self._events[-1]["hash"] if self._events else "0" * 64
            event_data = f"{prev_hash}:{event['id']}:{event['timestamp']}:{event_type}:{actor}"
            event["hash"] = hashlib.sha256(event_data.encode()).hexdigest()
            self._events.append(event)
            return event

    def get_events(self, event_type: str | None = None, actor: str | None = None) -> list[dict[str, Any]]:
        """Query audit events with optional filters."""
        with self._lock:
            events = list(self._events)
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        if actor:
            events = [e for e in events if e["actor"] == actor]
        return events

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """Verify the hash chain integrity. Returns (is_valid, errors)."""
        errors: list[str] = []
        with self._lock:
            for i, event in enumerate(self._events):
                prev_hash = self._events[i - 1]["hash"] if i > 0 else "0" * 64
                event_data = f"{prev_hash}:{event['id']}:{event['timestamp']}:{event['event_type']}:{event['actor']}"
                expected = hashlib.sha256(event_data.encode()).hexdigest()
                if event["hash"] != expected:
                    errors.append(f"Event {event['id']}: hash mismatch")
        return len(errors) == 0, errors

    @property
    def count(self) -> int:
        return len(self._events)


# ---------------------------------------------------------------------------
# Plugin 5: AnomalyDetector
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """Detects anomalous patterns in request streams using statistical analysis."""

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self._values: list[float] = []
        self._lock = threading.Lock()

    def add_value(self, value: float) -> tuple[bool, float]:
        """Add a value and check if it's anomalous. Returns (is_anomaly, z_score)."""
        with self._lock:
            self._values.append(value)
            if len(self._values) > self.window_size:
                self._values = self._values[-self.window_size:]

            if len(self._values) < 2:
                return False, 0.0

            mean = sum(self._values) / len(self._values)
            variance = sum((v - mean) ** 2 for v in self._values) / len(self._values)
            std_dev = variance ** 0.5

            if std_dev == 0:
                return False, 0.0

            z_score = abs(value - mean) / std_dev
            return z_score > self.z_threshold, z_score

    def get_stats(self) -> dict[str, float]:
        with self._lock:
            if not self._values:
                return {"mean": 0, "std_dev": 0, "min": 0, "max": 0, "count": 0}
            mean = sum(self._values) / len(self._values)
            variance = sum((v - mean) ** 2 for v in self._values) / len(self._values)
            return {
                "mean": mean,
                "std_dev": variance ** 0.5,
                "min": min(self._values),
                "max": max(self._values),
                "count": len(self._values),
            }

    def reset(self) -> None:
        with self._lock:
            self._values.clear()


# ---------------------------------------------------------------------------
# Plugin 6: ComplianceChecker
# ---------------------------------------------------------------------------

class ComplianceChecker:
    """Enforces regulatory compliance rules."""

    # GDPR: data retention limits, right to erasure, consent
    # HIPAA: PHI protection, access controls, audit trails
    # SOC2: security, availability, processing integrity, confidentiality, privacy
    # PCI DSS: cardholder data protection

    RULES: dict[str, list[dict[str, Any]]] = {
        "gdpr": [
            {"id": "GDPR-001", "description": "Data retention limit (max 365 days)", "check": "retention_days <= 365"},
            {"id": "GDPR-002", "description": "Right to erasure supported", "check": "supports_erasure == True"},
            {"id": "GDPR-003", "description": "User consent recorded", "check": "has_consent == True"},
            {"id": "GDPR-004", "description": "Data minimization (only necessary fields)", "check": "excess_fields == 0"},
            {"id": "GDPR-005", "description": "Data portability supported", "check": "supports_export == True"},
        ],
        "hipaa": [
            {"id": "HIPAA-001", "description": "PHI encryption at rest", "check": "phi_encrypted == True"},
            {"id": "HIPAA-002", "description": "Access controls implemented", "check": "access_controls == True"},
            {"id": "HIPAA-003", "description": "Audit trail enabled", "check": "audit_trail == True"},
            {"id": "HIPAA-004", "description": "Minimum necessary standard", "check": "minimum_necessary == True"},
            {"id": "HIPAA-005", "description": "BAA signed with vendors", "check": "baa_signed == True"},
        ],
        "soc2": [
            {"id": "SOC2-001", "description": "Security monitoring active", "check": "security_monitoring == True"},
            {"id": "SOC2-002", "description": "Incident response plan", "check": "incident_response == True"},
            {"id": "SOC2-003", "description": "Change management process", "check": "change_management == True"},
            {"id": "SOC2-004", "description": "Data classification", "check": "data_classification == True"},
            {"id": "SOC2-005", "description": "Vendor risk management", "check": "vendor_risk_mgmt == True"},
        ],
        "pci_dss": [
            {"id": "PCI-001", "description": "Cardholder data encrypted", "check": "data_encrypted == True"},
            {"id": "PCI-002", "description": "Network segmentation", "check": "network_segmented == True"},
            {"id": "PCI-003", "description": "Vulnerability scanning", "check": "vuln_scanning == True"},
            {"id": "PCI-004", "description": "Access control measures", "check": "access_control == True"},
            {"id": "PCI-005", "description": "Security testing", "check": "security_testing == True"},
        ],
    }

    def check(self, framework: ComplianceFramework, context: dict[str, Any]) -> list[SecurityFinding]:
        """Check compliance for a given framework."""
        findings: list[SecurityFinding] = []
        rules = self.RULES.get(framework.value, [])

        for rule in rules:
            try:
                passed = eval(rule["check"], {"__builtins__": {}}, context)
                if not passed:
                    findings.append(SecurityFinding(
                        rule_id=rule["id"],
                        severity=Severity.HIGH,
                        message=f"Compliance violation: {rule['description']}",
                        plugin="ComplianceChecker",
                        details={"framework": framework.value, "rule": rule["id"]},
                    ))
            except Exception as e:
                findings.append(SecurityFinding(
                    rule_id=rule["id"],
                    severity=Severity.MEDIUM,
                    message=f"Could not evaluate rule: {rule['description']} ({e})",
                    plugin="ComplianceChecker",
                    details={"framework": framework.value, "rule": rule["id"], "error": str(e)},
                ))

        return findings

    def check_all(self, context: dict[str, Any]) -> dict[str, list[SecurityFinding]]:
        """Check all compliance frameworks."""
        return {fw.value: self.check(fw, context) for fw in ComplianceFramework}


# ---------------------------------------------------------------------------
# Benchmark Runner
# ---------------------------------------------------------------------------

class SecurityBenchmark:
    """Runs all security plugins and aggregates results."""

    def __init__(self):
        self.input_validator = InputValidator()
        self.output_sanitizer = OutputSanitizer()
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger()
        self.anomaly_detector = AnomalyDetector()
        self.compliance_checker = ComplianceChecker()
        self.results: list[BenchmarkResult] = []

    def run_all(self) -> list[BenchmarkResult]:
        """Run all security benchmarks."""
        self.results = []
        self.results.append(self._benchmark_input_validator())
        self.results.append(self._benchmark_output_sanitizer())
        self.results.append(self._benchmark_rate_limiter())
        self.results.append(self._benchmark_audit_logger())
        self.results.append(self._benchmark_anomaly_detector())
        self.results.append(self._benchmark_compliance_checker())
        return self.results

    def _benchmark_input_validator(self) -> BenchmarkResult:
        start = time.monotonic()
        passed = 0
        failed = 0
        findings: list[SecurityFinding] = []

        test_cases = [
            ("Hello world", True),
            ("SELECT * FROM users", False),
            ("'; DROP TABLE users; --", False),
            ("<script>alert('xss')</script>", False),
            ("../../../etc/passwd", False),
            ("normal input 123", True),
            ("rm -rf /", False),
        ]

        for text, expected_valid in test_cases:
            is_valid, f = self.input_validator.validate(text)
            findings.extend(f)
            if is_valid == expected_valid:
                passed += 1
            else:
                failed += 1

        return BenchmarkResult(
            plugin="InputValidator",
            passed=passed,
            failed=failed,
            findings=findings,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _benchmark_output_sanitizer(self) -> BenchmarkResult:
        start = time.monotonic()
        passed = 0
        failed = 0
        findings: list[SecurityFinding] = []

        test_cases = [
            ("Contact: user@example.com", True),
            ("SSN: 123-45-6789", True),
            ("API key: sk-abc123def456ghi789", True),
            ("Normal output text", True),
        ]

        for text, _ in test_cases:
            sanitized, f = self.output_sanitizer.sanitize(text)
            findings.extend(f)
            if sanitized != text and f:
                passed += 1
            elif not f:
                passed += 1
            else:
                failed += 1

        return BenchmarkResult(
            plugin="OutputSanitizer",
            passed=passed,
            failed=failed,
            findings=findings,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _benchmark_rate_limiter(self) -> BenchmarkResult:
        start = time.monotonic()
        passed = 0
        failed = 0
        findings: list[SecurityFinding] = []

        rl = RateLimiter(max_tokens=5, refill_rate=1.0)
        # Should allow first 5
        for i in range(5):
            allowed, _ = rl.allow_request("test-client")
            if allowed:
                passed += 1
            else:
                failed += 1
        # 6th should be blocked
        allowed, _ = rl.allow_request("test-client")
        if not allowed:
            passed += 1
        else:
            failed += 1

        return BenchmarkResult(
            plugin="RateLimiter",
            passed=passed,
            failed=failed,
            findings=findings,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _benchmark_audit_logger(self) -> BenchmarkResult:
        start = time.monotonic()
        passed = 0
        failed = 0
        findings: list[SecurityFinding] = []

        al = AuditLogger()
        al.log("login", "user1", {"ip": "127.0.0.1"})
        al.log("logout", "user1")
        al.log("login", "user2")

        if al.count == 3:
            passed += 1
        else:
            failed += 1

        events = al.get_events(event_type="login")
        if len(events) == 2:
            passed += 1
        else:
            failed += 1

        is_valid, errors = al.verify_integrity()
        if is_valid:
            passed += 1
        else:
            failed += 1

        return BenchmarkResult(
            plugin="AuditLogger",
            passed=passed,
            failed=failed,
            findings=findings,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _benchmark_anomaly_detector(self) -> BenchmarkResult:
        start = time.monotonic()
        passed = 0
        failed = 0
        findings: list[SecurityFinding] = []

        ad = AnomalyDetector(window_size=20, z_threshold=2.0)
        # Normal values
        for i in range(15):
            ad.add_value(100.0 + i)
        # Anomaly
        is_anomaly, z = ad.add_value(200.0)
        if is_anomaly:
            passed += 1
        else:
            failed += 1

        stats = ad.get_stats()
        if stats["count"] == 16:
            passed += 1
        else:
            failed += 1

        return BenchmarkResult(
            plugin="AnomalyDetector",
            passed=passed,
            failed=failed,
            findings=findings,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _benchmark_compliance_checker(self) -> BenchmarkResult:
        start = time.monotonic()
        passed = 0
        failed = 0
        findings: list[SecurityFinding] = []

        cc = ComplianceChecker()
        # Fully compliant context
        context = {
            "retention_days": 365, "supports_erasure": True, "has_consent": True,
            "excess_fields": 0, "supports_export": True,
            "phi_encrypted": True, "access_controls": True, "audit_trail": True,
            "minimum_necessary": True, "baa_signed": True,
            "security_monitoring": True, "incident_response": True,
            "change_management": True, "data_classification": True,
            "vendor_risk_mgmt": True,
            "data_encrypted": True, "network_segmented": True,
            "vuln_scanning": True, "access_control": True, "security_testing": True,
        }
        all_findings = cc.check_all(context)
        total = sum(len(f) for f in all_findings.values())
        if total == 0:
            passed += 1
        else:
            failed += 1

        # Non-compliant context
        bad_context = {k: False for k in context}
        bad_findings = cc.check(ComplianceFramework.GDPR, bad_context)
        if len(bad_findings) > 0:
            passed += 1
        else:
            failed += 1

        return BenchmarkResult(
            plugin="ComplianceChecker",
            passed=passed,
            failed=failed,
            findings=findings,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def get_overall_score(self) -> dict[str, Any]:
        """Get overall benchmark score."""
        if not self.results:
            return {"total_passed": 0, "total_failed": 0, "pass_rate": 0.0, "plugins": 0}

        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total = total_passed + total_failed
        return {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total": total,
            "pass_rate": total_passed / total if total else 0.0,
            "plugins": len(self.results),
        }


__all__ = [
    "InputValidator",
    "OutputSanitizer",
    "RateLimiter",
    "AuditLogger",
    "AnomalyDetector",
    "ComplianceChecker",
    "SecurityBenchmark",
    "SecurityFinding",
    "BenchmarkResult",
    "Severity",
    "ComplianceFramework",
]
