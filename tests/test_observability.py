"""Tests for Observability & Evaluation Layer."""
from __future__ import annotations

import pytest
import os
import sys
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from observability import (
    MetricSample,
    MetricsCollector,
    LogEntry,
    StructuredLogger,
    Span,
    Tracer,
    EvaluationResult,
    EvaluationRunner,
    HealthChecker,
    Observability,
    LangSmithClient,
    LangSmithRun,
    LangSmithTracer,
    MetricPoint,
    AlertRule,
    Alert,
    TimeSeriesStore,
    MonitoringPipeline,
    BenchmarkCase,
    BenchmarkResult,
    ModelScore,
    Scorer,
    BenchmarkEngine,
)


# ─── MetricsCollector Tests ────────────────────────────────────────────────────

class TestMetricsCollector:
    def test_record(self):
        m = MetricsCollector()
        m.record("cpu_usage", 75.5)
        assert len(m.get("cpu_usage")) == 1

    def test_get_all(self):
        m = MetricsCollector()
        m.record("cpu", 50)
        m.record("memory", 80)
        assert len(m.get_all()) == 2

    def test_summary(self):
        m = MetricsCollector()
        m.record("cpu", 50)
        m.record("cpu", 100)
        s = m.summary()
        assert s["cpu"]["count"] == 2
        assert s["cpu"]["avg"] == 75

    def test_reset(self):
        m = MetricsCollector()
        m.record("cpu", 50)
        m.reset()
        assert len(m.get_all()) == 0


# ─── StructuredLogger Tests ────────────────────────────────────────────────────

class TestStructuredLogger:
    def test_info(self):
        logger = StructuredLogger()
        entry = logger.info("Test message")
        assert entry.level == "INFO"
        assert entry.message == "Test message"

    def test_warn(self):
        logger = StructuredLogger()
        entry = logger.warn("Warning message")
        assert entry.level == "WARN"

    def test_error(self):
        logger = StructuredLogger()
        entry = logger.error("Error message")
        assert entry.level == "ERROR"

    def test_debug(self):
        logger = StructuredLogger()
        entry = logger.debug("Debug message")
        assert entry.level == "DEBUG"

    def test_get_logs_by_level(self):
        logger = StructuredLogger()
        logger.info("Info 1")
        logger.error("Error 1")
        logger.info("Info 2")
        assert len(logger.get_logs("INFO")) == 2
        assert len(logger.get_logs("ERROR")) == 1


# ─── Tracer Tests ──────────────────────────────────────────────────────────────

class TestTracer:
    def test_start_span(self):
        tracer = Tracer()
        span = tracer.start_span("test_op")
        assert span.name == "test_op"
        assert span.trace_id is not None

    def test_end_span(self):
        tracer = Tracer()
        span = tracer.start_span("test")
        tracer.end_span(span)
        assert span.end_time is not None
        assert span.status == "ok"

    def test_span_context_manager(self):
        tracer = Tracer()
        with tracer.span("test") as span:
            assert span.name == "test"
        assert span.end_time is not None

    def test_span_context_manager_error(self):
        tracer = Tracer()
        with pytest.raises(ValueError):
            with tracer.span("test") as span:
                raise ValueError("test error")

    def test_get_spans(self):
        tracer = Tracer()
        tracer.start_span("span1")
        tracer.start_span("span2")
        assert len(tracer.get_spans()) == 2


# ─── EvaluationRunner Tests ────────────────────────────────────────────────────

class TestEvaluationRunner:
    def test_register_and_run(self):
        runner = EvaluationRunner()
        runner.register("test", lambda: {"score": 0.9, "total": 10, "passed": 9, "failed": 1})
        result = runner.run("test")
        assert result.score == 0.9
        assert result.passed == 9

    def test_run_missing(self):
        runner = EvaluationRunner()
        with pytest.raises(KeyError):
            runner.run("nonexistent")

    def test_run_all(self):
        runner = EvaluationRunner()
        runner.register("a", lambda: {"score": 0.8, "total": 10, "passed": 8, "failed": 2})
        runner.register("b", lambda: {"score": 0.9, "total": 10, "passed": 9, "failed": 1})
        results = runner.run_all()
        assert len(results) == 2


# ─── HealthChecker Tests ───────────────────────────────────────────────────────

