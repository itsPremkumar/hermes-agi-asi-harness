"""Tests for Observability & Evaluation Layer."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from observability import (
    LangSmithClient,
    ObservabilityPipeline,
    MetricType,
    TraceStatus,
)
from observability.langsmith_integration import (
    LangSmithTraceConfig,
    LangSmithTracer,
    SecretScrubber,
    TraceSpan,
)
from observability.monitoring_pipeline import (
    AlertRule,
    DashboardWidget,
    MetricSample,
    MetricsAggregator,
    MonitoringPipeline,
)
from observability.benchmark_engine import (
    BenchmarkEngine,
    BenchmarkScore,
    BenchmarkTask,
    ModelResult,
)


# =====================================================================
# Original ObservabilityPipeline Tests
# =====================================================================


class TestMetricType:
    def test_values(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"


class TestTraceStatus:
    def test_values(self):
        assert TraceStatus.STARTED.value == "started"
        assert TraceStatus.COMPLETED.value == "completed"
        assert TraceStatus.FAILED.value == "failed"


class TestLangSmithClient:
    def test_create(self):
        client = LangSmithClient(api_key="test-key", project="test-project")
        assert client.project == "test-project"
        assert client.api_key == "test-key"

    def test_start_trace(self):
        client = LangSmithClient()
        trace = client.start_trace("test-operation")
        assert trace.name == "test-operation"
        assert trace.status == TraceStatus.STARTED
        assert len(client._traces) == 1

    def test_complete_trace(self):
        client = LangSmithClient()
        trace = client.start_trace("test")
        trace.complete({"result": "ok"})
        assert trace.status == TraceStatus.COMPLETED
        assert trace.end_time is not None
        assert trace.duration_ms >= 0

    def test_fail_trace(self):
        client = LangSmithClient()
        trace = client.start_trace("test")
        trace.fail("error")
        assert trace.status == TraceStatus.FAILED
        assert "error" in trace.metadata

    def test_record_metric(self):
        client = LangSmithClient()
        client.record_metric("test_metric", 42.0, MetricType.GAUGE)
        assert len(client._metrics) == 1
        assert client._metrics[0].value == 42.0

    def test_get_traces_by_status(self):
        client = LangSmithClient()
        t1 = client.start_trace("a")
        t2 = client.start_trace("b")
        t1.complete()
        t2.fail("err")
        assert len(client.get_traces(TraceStatus.COMPLETED)) == 1
        assert len(client.get_traces(TraceStatus.FAILED)) == 1

    def test_get_metrics_by_name(self):
        client = LangSmithClient()
        client.record_metric("latency", 100.0)
        client.record_metric("latency", 200.0)
        client.record_metric("tokens", 50.0)
        assert len(client.get_metrics("latency")) == 2
        assert len(client.get_metrics("tokens")) == 1

    def test_get_summary(self):
        client = LangSmithClient()
        t1 = client.start_trace("a")
        t1.complete()
        t2 = client.start_trace("b")
        t2.fail("err")
        summary = client.get_summary()
        assert summary["total_traces"] == 2
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["success_rate"] == 0.5


class TestObservabilityPipeline:
    def test_create(self):
        pipeline = ObservabilityPipeline(langsmith_api_key="test")
        assert pipeline.langsmith is not None

    def test_record_latency(self):
        pipeline = ObservabilityPipeline()
        pipeline.record_latency("inference", 150.5)
        assert len(pipeline.langsmith._metrics) == 1

    def test_record_token_usage(self):
        pipeline = ObservabilityPipeline()
        pipeline.record_token_usage("gpt-4", 1000, 0.03)
        assert len(pipeline.langsmith._metrics) == 2

    def test_record_task_completion(self):
        pipeline = ObservabilityPipeline()
        pipeline.record_task_completion("t-001", "devops", 5000, True)
        assert len(pipeline.langsmith._metrics) == 1

    def test_evaluate_benchmark_pass(self):
        pipeline = ObservabilityPipeline()
        result = pipeline.evaluate_benchmark("mmlu", 0.85, 0.80)
        assert result.passed is True
        assert abs(result.gap - (-0.05)) < 1e-9

    def test_evaluate_benchmark_fail(self):
        pipeline = ObservabilityPipeline()
        result = pipeline.evaluate_benchmark("mmlu", 0.70, 0.80)
        assert result.passed is False
        assert abs(result.gap - 0.10) < 1e-9

    def test_get_evaluation_summary(self):
        pipeline = ObservabilityPipeline()
        pipeline.evaluate_benchmark("a", 0.9, 0.8)
        pipeline.evaluate_benchmark("b", 0.7, 0.8)
        pipeline.evaluate_benchmark("c", 0.85, 0.8)
        summary = pipeline.get_evaluation_summary()
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1

    def test_generate_report(self):
        pipeline = ObservabilityPipeline()
        pipeline.record_latency("op", 100)
        pipeline.evaluate_benchmark("test", 0.9, 0.8)
        report = pipeline.generate_report()
        assert "langsmith" in report
        assert "evaluations" in report
        assert report["evaluations"]["total"] == 1

    def test_save_report(self, tmp_path):
        pipeline = ObservabilityPipeline()
        pipeline.evaluate_benchmark("test", 0.9, 0.8)
        report_path = tmp_path / "report.json"
        pipeline.save_report(str(report_path))
        assert report_path.exists()
        import json
        data = json.loads(report_path.read_text())
        assert data["evaluations"]["total"] == 1


class TestEvaluationResult:
    def test_create(self):
        from observability import EvaluationResult
        result = EvaluationResult(
            run_id="r-001",
            benchmark="mmlu",
            score=0.85,
            target=0.80,
            passed=True,
        )
        assert abs(result.gap - (-0.05)) < 1e-9

    def test_gap_zero(self):
        from observability import EvaluationResult
        result = EvaluationResult(
            run_id="r-002",
            benchmark="test",
            score=0.80,
            target=0.80,
            passed=True,
        )
        assert result.gap == 0.0


# =====================================================================
# LangSmith Integration Tests
# =====================================================================


class TestLangSmithTraceConfig:
    def test_defaults(self):
        config = LangSmithTraceConfig()
        assert config.enabled is False
        assert config.project_name == "hermes-asi-master"
        assert config.scrub_secrets is True
        assert config.local_fallback is True
        assert config.sample_rate == 1.0

    def test_from_env(self):
        config = LangSmithTraceConfig.from_env()
        assert isinstance(config, LangSmithTraceConfig)
        assert config.scrub_secrets is True


class TestSecretScrubber:
    def test_scrub_openai_key(self):
        result = SecretScrubber.scrub("api_key=sk-abcdefghijklmnopqrstuvwxyz123456")
        assert "[REDACTED_OPENAI_KEY]" in result

    def test_scrub_github_token(self):
        result = SecretScrubber.scrub("token=ghp_abcdefghijklmnopqrstuvwxyz123456")
        assert "[REDACTED_GITHUB_TOKEN]" in result

    def test_scrub_bearer_token(self):
        result = SecretScrubber.scrub("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "[REDACTED_BEARER_TOKEN]" in result

    def test_scrub_dict(self):
        data = {"api_key": "sk-abcdefghijklmnopqrstuvwxyz123456", "name": "test"}
        result = SecretScrubber.scrub(data)
        assert "[REDACTED_OPENAI_KEY]" in result["api_key"]
        assert result["name"] == "test"

    def test_scrub_list(self):
        data = ["ghp_abcdefghijklmnopqrstuvwxyz123456", "normal"]
        result = SecretScrubber.scrub(data)
        assert "[REDACTED_GITHUB_TOKEN]" in result[0]
        assert result[1] == "normal"

    def test_scrub_password(self):
        data = "password='supersecret'"
        result = SecretScrubber.scrub(data)
        assert "[REDACTED_PASSWORD]" in result


class TestTraceSpan:
    def test_create(self):
        span = TraceSpan(name="test-span")
        assert span.name == "test-span"
        assert span.status == "running"
        assert span.end_time is None

    def test_end(self):
        span = TraceSpan(name="test")
        span.end(outputs={"result": "ok"})
        assert span.status == "completed"
        assert span.end_time is not None
        assert span.duration_ms >= 0

    def test_end_with_error(self):
        span = TraceSpan(name="test")
        span.end(error="something failed")
        assert span.status == "failed"
        assert span.error == "something failed"

    def test_to_dict(self):
        span = TraceSpan(name="test", inputs={"x": 1})
        d = span.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "running"
        assert d["inputs"] == {"x": 1}


class TestLangSmithTracer:
    def test_create(self):
        tracer = LangSmithTracer()
        assert tracer.config.project_name == "hermes-asi-master"

    def test_start_span(self):
        tracer = LangSmithTracer()
        span = tracer.start_span("test-op", inputs={"x": 1})
        assert span.name == "test-op"
        assert span.status == "running"

    def test_end_span(self):
        tracer = LangSmithTracer()
        span = tracer.start_span("test-op")
        result = tracer.end_span(span.span_id, outputs={"y": 2})
        assert result is not None
        assert result["status"] == "completed"

    def test_end_span_with_error(self):
        tracer = LangSmithTracer()
        span = tracer.start_span("test-op")
        result = tracer.end_span(span.span_id, error="fail")
        assert result["status"] == "failed"

    def test_get_completed_traces(self):
        tracer = LangSmithTracer()
        span = tracer.start_span("test-op")
        tracer.end_span(span.span_id)
        traces = tracer.get_completed_traces()
        assert len(traces) >= 1

    def test_record_evaluation(self):
        tracer = LangSmithTracer()
        ok = tracer.record_evaluation("run-1", "correctness", 0.95)
        assert ok is True

    def test_clear(self):
        tracer = LangSmithTracer()
        span = tracer.start_span("test")
        tracer.end_span(span.span_id)
        tracer.clear()
        assert len(tracer.get_completed_traces()) == 0


# =====================================================================
# Monitoring Pipeline Tests
# =====================================================================


class TestMetricSample:
    def test_create(self):
        sample = MetricSample(name="cpu", value=75.0, labels={"host": "main"})
        assert sample.name == "cpu"
        assert sample.value == 75.0
        assert sample.labels["host"] == "main"

    def test_to_dict(self):
        sample = MetricSample(name="mem", value=50.0)
        d = sample.to_dict()
        assert d["name"] == "mem"
        assert d["value"] == 50.0


class TestMetricsAggregator:
    def test_add_sample(self):
        agg = MetricsAggregator(window_size_s=60.0)
        agg.add_sample(MetricSample(name="cpu", value=50.0))
        stats = agg.get_stats("cpu")
        assert stats["count"] == 1
        assert stats["avg"] == 50.0

    def test_get_stats_empty(self):
        agg = MetricsAggregator()
        stats = agg.get_stats("nonexistent")
        assert stats["count"] == 0

    def test_get_stats_multiple(self):
        agg = MetricsAggregator()
        agg.add_sample(MetricSample(name="cpu", value=10.0))
        agg.add_sample(MetricSample(name="cpu", value=20.0))
        agg.add_sample(MetricSample(name="cpu", value=30.0))
        stats = agg.get_stats("cpu")
        assert stats["count"] == 3
        assert stats["avg"] == 20.0
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0

    def test_get_stats_with_labels(self):
        agg = MetricsAggregator()
        agg.add_sample(MetricSample(name="cpu", value=10.0, labels={"host": "a"}))
        agg.add_sample(MetricSample(name="cpu", value=20.0, labels={"host": "b"}))
        agg.add_sample(MetricSample(name="cpu", value=30.0, labels={"host": "a"}))
        stats = agg.get_stats("cpu", labels={"host": "a"})
        assert stats["count"] == 2
        assert stats["avg"] == 20.0


class TestAlertRule:
    def test_gt_trigger(self):
        rule = AlertRule("cpu-high", "cpu", 80.0, comparison="gt")
        assert rule.evaluate(90.0) is True
        assert rule.evaluate(70.0) is False

    def test_lt_trigger(self):
        rule = AlertRule("cpu-low", "cpu", 20.0, comparison="lt")
        assert rule.evaluate(10.0) is True
        assert rule.evaluate(30.0) is False

    def test_gte_trigger(self):
        rule = AlertRule("cpu-gte", "cpu", 80.0, comparison="gte")
        assert rule.evaluate(80.0) is True
        assert rule.evaluate(79.0) is False

    def test_no_repeat_trigger(self):
        rule = AlertRule("cpu-high", "cpu", 80.0, comparison="gt")
        assert rule.evaluate(90.0) is True
        assert rule.evaluate(95.0) is False  # Already triggered
        assert rule.evaluate(70.0) is False  # Resets
        assert rule.evaluate(95.0) is True  # Re-triggers


class TestMonitoringPipeline:
    def test_create(self):
        pipeline = MonitoringPipeline()
        assert pipeline.aggregator is not None

    def test_record_metric(self):
        pipeline = MonitoringPipeline()
        sample = pipeline.record_metric("cpu", 75.0)
        assert sample.name == "cpu"
        assert sample.value == 75.0

    def test_record_counter(self):
        pipeline = MonitoringPipeline()
        pipeline.record_counter("requests", 1.0)
        stats = pipeline.aggregator.get_stats("requests")
        assert stats["count"] == 1

    def test_record_gauge(self):
        pipeline = MonitoringPipeline()
        pipeline.record_gauge("memory", 4096.0)
        stats = pipeline.aggregator.get_stats("memory")
        assert stats["avg"] == 4096.0

    def test_record_histogram(self):
        pipeline = MonitoringPipeline()
        pipeline.record_histogram("latency", 150.0)
        stats = pipeline.aggregator.get_stats("latency")
        assert stats["avg"] == 150.0

    def test_add_alert_rule(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule("cpu-high", "cpu", 80.0)
        pipeline.add_alert_rule(rule)
        assert "cpu-high" in pipeline._alert_rules

    def test_remove_alert_rule(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule("cpu-high", "cpu", 80.0)
        pipeline.add_alert_rule(rule)
        assert pipeline.remove_alert_rule("cpu-high") is True
        assert pipeline.remove_alert_rule("nonexistent") is False

    def test_alert_triggered(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule("cpu-high", "cpu", 80.0, comparison="gt", severity="warning")
        pipeline.add_alert_rule(rule)
        pipeline.record_gauge("cpu", 95.0)
        alerts = pipeline.get_active_alerts()
        assert len(alerts) >= 1
        assert alerts[0]["rule_id"] == "cpu-high"

    def test_clear_alerts(self):
        pipeline = MonitoringPipeline()
        rule = AlertRule("cpu-high", "cpu", 80.0)
        pipeline.add_alert_rule(rule)
        pipeline.record_gauge("cpu", 95.0)
        pipeline.clear_alerts()
        assert len(pipeline.get_active_alerts()) == 0

    def test_add_widget(self):
        pipeline = MonitoringPipeline()
        widget = DashboardWidget("cpu-widget", "CPU Usage", "cpu")
        pipeline.add_widget(widget)
        assert "cpu-widget" in pipeline._widgets

    def test_get_dashboard_data(self):
        pipeline = MonitoringPipeline()
        widget = DashboardWidget("cpu-widget", "CPU Usage", "cpu")
        pipeline.add_widget(widget)
        pipeline.record_gauge("cpu", 75.0)
        data = pipeline.get_dashboard_data()
        assert "cpu-widget" in data

    def test_get_system_health(self):
        pipeline = MonitoringPipeline()
        health = pipeline.get_system_health()
        assert "timestamp" in health
        assert "active_alerts" in health
        assert "dashboard" in health

    def test_on_metric_callback(self):
        pipeline = MonitoringPipeline()
        received = []
        pipeline.on_metric(lambda name, sample: received.append((name, sample.value)))
        pipeline.record_gauge("cpu", 75.0)
        assert len(received) == 1
        assert received[0] == ("cpu", 75.0)


# =====================================================================
# Benchmark Engine Tests
# =====================================================================


class TestBenchmarkTask:
    def test_create(self):
        task = BenchmarkTask("t1", "Test Task", description="A test", category="math")
        assert task.task_id == "t1"
        assert task.name == "Test Task"
        assert task.difficulty == "medium"


class TestModelResult:
    def test_create(self):
        result = ModelResult(model_id="gpt-4", task_id="t1", score=0.9, latency_ms=100.0)
        assert result.model_id == "gpt-4"
        assert result.score == 0.9
        assert result.success is True


class TestBenchmarkScore:
    def test_create(self):
        score = BenchmarkScore(model_id="gpt-4", total_tasks=5, completed_tasks=4)
        assert score.model_id == "gpt-4"
        assert score.success_rate == 0.8

    def test_avg_score(self):
        score = BenchmarkScore(model_id="gpt-4")
        score.completed_tasks = 2
        score.total_score = 1.6
        assert score.avg_score == 0.8

    def test_to_dict(self):
        score = BenchmarkScore(model_id="gpt-4", total_tasks=3, completed_tasks=2, total_score=1.7)
        d = score.to_dict()
        assert d["model_id"] == "gpt-4"
        assert d["avg_score"] == 0.85


class TestBenchmarkEngine:
    def test_create(self):
        engine = BenchmarkEngine()
        assert len(engine._tasks) == 0

    def test_register_task(self):
        engine = BenchmarkEngine()
        task = BenchmarkTask("t1", "Test")
        engine.register_task(task)
        assert "t1" in engine._tasks

    def test_add_task(self):
        engine = BenchmarkEngine()
        task = engine.add_task("t1", "Test Task", category="math")
        assert task.task_id == "t1"
        assert "t1" in engine._tasks

    def test_register_model(self):
        engine = BenchmarkEngine()
        engine.register_model("mock", lambda t: ModelResult(model_id="mock", task_id=t.task_id, score=0.8))
        assert "mock" in engine._models

    def test_run_task(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Test")
        engine.register_model("mock", lambda t: ModelResult(model_id="mock", task_id=t.task_id, score=0.9))
        result = engine.run_task("t1", "mock")
        assert result is not None
        assert result.score == 0.9

    def test_run_benchmark(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")
        engine.add_task("t2", "Task 2")
        engine.register_model("model-a", lambda t: ModelResult(model_id="model-a", task_id=t.task_id, score=0.9))
        engine.register_model("model-b", lambda t: ModelResult(model_id="model-b", task_id=t.task_id, score=0.7))
        scores = engine.run_benchmark()
        assert "model-a" in scores
        assert "model-b" in scores
        assert scores["model-a"].avg_score == 0.9
        assert scores["model-b"].avg_score == 0.7

    def test_compare_models(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")
        engine.register_model("model-a", lambda t: ModelResult(model_id="model-a", task_id=t.task_id, score=0.9))
        engine.register_model("model-b", lambda t: ModelResult(model_id="model-b", task_id=t.task_id, score=0.7))
        engine.run_benchmark()
        ranking = engine.compare_models()
        assert ranking[0]["model_id"] == "model-a"
        assert ranking[1]["model_id"] == "model-b"

    def test_get_leaderboard(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")
        engine.register_model("model-a", lambda t: ModelResult(model_id="model-a", task_id=t.task_id, score=0.85))
        engine.run_benchmark()
        board = engine.get_leaderboard()
        assert len(board) == 1
        assert board[0]["model_id"] == "model-a"

    def test_get_task_results(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")
        engine.register_model("mock", lambda t: ModelResult(model_id="mock", task_id=t.task_id))
        engine.run_task("t1", "mock")
        results = engine.get_task_results("t1")
        assert len(results) == 1

    def test_generate_report(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")
        engine.register_model("mock", lambda t: ModelResult(model_id="mock", task_id=t.task_id, score=0.8))
        engine.run_benchmark()
        report = engine.generate_report()
        assert "leaderboard" in report
        assert "scores" in report
        assert report["total_tasks"] == 1

    def test_clear_results(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")
        engine.register_model("mock", lambda t: ModelResult(model_id="mock", task_id=t.task_id))
        engine.run_benchmark()
        engine.clear_results()
        assert len(engine._results) == 0
        assert len(engine._scores) == 0

    def test_run_task_model_failure(self):
        engine = BenchmarkEngine()
        engine.add_task("t1", "Task 1")

        def failing_executor(task):
            raise RuntimeError("Model unavailable")

        engine.register_model("failing", failing_executor)
        result = engine.run_task("t1", "failing")
        assert result.success is False
        assert "unavailable" in result.error
