"""Tests for benchmark_security.py — 40+ tests across all 6 security plugins."""

from __future__ import annotations

import time
import pytest
from src.security.benchmark_security import (
    InputValidator,
    OutputSanitizer,
    RateLimiter,
    AuditLogger,
    AnomalyDetector,
    ComplianceChecker,
    SecurityBenchmark,
    SecurityFinding,
    BenchmarkResult,
    Severity,
    ComplianceFramework,
)


# ===========================================================================
# InputValidator Tests (10 tests)
# ===========================================================================

class TestInputValidator:
    def test_valid_input(self):
        v = InputValidator()
        is_valid, findings = v.validate("Hello world")
        assert is_valid is True
        assert len(findings) == 0

    def test_sql_injection_select(self):
        v = InputValidator()
        is_valid, findings = v.validate("SELECT * FROM users")
        assert is_valid is False
        assert any(f.rule_id == "SQL_INJECTION" for f in findings)

    def test_sql_injection_drop(self):
        v = InputValidator()
        is_valid, findings = v.validate("'; DROP TABLE users; --")
        assert is_valid is False
        assert any(f.rule_id == "SQL_INJECTION" for f in findings)

    def test_sql_injection_union(self):
        v = InputValidator()
        is_valid, findings = v.validate("1 UNION SELECT * FROM passwords")
        assert is_valid is False
        assert any(f.rule_id == "SQL_INJECTION" for f in findings)

    def test_command_injection(self):
        v = InputValidator()
        is_valid, findings = v.validate("hello; rm -rf /")
        assert is_valid is False
        assert any(f.rule_id == "COMMAND_INJECTION" for f in findings)

    def test_path_traversal(self):
        v = InputValidator()
        is_valid, findings = v.validate("../../../etc/passwd")
        assert is_valid is False
        assert any(f.rule_id == "PATH_TRAVERSAL" for f in findings)

    def test_xss_script(self):
        v = InputValidator()
        is_valid, findings = v.validate("<script>alert('xss')</script>")
        assert is_valid is False
        assert any(f.rule_id == "XSS" for f in findings)

    def test_input_too_long(self):
        v = InputValidator(max_length=10)
        is_valid, findings = v.validate("a" * 11)
        assert any(f.rule_id == "INPUT_TOO_LONG" for f in findings)

    def test_non_string_input(self):
        v = InputValidator()
        is_valid, findings = v.validate(12345)
        assert is_valid is False
        assert any(f.rule_id == "INPUT_NOT_STRING" for f in findings)

    def test_sanitize_html_entities(self):
        v = InputValidator()
        sanitized = v.sanitize('<script>alert("xss")</script>')
        assert "<script>" not in sanitized
        assert "&lt;" in sanitized

    def test_sanitize_truncates(self):
        v = InputValidator(max_length=5)
        sanitized = v.sanitize("hello world")
        assert len(sanitized) == 5

    def test_sanitize_non_string(self):
        v = InputValidator()
        assert v.sanitize(None) == ""
        assert v.sanitize(123) == ""


# ===========================================================================
# OutputSanitizer Tests (8 tests)
# ===========================================================================

class TestOutputSanitizer:
    def test_pii_email(self):
        s = OutputSanitizer()
        sanitized, findings = s.sanitize("Contact: user@example.com")
        assert any(f.rule_id == "PII_EMAIL" for f in findings)
        assert "user@example.com" not in sanitized

    def test_pii_ssn(self):
        s = OutputSanitizer()
        sanitized, findings = s.sanitize("SSN: 123-45-6789")
        assert any(f.rule_id == "PII_SSN" for f in findings)
        assert "123-45-6789" not in sanitized

    def test_secret_api_key(self):
        s = OutputSanitizer()
        sanitized, findings = s.sanitize("api_key=ABC123DEF456GHI789")
        assert any(f.rule_id == "SECRET_API_KEY" for f in findings)
        assert "ABC123DEF456GHI789" not in sanitized

    def test_secret_aws_key(self):
        s = OutputSanitizer()
        sanitized, findings = s.sanitize("AWS key: AKIAIOSFODNN7EXAMPLE")
        assert any(f.rule_id == "SECRET_AWS_KEY" for f in findings)

    def test_no_pii_clean_text(self):
        s = OutputSanitizer()
        sanitized, findings = s.sanitize("This is a normal output with no PII.")
        assert len(findings) == 0
        assert sanitized == "This is a normal output with no PII."

    def test_allow_pii(self):
        s = OutputSanitizer(allow_pii=True)
        sanitized, findings = s.sanitize("Email: test@test.com")
        assert len(findings) == 0

    def test_mask_preserves_length(self):
        s = OutputSanitizer()
        sanitized, _ = s.sanitize("Phone: 555-123-4567")
        # Masked phone should still have same length
        assert len(sanitized) == len("Phone: 555-123-4567")

    def test_multiple_pii(self):
        s = OutputSanitizer()
        text = "Email: a@b.com, SSN: 111-22-3333, Phone: 555-555-5555"
        sanitized, findings = s.sanitize(text)
        assert len(findings) >= 3