class TestHealthChecker:
    def test_register_and_check(self):
        hc = HealthChecker()
        hc.register("db", lambda: True)
        assert hc.check("db") is True

    def test_check_all(self):
        hc = HealthChecker()
        hc.register("db", lambda: True)
        hc.register("cache", lambda: False)
        results = hc.check_all()
        assert results["db"] is True
        assert results["cache"] is False

    def test_is_healthy(self):
        hc = HealthChecker()
        hc.register("db", lambda: True)
        assert hc.is_healthy() is True

    def test_is_healthy_false(self):
        hc = HealthChecker()
        hc.register("db", lambda: False)
        assert hc.is_healthy() is False


# ─── Observability Tests ───────────────────────────────────────────────────────

class TestObservability:
    def test_report(self):
        obs = Observability()
        obs.metrics.record("cpu", 50)
        obs.logger.info("Test")
        report = obs.report()
        assert "metrics" in report
        assert "log_count" in report
        assert "span_count" in report
        assert "health" in report


# ─── LangSmithClient Tests ───────────────────────────────────────────────────

class TestLangSmithClient:
    def test_init_with_api_key(self):
        client = LangSmithClient(api_key="test-key", project_name="test-project")
        assert client.is_active is True
        assert client.project_name == "test-project"

    def test_init_without_api_key(self):
        # Clear env var to test inactive state
        old_key = os.environ.pop("LANGSMITH_API_KEY", None)
        try:
            client = LangSmithClient()
            assert client.is_active is False
        finally:
            if old_key:
                os.environ["LANGSMITH_API_KEY"] = old_key

    def test_create_run(self):
        client = LangSmithClient(api_key="test-key")
        run = client.create_run("test_run", inputs={"prompt": "hello"})
        assert run.name == "test_run"
        assert run.run_type == "chain"
        assert run.status == "running"
        assert run.inputs == {"prompt": "hello"}

    def test_end_run(self):
        client = LangSmithClient(api_key="test-key")
        run = client.create_run("test_run")
        client.end_run(run, outputs={"result": "world"})
        assert run.status == "success"
        assert run.end_time is not None
        assert run.outputs == {"result": "world"}

    def test_end_run_with_error(self):
        client = LangSmithClient(api_key="test-key")
        run = client.create_run("test_run")
        client.end_run(run, error="Something went wrong")
        assert run.status == "error"
        assert run.error == "Something went wrong"

    def test_get_run(self):
        client = LangSmithClient(api_key="test-key")
        run = client.create_run("test_run")
        retrieved = client.get_run(run.run_id)
        assert retrieved is not None
        assert retrieved.run_id == run.run_id

    def test_get_runs_by_type(self):
        client = LangSmithClient(api_key="test-key")
        client.create_run("chain_run", run_type="chain")
        client.create_run("tool_run", run_type="tool")
        client.create_run("chain_run2", run_type="chain")
        chain_runs = client.get_runs(run_type="chain")
        assert len(chain_runs) == 2

    def test_trace_context_manager(self):
        client = LangSmithClient(api_key="test-key")
        with client.trace("test_op", inputs={"x": 1}) as run:
            assert run.status == "running"
        assert run.status == "success"
        assert run.end_time is not None

    def test_trace_context_manager_error(self):
        client = LangSmithClient(api_key="test-key")
        with pytest.raises(ValueError):
            with client.trace("test_op") as run:
                raise ValueError("test error")
        assert run.status == "error"
        assert run.error == "test error"

    def test_evaluate(self):
        client = LangSmithClient(api_key="test-key")
        run = client.create_run("test_run")
        evaluation = client.evaluate(run.run_id, "accuracy", 0.95, "Good result")
        assert evaluation["run_id"] == run.run_id
        assert evaluation["evaluator"] == "accuracy"
        assert evaluation["score"] == 0.95

    def test_get_project_stats(self):
        client = LangSmithClient(api_key="test-key")
        run1 = client.create_run("run1")
        client.end_run(run1, status="success")
        run2 = client.create_run("run2")
        client.end_run(run2, error="fail")
        stats = client.get_project_stats()
        assert stats["total_runs"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5


# ─── LangSmithTracer Tests ───────────────────────────────────────────────────

class TestLangSmithTracer:
    def test_start_span(self):
        tracer = LangSmithTracer()
        span_id = tracer.start_span("test_span")
        assert span_id is not None

    def test_end_span(self):
        tracer = LangSmithTracer()
        span_id = tracer.start_span("test_span")
        tracer.end_span(span_id)
        # Should not raise

    def test_end_span_nonexistent(self):
        tracer = LangSmithTracer()
        tracer.end_span("nonexistent")  # Should not raise

    def test_span_context_manager(self):
        tracer = LangSmithTracer()
        with tracer.span("test_span") as span_id:
            assert span_id is not None

    def test_span_context_manager_error(self):
        tracer = LangSmithTracer()
        with pytest.raises(ValueError):
            with tracer.span("test_span") as span_id:
                raise ValueError("test error")


# ─── TimeSeriesStore Tests ──────────────────────────────────────────────────

class TestTimeSeriesStore:
    def test_write_and_query(self):
        store = TimeSeriesStore()
        point = MetricPoint(name="cpu", value=50.0, timestamp="2024-01-01T00:00:00Z")
        store.write(point)
        results = store.query("cpu")
        assert len(results) == 1
        assert results[0].value == 50.0

    def test_query_with_time_range(self):
        store = TimeSeriesStore()
        store.write(MetricPoint(name="cpu", value=50.0, timestamp="2024-01-01T00:00:00Z"))
        store.write(MetricPoint(name="cpu", value=60.0, timestamp="2024-01-02T00:00:00Z"))
        store.write(MetricPoint(name="cpu", value=70.0, timestamp="2024-01-03T00:00:00Z"))
        results = store.query("cpu", start_time="2024-01-02T00:00:00Z")
        assert len(results) == 2

    def test_query_limit(self):
        store = TimeSeriesStore()
        for i in range(10):
            store.write(MetricPoint(name="cpu", value=float(i), timestamp=f"2024-01-0{i+1}T00:00:00Z"))
        results = store.query("cpu", limit=5)
        assert len(results) == 5

    def test_aggregate(self):
        store = TimeSeriesStore()
        for i in range(5):
            store.write(MetricPoint(name="cpu", value=float(i * 10), timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()))
        result = store.aggregate("cpu", window_seconds=60, agg_func="avg")
        assert len(result) == 1
        assert result[0]["aggregation"] == "avg"

    def test_aggregate_empty(self):
        store = TimeSeriesStore()
        result = store.aggregate("nonexistent", window_seconds=60)
        assert result == []

    def test_close(self):
        store = TimeSeriesStore()
        store.close()  # Should not raise


# ─── MonitoringPipeline Tests ────────────────────────────────────────────────

class TestMonitoringPipeline:
    def test_record(self):
        pipeline = MonitoringPipeline()
        pipeline.record("cpu", 75.5)
        metrics = pipeline.get_metrics("cpu")
        assert len(metrics) == 1
        assert metrics[0].value == 75.5

    def test_add_alert_rule(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule(name="high_cpu", metric="cpu", threshold=90.0)
        pipeline.add_alert_rule(rule)
        assert "high_cpu" in pipeline._alert_rules

    def test_remove_alert_rule(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule(name="high_cpu", metric="cpu", threshold=90.0)
        pipeline.add_alert_rule(rule)
        pipeline.remove_alert_rule("high_cpu")
        assert "high_cpu" not in pipeline._alert_rules

    def test_alert_triggered(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule(name="high_cpu", metric="cpu", threshold=90.0, duration=0)
        pipeline.add_alert_rule(rule)
        pipeline.record("cpu", 95.0)
        alerts = pipeline.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_cpu"
        assert alerts[0].value == 95.0

    def test_alert_not_triggered(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule(name="high_cpu", metric="cpu", threshold=90.0, duration=0)
        pipeline.add_alert_rule(rule)
        pipeline.record("cpu", 50.0)
        alerts = pipeline.get_active_alerts()
        assert len(alerts) == 0

    def test_clear_alerts(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule(name="high_cpu", metric="cpu", threshold=90.0, duration=0)
        pipeline.add_alert_rule(rule)
        pipeline.record("cpu", 95.0)
        pipeline.clear_alerts()
        assert len(pipeline.get_active_alerts()) == 0

    def test_get_dashboard_data(self):
        pipeline = MonitoringPipeline()
        pipeline.record("cpu", 50.0)
        pipeline.record("memory", 70.0)
        data = pipeline.get_dashboard_data()
        assert "metrics" in data
        assert "active_alerts" in data
        assert "alert_count" in data

    def test_add_collector(self):
        pipeline = MonitoringPipeline()
        collector = lambda: [MetricPoint(name="test", value=1.0, timestamp="2024-01-01T00:00:00Z")]
        pipeline.add_collector(collector)
        assert len(pipeline._collectors) == 1

    def test_close(self):
        pipeline = MonitoringPipeline()
        pipeline.close()  # Should not raise


# ─── AlertRule Tests ─────────────────────────────────────────────────────────

class TestAlertRule:
    def test_check_gt(self):
        rule = AlertRule(name="test", metric="cpu", threshold=90.0, comparison="gt")
        assert rule.check(95.0) is True
        assert rule.check(85.0) is False

    def test_check_lt(self):
        rule = AlertRule(name="test", metric="cpu", threshold=10.0, comparison="lt")
        assert rule.check(5.0) is True
        assert rule.check(15.0) is False

    def test_check_gte(self):
        rule = AlertRule(name="test", metric="cpu", threshold=90.0, comparison="gte")
        assert rule.check(90.0) is True
        assert rule.check(89.0) is False

    def test_check_lte(self):
        rule = AlertRule(name="test", metric="cpu", threshold=10.0, comparison="lte")
        assert rule.check(10.0) is True
        assert rule.check(11.0) is False

    def test_check_eq(self):
        rule = AlertRule(name="test", metric="cpu", threshold=50.0, comparison="eq")
        assert rule.check(50.0) is True
        assert rule.check(51.0) is False


# ─── Scorer Tests ─────────────────────────────────────────────────────────────

class TestScorer:
    def test_exact_match(self):
        assert Scorer.exact_match("hello", "hello") == 1.0
        assert Scorer.exact_match("hello", "world") == 0.0

    def test_contains(self):
        assert Scorer.contains("hello world", "world") == 1.0
        assert Scorer.contains("hello world", "xyz") == 0.0

    def test_similarity(self):
        assert Scorer.similarity("hello world", "hello") == 1.0
        assert Scorer.similarity("hello world", "xyz") == 0.0

    def test_levenshtein_ratio(self):
        assert Scorer.levenshtein_ratio("hello", "hello") == 1.0
        assert Scorer.levenshtein_ratio("kitten", "sitting") > 0.5


# ─── BenchmarkEngine Tests ──────────────────────────────────────────────────

class TestBenchmarkEngine:
    def test_add_case(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="What is 2+2?", expected="4")
        engine.add_case(case)
        assert "1" in engine._cases

    def test_add_cases(self):
        engine = BenchmarkEngine()
        cases = [
            BenchmarkCase(case_id="1", prompt="Q1", expected="A1"),
            BenchmarkCase(case_id="2", prompt="Q2", expected="A2"),
        ]
        engine.add_cases(cases)
        assert len(engine._cases) == 2

    def test_register_model(self):
        engine = BenchmarkEngine()
        model = MagicMock()
        model.generate.return_value = "4"
        engine.register_model("test_model", model)
        assert "test_model" in engine._models

    def test_run_case(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="What is 2+2?", expected="4")
        engine.add_case(case)
        model = MagicMock()
        model.generate.return_value = "4"
        engine.register_model("test_model", model)
        result = engine.run_case("1", "test_model")
        assert result.score == 1.0
        assert result.output == "4"

    def test_run_benchmark(self):
        engine = BenchmarkEngine()
        cases = [
            BenchmarkCase(case_id="1", prompt="Q1", expected="A1"),
            BenchmarkCase(case_id="2", prompt="Q2", expected="A2"),
        ]
        engine.add_cases(cases)
        model = MagicMock()
        model.generate.return_value = "A1"
        engine.register_model("test_model", model)
        results = engine.run_benchmark("test_model")
        assert len(results) == 2

    def test_run_all_models(self):
        engine = BenchmarkEngine()
        cases = [BenchmarkCase(case_id="1", prompt="Q1", expected="A1")]
        engine.add_cases(cases)
        model1 = MagicMock()
        model1.generate.return_value = "A1"
        model2 = MagicMock()
        model2.generate.return_value = "wrong"
        engine.register_model("model1", model1)
        engine.register_model("model2", model2)
        results = engine.run_all_models()
        assert len(results) == 2

    def test_get_model_score(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="Q", expected="A")
        engine.add_case(case)
        model = MagicMock()
        model.generate.return_value = "A"
        engine.register_model("test_model", model)
        engine.run_benchmark("test_model")
        score = engine.get_model_score("test_model")
        assert score is not None
        assert score.model_name == "test_model"
        assert score.avg_score == 1.0

    def test_get_model_score_no_results(self):
        engine = BenchmarkEngine()
        engine.register_model("test_model", MagicMock())
        score = engine.get_model_score("test_model")
        assert score is None

    def test_compare_models(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="Q", expected="A")
        engine.add_case(case)
        model1 = MagicMock()
        model1.generate.return_value = "A"
        model2 = MagicMock()
        model2.generate.return_value = "wrong"
        engine.register_model("model1", model1)
        engine.register_model("model2", model2)
        engine.run_all_models()
        comparison = engine.compare_models()
        assert len(comparison) == 2
        assert comparison[0].model_name == "model1"

    def test_get_results(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="Q", expected="A")
        engine.add_case(case)
        model = MagicMock()
        model.generate.return_value = "A"
        engine.register_model("test_model", model)
        engine.run_benchmark("test_model")
        results = engine.get_results("test_model")
        assert len(results) == 1

    def test_export_results(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="Q", expected="A")
        engine.add_case(case)
        model = MagicMock()
        model.generate.return_value = "A"
        engine.register_model("test_model", model)
        engine.run_benchmark("test_model")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            engine.export_results(path)
            data = json.loads(Path(path).read_text())
            assert "models" in data
            assert "results" in data
        finally:
            os.unlink(path)

    def test_clear_results(self):
        engine = BenchmarkEngine()
        case = BenchmarkCase(case_id="1", prompt="Q", expected="A")
        engine.add_case(case)
        model = MagicMock()
        model.generate.return_value = "A"
        engine.register_model("test_model", model)
        engine.run_benchmark("test_model")
        engine.clear_results()
        assert len(engine.get_results()) == 0


# ─── BenchmarkCase Tests ─────────────────────────────────────────────────────

class TestBenchmarkCase:
    def test_creation(self):
        case = BenchmarkCase(case_id="1", prompt="Q", expected="A", category="math", difficulty="easy")
        assert case.case_id == "1"
        assert case.prompt == "Q"
        assert case.expected == "A"
        assert case.category == "math"
        assert case.difficulty == "easy"


# ─── BenchmarkResult Tests ──────────────────────────────────────────────────

class TestBenchmarkResult:
    def test_to_dict(self):
        result = BenchmarkResult(
            case_id="1",
            model_name="test",
            prompt="Q",
            output="A",
            expected="A",
            score=1.0,
            latency=0.5,
            category="general",
            difficulty="medium",
        )
        d = result.to_dict()
        assert d["case_id"] == "1"
        assert d["score"] == 1.0
        assert d["latency"] == 0.5


# ─── ModelScore Tests ────────────────────────────────────────────────────────

class TestModelScore:
    def test_to_dict(self):
        score = ModelScore(
            model_name="test",
            total_cases=10,
            avg_score=0.8,
            median_score=0.8,
            std_score=0.1,
            avg_latency=0.5,
            min_score=0.0,
            max_score=1.0,
        )
        d = score.to_dict()
        assert d["model_name"] == "test"
        assert d["total_cases"] == 10
        assert d["avg_score"] == 0.8


# ─── MetricPoint Tests ───────────────────────────────────────────────────────

class TestMetricPoint:
    def test_to_dict(self):
        point = MetricPoint(name="cpu", value=50.0, timestamp="2024-01-01T00:00:00Z", labels={"host": "server1"})
        d = point.to_dict()
        assert d["name"] == "cpu"
        assert d["value"] == 50.0
        assert d["labels"]["host"] == "server1"


# ─── Alert Tests ─────────────────────────────────────────────────────────────

class TestAlert:
    def test_to_dict(self):
        alert = Alert(
            rule_name="high_cpu",
            metric="cpu",
            value=95.0,
            threshold=90.0,
            severity="warning",
            timestamp="2024-01-01T00:00:00Z",
        )
        d = alert.to_dict()
        assert d["rule_name"] == "high_cpu"
        assert d["value"] == 95.0
        assert d["severity"] == "warning"


# ─── LangSmithRun Tests ─────────────────────────────────────────────────────

class TestLangSmithRun:
    def test_to_dict(self):
        run = LangSmithRun(
            run_id="123",
            name="test",
            run_type="chain",
            inputs={"x": 1},
            outputs={"y": 2},
        )
        d = run.to_dict()
        assert d["id"] == "123"
        assert d["name"] == "test"
        assert d["inputs"] == {"x": 1}
