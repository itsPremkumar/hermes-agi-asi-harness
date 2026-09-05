"""Tests for Delegate Task Concurrency Diagnostic Tool."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from diagnostics.delegate_task_diagnostic import (
    CapType,
    DelegateTaskDiagnostic,
    DiagnosticReport,
    DiagnosticResult,
)


class TestDiagnosticResult:
    def test_create(self):
        result = DiagnosticResult(
            cap_type=CapType.PER_CALL_REJECT,
            detected=True,
            message="Test message",
            suggestion="Test suggestion",
        )
        assert result.cap_type == CapType.PER_CALL_REJECT
        assert result.detected is True
        assert result.message == "Test message"
        assert result.suggestion == "Test suggestion"
        assert result.details == {}


class TestDiagnosticReport:
    def test_create(self):
        report = DiagnosticReport(
            profile="default",
            config_path="/path/to/config.yaml",
            max_concurrent_children=15,
            env_var_value="15",
            running_processes=[],
            log_path="/path/to/agent.log",
            cap_paths_detected=[],
            summary="Test summary",
            recommendations=["Rec 1"],
        )
        assert report.profile == "default"
        assert report.max_concurrent_children == 15


class TestDelegateTaskDiagnostic:
    def setup_method(self):
        """Create temp hermes home for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.hermes_home = Path(self.temp_dir) / ".hermes"
        self.hermes_home.mkdir(parents=True, exist_ok=True)
        (self.hermes_home / "profiles" / "default").mkdir(parents=True, exist_ok=True)
        (self.hermes_home / "logs").mkdir(parents=True, exist_ok=True)

    def test_init(self):
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        assert diagnostic.profile == "default"
        assert diagnostic.hermes_home == self.hermes_home

    def test_init_from_env(self):
        old_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = str(self.hermes_home)
        diagnostic = DelegateTaskDiagnostic()
        assert diagnostic.hermes_home == self.hermes_home
        if old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old_home

    def test_get_max_concurrent_children_from_config(self):
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 15\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        assert diagnostic._get_max_concurrent_children() == 15

    def test_get_max_concurrent_children_missing_config(self):
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        assert diagnostic._get_max_concurrent_children() is None

    def test_get_max_concurrent_children_default(self):
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("other_setting: value\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        # Should return 3 (default)
        assert diagnostic._get_max_concurrent_children() == 3

    def test_check_per_call_reject_detected(self):
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("Too many tasks: 20 provided, but max_concurrent_children is 15.\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        result = diagnostic._check_per_call_reject(15)
        assert result.detected is True
        assert result.cap_type == CapType.PER_CALL_REJECT
        assert "20" in result.message
        assert "15" in result.message

    def test_check_per_call_reject_not_detected(self):
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("No errors here.\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        result = diagnostic._check_per_call_reject(15)
        assert result.detected is False

    def test_check_per_turn_truncator_detected(self):
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("Truncated 5 excess delegate_task call(s) to enforce max_concurrent_children=10 limit\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        result = diagnostic._check_per_turn_truncator()
        assert result.detected is True
        assert result.cap_type == CapType.PER_TURN_TRUNCATOR
        assert "5" in result.message

    def test_check_per_turn_truncator_not_detected(self):
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("No truncation.\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        result = diagnostic._check_per_turn_truncator()
        assert result.detected is False

    def test_check_cost_warning_detected(self):
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("delegation.max_concurrent_children=15: each child consumes API tokens independently.\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        result = diagnostic._check_cost_warning(15)
        assert result.detected is True
        assert result.cap_type == CapType.COST_WARNING

    def test_check_cost_warning_not_detected(self):
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("No warnings.\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        result = diagnostic._check_cost_warning(5)
        assert result.detected is False

    def test_check_model_self_limit_other_caps_active(self):
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        other_caps = [
            DiagnosticResult(cap_type=CapType.PER_CALL_REJECT, detected=True, message=""),
        ]
        result = diagnostic._check_model_self_limit(15, other_caps)
        assert result.detected is False

    def test_check_model_self_limit_high_value(self):
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        other_caps = [
            DiagnosticResult(cap_type=CapType.PER_CALL_REJECT, detected=False, message=""),
            DiagnosticResult(cap_type=CapType.PER_TURN_TRUNCATOR, detected=False, message=""),
            DiagnosticResult(cap_type=CapType.COST_WARNING, detected=False, message=""),
        ]
        result = diagnostic._check_model_self_limit(15, other_caps)
        assert result.detected is True
        assert result.cap_type == CapType.MODEL_SELF_LIMIT

    def test_check_model_self_limit_low_value(self):
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        other_caps = [
            DiagnosticResult(cap_type=CapType.PER_CALL_REJECT, detected=False, message=""),
            DiagnosticResult(cap_type=CapType.PER_TURN_TRUNCATOR, detected=False, message=""),
            DiagnosticResult(cap_type=CapType.COST_WARNING, detected=False, message=""),
        ]
        result = diagnostic._check_model_self_limit(5, other_caps)
        assert result.detected is False

    def test_run_full_report(self):
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 15\n")
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("Too many tasks: 20 provided, but max_concurrent_children is 15.\n")
        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        report = diagnostic.run()
        assert report.profile == "default"
        assert report.max_concurrent_children == 15
        assert len(report.cap_paths_detected) == 4
        assert any(r.cap_type == CapType.PER_CALL_REJECT and r.detected for r in report.cap_paths_detected)
        assert len(report.recommendations) > 0


class TestIntegrationScenarios:
    """Integration tests simulating real-world scenarios."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.hermes_home = Path(self.temp_dir) / ".hermes"
        self.hermes_home.mkdir(parents=True, exist_ok=True)
        (self.hermes_home / "profiles" / "default").mkdir(parents=True, exist_ok=True)
        (self.hermes_home / "logs").mkdir(parents=True, exist_ok=True)

    def test_scenario_per_call_reject(self):
        """Scenario: User set max=5, tried to delegate 8 tasks."""
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 5\n")
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("Too many tasks: 8 provided, but max_concurrent_children is 5.\n")

        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        report = diagnostic.run()

        per_call = next(r for r in report.cap_paths_detected if r.cap_type == CapType.PER_CALL_REJECT)
        assert per_call.detected is True
        assert "8" in per_call.message
        assert "5" in per_call.message

    def test_scenario_per_turn_truncator(self):
        """Scenario: User made 3 separate delegate_task calls in one turn, max=2."""
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 2\n")
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("Truncated 1 excess delegate_task call(s) to enforce max_concurrent_children=2 limit\n")

        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        report = diagnostic.run()

        trunc = next(r for r in report.cap_paths_detected if r.cap_type == CapType.PER_TURN_TRUNCATOR)
        assert trunc.detected is True

    def test_scenario_cost_warning_only(self):
        """Scenario: max=15 but user sees cost warning, thinks it's a cap."""
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 15\n")
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("delegation.max_concurrent_children=15: each child consumes API tokens independently.\n")

        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        report = diagnostic.run()

        cost = next(r for r in report.cap_paths_detected if r.cap_type == CapType.COST_WARNING)
        assert cost.detected is True
        assert "not a cap" in cost.message.lower() or "WARNING" in cost.message

    def test_scenario_model_self_limit(self):
        """Scenario: max=20, no Hermes caps, model still limited to 9."""
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 20\n")
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("")  # Clean log

        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        report = diagnostic.run()

        model = next(r for r in report.cap_paths_detected if r.cap_type == CapType.MODEL_SELF_LIMIT)
        assert model.detected is True
        assert "model" in model.message.lower() or "self-limit" in model.message.lower()

    def test_scenario_no_caps(self):
        """Scenario: Everything configured correctly, no caps."""
        config_path = self.hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 5\n")
        log_path = self.hermes_home / "logs" / "agent.log"
        log_path.write_text("")

        diagnostic = DelegateTaskDiagnostic(profile="default", hermes_home=str(self.hermes_home))
        report = diagnostic.run()

        detected = [r for r in report.cap_paths_detected if r.detected]
        assert len(detected) == 0


class TestMainCLI:
    """Test CLI entry point."""

    def test_cli_help(self, capsys):
        import sys

        from diagnostics.delegate_task_diagnostic import main
        old_argv = sys.argv
        sys.argv = ["delegate_task_diagnostic", "--help"]
        try:
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
        finally:
            sys.argv = old_argv

    def test_cli_json_output(self, capsys, tmp_path):
        hermes_home = tmp_path / ".hermes"
        hermes_home.mkdir()
        (hermes_home / "profiles" / "default").mkdir(parents=True)
        (hermes_home / "logs").mkdir(parents=True)
        config_path = hermes_home / "profiles" / "default" / "config.yaml"
        config_path.write_text("delegation:\n  max_concurrent_children: 10\n")

        import sys

        from diagnostics.delegate_task_diagnostic import main
        old_argv = sys.argv
        sys.argv = ["delegate_task_diagnostic", "--hermes-home", str(hermes_home), "--json"]
        try:
            main()
        finally:
            sys.argv = old_argv
        # No exception = success
