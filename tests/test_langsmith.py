"""Tests for langsmith/ — LangSmith Integration."""

from __future__ import annotations


from src.harness.langsmith import (
    TracingClient,
    TraceSpan,
    Dataset,
    EvalRunner,
    EvalResult,
    Experiment,
    ExperimentManager,
)


class TestTraceSpan:
    """Tests for TraceSpan."""

    def test_create_span(self):
        span = TraceSpan(name="test", inputs={"x": 1})
        assert span.name == "test"
        assert span.run_id is not None

    def test_end_span(self):
        span = TraceSpan(name="test")
        span.end(outputs={"result": "ok"})
        assert span.outputs == {"result": "ok"}

    def test_end_with_error(self):
        span = TraceSpan(name="test")
        span.end(error="fail")
        assert span.error == "fail"


class TestTracingClient:
    """Tests for TracingClient."""

    def test_start_span(self):
        tc = TracingClient()
        span = tc.start_span("test", inputs={"x": 1})
        assert span.name == "test"

    def test_end_span(self):
        tc = TracingClient()
        span = tc.start_span("test")
        ended = tc.end_span(span.run_id, outputs={"y": 2})
        assert ended is not None
        assert ended.outputs == {"y": 2}

    def test_parent_child_span(self):
        tc = TracingClient()
        parent = tc.start_span("parent")
        child = tc.start_span("child", parent_id=parent.run_id)
        assert child.parent_id == parent.run_id
        assert len(parent.children) == 1

    def test_get_traces(self):
        tc = TracingClient()
        tc.start_span("test")
        traces = tc.get_traces()
        assert len(traces) == 1

    def test_clear(self):
        tc = TracingClient()
        tc.start_span("test")
        tc.clear()
        assert len(tc.get_traces()) == 0


class TestDataset:
    """Tests for Dataset."""

    def test_create_dataset(self):
        ds = Dataset(name="test")
        assert ds.name == "test"
        assert ds.size == 0

    def test_add_entry(self):
        ds = Dataset(name="test")
        ds.add_entry(inputs={"q": "hello"}, expected_output="world")
        assert ds.size == 1

    def test_entry_has_id(self):
        ds = Dataset(name="test")
        entry = ds.add_entry(inputs={"q": "hi"})
        assert entry.entry_id is not None


class TestEvalRunner:
    """Tests for EvalRunner."""

    def test_run_eval(self):
        runner = EvalRunner()
        ds = Dataset(name="test")
        ds.add_entry(inputs={"q": "2+2"}, expected_output="4")
        results = runner.run_eval(ds, lambda inp: "4", lambda p, e, i: 1.0 if p == e else 0.0)
        assert len(results) == 1
        assert results[0].score == 1.0

    def test_run_eval_failure(self):
        runner = EvalRunner()
        ds = Dataset(name="test")
        ds.add_entry(inputs={"q": "test"}, expected_output="ok")
        results = runner.run_eval(ds, lambda inp: (_ for _ in ()).throw(ValueError("fail")))
        assert len(results) == 1
        assert results[0].score == 0.0


class TestExperiment:
    """Tests for Experiment."""

    def test_create_experiment(self):
        exp = Experiment(name="test")
        assert exp.name == "test"
        assert exp.avg_score == 0.0

    def test_avg_score(self):
        exp = Experiment(name="test")
        exp.results = [
            EvalResult(entry_id="1", predicted="a", expected="a", score=0.8),
            EvalResult(entry_id="2", predicted="b", expected="b", score=0.6),
        ]
        assert exp.avg_score == 0.7


class TestExperimentManager:
    """Tests for ExperimentManager."""

    def test_create_and_get(self):
        em = ExperimentManager()
        exp = em.create("test")
        assert em.get(exp.experiment_id) == exp

    def test_list_experiments(self):
        em = ExperimentManager()
        em.create("exp1")
        em.create("exp2")
        assert len(em.list_experiments()) == 2

    def test_compare(self):
        em = ExperimentManager()
        exp1 = em.create("exp1")
        exp1.results = [EvalResult(entry_id="1", predicted="a", expected="a", score=0.9)]
        exp2 = em.create("exp2")
        exp2.results = [EvalResult(entry_id="1", predicted="b", expected="b", score=0.5)]
        comparison = em.compare(exp1.experiment_id, exp2.experiment_id)
        assert len(comparison) == 2
        assert comparison[exp1.experiment_id] == 0.9