# ===========================================================================
# RateLimiter Tests (7 tests)
# ===========================================================================

class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_tokens=5, refill_rate=1.0)
        for _ in range(5):
            allowed, _ = rl.allow_request("client1")
            assert allowed is True

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_tokens=3, refill_rate=0.1)
        for _ in range(3):
            rl.allow_request("client1")
        allowed, info = rl.allow_request("client1")
        assert allowed is False
        assert info["allowed"] is False

    def test_separate_buckets(self):
        rl = RateLimiter(max_tokens=1, refill_rate=0.1)
        allowed1, _ = rl.allow_request("client1")
        allowed2, _ = rl.allow_request("client2")
        assert allowed1 is True
        assert allowed2 is True

    def test_remaining_decreases(self):
        rl = RateLimiter(max_tokens=10, refill_rate=0.0)
        rl.allow_request("client1", tokens=3)
        remaining = rl.get_remaining("client1")
        assert remaining == 7.0

    def test_reset(self):
        rl = RateLimiter(max_tokens=1, refill_rate=0.1)
        rl.allow_request("client1")
        rl.reset("client1")
        allowed, _ = rl.allow_request("client1")
        assert allowed is True

    def test_retry_after(self):
        rl = RateLimiter(max_tokens=1, refill_rate=1.0)
        rl.allow_request("client1")
        allowed, info = rl.allow_request("client1", tokens=2)
        assert allowed is False
        assert "retry_after" in info
        assert info["retry_after"] > 0

    def test_multiple_tokens(self):
        rl = RateLimiter(max_tokens=10, refill_rate=0.0)
        allowed, info = rl.allow_request("client1", tokens=5)
        assert allowed is True
        assert info["remaining"] == 5.0


# ===========================================================================
# AuditLogger Tests (6 tests)
# ===========================================================================

class TestAuditLogger:
    def test_log_event(self):
        al = AuditLogger()
        event = al.log("login", "user1", {"ip": "127.0.0.1"})
        assert event["id"] == 1
        assert event["event_type"] == "login"
        assert event["actor"] == "user1"

    def test_event_count(self):
        al = AuditLogger()
        al.log("login", "user1")
        al.log("logout", "user1")
        al.log("login", "user2")
        assert al.count == 3

    def test_filter_by_type(self):
        al = AuditLogger()
        al.log("login", "user1")
        al.log("logout", "user1")
        al.log("login", "user2")
        events = al.get_events(event_type="login")
        assert len(events) == 2

    def test_filter_by_actor(self):
        al = AuditLogger()
        al.log("login", "user1")
        al.log("login", "user2")
        al.log("logout", "user1")
        events = al.get_events(actor="user1")
        assert len(events) == 2

    def test_integrity_valid(self):
        al = AuditLogger()
        al.log("login", "user1")
        al.log("logout", "user1")
        is_valid, errors = al.verify_integrity()
        assert is_valid is True
        assert len(errors) == 0

    def test_hash_chain(self):
        al = AuditLogger()
        e1 = al.log("login", "user1")
        e2 = al.log("logout", "user1")
        # Each event's hash should be different
        assert e1["hash"] != e2["hash"]
        # Hash should be 64 chars (SHA-256 hex)
        assert len(e1["hash"]) == 64


# ===========================================================================
# AnomalyDetector Tests (6 tests)
# ===========================================================================

class TestAnomalyDetector:
    def test_normal_values_not_anomaly(self):
        ad = AnomalyDetector(window_size=20, z_threshold=3.0)
        for i in range(10):
            is_anomaly, _ = ad.add_value(100.0)
        assert is_anomaly is False

    def test_extreme_value_is_anomaly(self):
        ad = AnomalyDetector(window_size=20, z_threshold=2.0)
        for i in range(15):
            ad.add_value(100.0)
        is_anomaly, z = ad.add_value(200.0)
        assert is_anomaly is True
        assert z > 2.0

    def test_stats(self):
        ad = AnomalyDetector(window_size=10)
        for v in [10, 20, 30, 40, 50]:
            ad.add_value(float(v))
        stats = ad.get_stats()
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0

    def test_reset(self):
        ad = AnomalyDetector()
        ad.add_value(100.0)
        ad.add_value(200.0)
        ad.reset()
        stats = ad.get_stats()
        assert stats["count"] == 0

    def test_window_size_limit(self):
        ad = AnomalyDetector(window_size=5)
        for i in range(10):
            ad.add_value(float(i))
        stats = ad.get_stats()
        assert stats["count"] == 5

    def test_empty_stats(self):
        ad = AnomalyDetector()
        stats = ad.get_stats()
        assert stats["count"] == 0
        assert stats["mean"] == 0


