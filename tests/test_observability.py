"""Tests for Observability & Evaluation Pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from observability import (
    LangSmithClient,
    ObservabilityPipeline,
    MetricType,
    TraceStatus,
)


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
