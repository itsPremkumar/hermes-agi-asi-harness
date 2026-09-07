"""Tests for SecurityScanner."""

from __future__ import annotations

import pytest

from harness.review.security import SecurityScanner, Vulnerability, SecurityReport


class TestSecurityScannerInit:
    """Test SecurityScanner initialization."""

    def test_default_init(self):
        """Test default initialization."""
        scanner = SecurityScanner()
        assert len(scanner.SECRET_PATTERNS) > 0
        assert len(scanner.DANGEROUS_FUNCTIONS) > 0
        assert len(scanner.SQL_INJECTION_PATTERNS) > 0


class TestScanFiles:
    """Test scan_files method."""

    def test_clean_file_no_vulnerabilities(self):
        """Test that a clean file has no vulnerabilities."""
        scanner = SecurityScanner()
        files = {
            "safe.py": '"""Safe module."""\ndef add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n',
        }
        report = scanner.scan_files(files)
        assert len(report.vulnerabilities) == 0
        assert report.overall_score == 100.0

    def test_hardcoded_password_detected(self):
        """Test detection of hardcoded passwords."""
        scanner = SecurityScanner()
        files = {
            "secrets.py": '"""Module."""\npassword = "supersecret123"\n',
        }
        report = scanner.scan_files(files)
        assert any("Hardcoded" in v.message for v in report.vulnerabilities)

    def test_hardcoded_api_key_detected(self):
        """Test detection of hardcoded API keys."""
        scanner = SecurityScanner()
        files = {
            "keys.py": '"""Module."""\napi_key = "TEST_KEY_xyz123_not_a_real_key_abc"\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-798" for v in report.vulnerabilities)

    def test_private_key_detected(self):
        """Test detection of embedded private keys."""
        scanner = SecurityScanner()
        files = {
            "key.py": '"""Module."""\nkey = """-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----"""\n',
        }
        report = scanner.scan_files(files)
        assert any("Private key" in v.message for v in report.vulnerabilities)

    def test_eval_detected(self):
        """Test detection of eval usage."""
        scanner = SecurityScanner()
        files = {
            "eval_mod.py": '"""Module."""\ndef run(code: str) -> None:\n    """Run."""\n    eval(code)\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-95" for v in report.vulnerabilities)

    def test_exec_detected(self):
        """Test detection of exec usage."""
        scanner = SecurityScanner()
        files = {
            "exec_mod.py": '"""Module."""\ndef run(code: str) -> None:\n    """Run."""\n    exec(code)\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-95" for v in report.vulnerabilities)

    def test_pickle_detected(self):
        """Test detection of pickle usage."""
        scanner = SecurityScanner()
        files = {
            "pickle_mod.py": '"""Module."""\nimport pickle\ndef load(data: bytes) -> None:\n    """Load."""\n    pickle.loads(data)\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-502" for v in report.vulnerabilities)

    def test_unsafe_yaml_detected(self):
        """Test detection of unsafe YAML loading."""
        scanner = SecurityScanner()
        files = {
            "yaml_mod.py": '"""Module."""\nimport yaml\ndef load(text: str) -> None:\n    """Load."""\n    yaml.load(text)\n',
        }
        report = scanner.scan_files(files)
        assert any("YAML" in v.message for v in report.vulnerabilities)

    def test_subprocess_detected(self):
        """Test detection of subprocess usage."""
        scanner = SecurityScanner()
        files = {
            "subprocess_mod.py": '"""Module."""\nimport subprocess\ndef run(cmd: str) -> None:\n    """Run."""\n    subprocess.call(cmd)\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-78" for v in report.vulnerabilities)

    def test_os_system_detected(self):
        """Test detection of os.system usage."""
        scanner = SecurityScanner()
        files = {
            "os_mod.py": '"""Module."""\nimport os\ndef run(cmd: str) -> None:\n    """Run."""\n    os.system(cmd)\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-78" for v in report.vulnerabilities)

    def test_sql_injection_detected(self):
        """Test detection of SQL injection patterns."""
        scanner = SecurityScanner()
        files = {
            "db.py": '"""Module."""\ndef query(user_input: str) -> None:\n    """Query."""\n    cursor.execute("SELECT * FROM users WHERE id = " + user_input)\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-89" for v in report.vulnerabilities)

    def test_sql_injection_fstring_detected(self):
        """Test detection of SQL injection with f-strings."""
        scanner = SecurityScanner()
        files = {
            "db2.py": '"""Module."""\ndef query(user_input: str) -> None:\n    """Query."""\n    cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-89" for v in report.vulnerabilities)

    def test_path_traversal_detected(self):
        """Test detection of path traversal patterns."""
        scanner = SecurityScanner()
        files = {
            "files.py": '"""Module."""\ndef read(path: str) -> None:\n    """Read."""\n    open(path + ".txt")\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-22" for v in report.vulnerabilities)

    def test_assert_detected(self):
        """Test detection of assert statements."""
        scanner = SecurityScanner()
        files = {
            "assert_mod.py": '"""Module."""\ndef validate(x: int) -> None:\n    """Validate."""\n    assert x > 0\n',
        }
        report = scanner.scan_files(files)
        assert any(v.cwe_id == "CWE-703" for v in report.vulnerabilities)

    def test_import_detected(self):
        """Test detection of __import__ usage."""
        scanner = SecurityScanner()
        files = {
            "imp.py": '"""Module."""\ndef load(name: str) -> None:\n    """Load."""\n    __import__(name)\n',
        }
        report = scanner.scan_files(files)
        assert any("__import__" in v.message for v in report.vulnerabilities)

    def test_compile_detected(self):
        """Test detection of compile() usage."""
        scanner = SecurityScanner()
        files = {
            "comp.py": '"""Module."""\ndef make(code: str) -> None:\n    """Make."""\n    compile(code, "<string>", "exec")\n',
        }
        report = scanner.scan_files(files)
        assert any("compile()" in v.message for v in report.vulnerabilities)

    def test_globals_detected(self):
        """Test detection of globals() usage."""
        scanner = SecurityScanner()
        files = {
            "glob.py": '"""Module."""\ndef inspect_scope() -> None:\n    """Inspect."""\n    globals()\n',
        }
        report = scanner.scan_files(files)
        assert any("globals" in v.message for v in report.vulnerabilities)

    def test_multiple_vulnerabilities(self):
        """Test detection of multiple vulnerabilities in one file."""
        scanner = SecurityScanner()
        files = {
            "bad.py": '"""Module."""\nimport pickle, os\npassword = "secret123"\ndef run(cmd: str) -> None:\n    """Run."""\n    os.system(cmd)\n    pickle.loads(b"test")\n',
        }
        report = scanner.scan_files(files)
        assert len(report.vulnerabilities) >= 3

    def test_overall_score_decreases_with_vulns(self):
        """Test that score decreases with more vulnerabilities."""
        scanner = SecurityScanner()
        clean = scanner.scan_files({"safe.py": '"""Safe."""\npass\n'})
        vuln = scanner.scan_files({"bad.py": '"""Bad."""\nx = eval("1")\n'})
        assert vuln.overall_score < clean.overall_score

    def test_scan_metadata(self):
        """Test scan metadata is populated."""
        scanner = SecurityScanner()
        files = {"a.py": '"""A."""\npass\n', "b.py": '"""B."""\npass\n'}
        report = scanner.scan_files(files)
        assert report.scan_metadata["files_scanned"] == 2

    def test_suggestions_generated(self):
        """Test that suggestions are generated."""
        scanner = SecurityScanner()
        files = {
            "vuln.py": '"""Vuln."""\npassword = "secret123"\nimport pickle\npickle.loads(b"x")\n',
        }
        report = scanner.scan_files(files)
        assert len(report.suggestions) > 0