# ===========================================================================
# ComplianceChecker Tests (6 tests)
# ===========================================================================

class TestComplianceChecker:
    def test_gdpr_compliant(self):
        cc = ComplianceChecker()
        context = {
            "retention_days": 365, "supports_erasure": True, "has_consent": True,
            "excess_fields": 0, "supports_export": True,
        }
        findings = cc.check(ComplianceFramework.GDPR, context)
        assert len(findings) == 0

    def test_gdpr_non_compliant(self):
        cc = ComplianceChecker()
        context = {
            "retention_days": 500, "supports_erasure": False, "has_consent": False,
            "excess_fields": 3, "supports_export": False,
        }
        findings = cc.check(ComplianceFramework.GDPR, context)
        assert len(findings) == 5

    def test_hipaa_compliant(self):
        cc = ComplianceChecker()
        context = {
            "phi_encrypted": True, "access_controls": True, "audit_trail": True,
            "minimum_necessary": True, "baa_signed": True,
        }
        findings = cc.check(ComplianceFramework.HIPAA, context)
        assert len(findings) == 0

    def test_soc2_compliant(self):
        cc = ComplianceChecker()
        context = {
            "security_monitoring": True, "incident_response": True,
            "change_management": True, "data_classification": True,
            "vendor_risk_mgmt": True,
        }
        findings = cc.check(ComplianceFramework.SOC2, context)
        assert len(findings) == 0

    def test_pci_dss_compliant(self):
        cc = ComplianceChecker()
        context = {
            "data_encrypted": True, "network_segmented": True,
            "vuln_scanning": True, "access_control": True, "security_testing": True,
        }
        findings = cc.check(ComplianceFramework.PCI_DSS, context)
        assert len(findings) == 0

    def test_check_all(self):
        cc = ComplianceChecker()
        context = {k: True for k in [
            "retention_days", "supports_erasure", "has_consent", "excess_fields",
            "supports_export", "phi_encrypted", "access_controls", "audit_trail",
            "minimum_necessary", "baa_signed", "security_monitoring",
            "incident_response", "change_management", "data_classification",
            "vendor_risk_mgmt", "data_encrypted", "network_segmented",
            "vuln_scanning", "access_control", "security_testing",
        ]}
        # Override non-boolean fields
        context["retention_days"] = 365
        context["excess_fields"] = 0
        results = cc.check_all(context)
        total = sum(len(f) for f in results.values())
        assert total == 0


# ===========================================================================
# SecurityBenchmark Integration Tests (5 tests)
# ===========================================================================

class TestSecurityBenchmark:
    def test_run_all_returns_6_results(self):
        sb = SecurityBenchmark()
        results = sb.run_all()
        assert len(results) == 6

    def test_all_plugins_present(self):
        sb = SecurityBenchmark()
        sb.run_all()
        plugin_names = {r.plugin for r in sb.results}
        assert "InputValidator" in plugin_names
        assert "OutputSanitizer" in plugin_names
        assert "RateLimiter" in plugin_names
        assert "AuditLogger" in plugin_names
        assert "AnomalyDetector" in plugin_names
        assert "ComplianceChecker" in plugin_names

    def test_overall_score(self):
        sb = SecurityBenchmark()
        sb.run_all()
        score = sb.get_overall_score()
        assert score["plugins"] == 6
        assert 0 <= score["pass_rate"] <= 1

    def test_benchmark_result_to_dict(self):
        result = BenchmarkResult(
            plugin="TestPlugin",
            passed=5,
            failed=2,
            findings=[],
            duration_ms=10.0,
        )
        d = result.to_dict()
        assert d["plugin"] == "TestPlugin"
        assert d["total"] == 7
        assert d["pass_rate"] == 5 / 7

    def test_finding_to_dict(self):
        finding = SecurityFinding(
            rule_id="TEST-001",
            severity=Severity.HIGH,
            message="Test finding",
            plugin="TestPlugin",
            details={"key": "value"},
        )
        d = finding.to_dict()
        assert d["rule_id"] == "TEST-001"
        assert d["severity"] == "high"
        assert d["details"]["key"] == "value"
