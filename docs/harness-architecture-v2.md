# Hermes AGI/ASI Harness Architecture v2

> Updated system architecture incorporating all 14+ benchmark modules, unified scoring engine, and plugin-based extensibility.

---

## 1. Architecture Overview

The Hermes AGI/ASI Harness is a modular, plugin-based evaluation framework for measuring agent capabilities across reasoning, coding, math, language, bias, and safety dimensions. The architecture follows a layered design with clear separation between benchmark adapters, scoring aggregation, evaluation orchestration, and reporting.

### Design Principles

- **Modularity**: Each benchmark is an independent module with a unified adapter interface
- **Extensibility**: New benchmarks can be added without modifying existing code
- **Reproducibility**: All evaluations are deterministic with seed-controlled sampling
- **Scalability**: Thread-safe design supports concurrent benchmark execution
- **Transparency**: Full audit trail from raw results to aggregated scores

---

## 2. System Layers

### 2.1 Benchmark Layer

The benchmark layer contains individual benchmark implementations. Each benchmark provides:

- **Problem Loading**: Load problems from JSON files or built-in datasets
- **Execution**: Run evaluations against provided solutions
- **Scoring**: Compute pass rates, accuracy, or resolution rates

**Coding Benchmarks:**
- **HumanEval**: 164 Python programming problems with test-based evaluation
- **MBPP**: 974+ Mostly Basic Python Problems with automated test execution
- **SWE-bench Pro**: Production-grade software engineering tasks with patch evaluation

**Reasoning Benchmarks:**
- **HellaSwag**: 10,000 commonsense reasoning problems
- **BoolQ**: 15,000 yes/no question answering
- **PIQA**: Physical intuition question answering
- **OpenBookQA**: Open-book question answering with 500 problems
- **SIQA**: Social interaction question answering with 1,000 problems
- **WinoGrande**: Winograd Schema pronoun resolution with 440 problems
- **ARC-AGI-3**: 183 levels across 25 environments for abstract reasoning

**Math Benchmarks:**
- **GSM8K**: 1,319 grade school math word problems

**Language Benchmarks:**
- **MMLU**: 15,908 questions across 57 subjects

**Bias Benchmarks:**
- **Winogender**: 120 gender bias detection problems across 24 occupations

**Safety Benchmarks:**
- **RealToxicityPrompts**: Toxicity scoring for language generation

### 2.2 Adapter Layer

The adapter layer (`src/benchmark/adapters.py`) provides a unified interface for all benchmarks:

```python
class BenchmarkAdapter(Protocol):
    def load(self, path: str | None = None) -> int: ...
    def run(self, task_id: str, solution: str) -> TaskResult | None: ...
    def get_pass_rate(self) -> dict[str, float]: ...
```

**Adapter Types:**
- `HumanEvalAdapter`: Loads HumanEval problems, executes solutions against test cases
- `MBPPAdapter`: Loads MBPP problems, evaluates Python function correctness
- `MMLUAdapter`: Loads MMLU questions, compares predicted vs actual answers
- `GSM8KAdapter`: Loads math problems, extracts and compares numerical answers
- `SWEBenchProAdapter`: Loads SWE tasks, evaluates patch correctness via test results

**BenchmarkManager**: Central registry for all adapters providing unified access:
- `register(name, adapter)`: Register a benchmark adapter
- `load(name, path)`: Load problems for a benchmark
- `run(name, task_id, solution)`: Run a specific task
- `get_pass_rate(name)`: Get pass rate for a benchmark
- `get_all_pass_rates()`: Get all benchmark pass rates

### 2.3 Scoring Layer

The scoring layer (`src/benchmark/score_aggregator.py`) computes weighted scores across all benchmarks:

**BenchmarkScore**: Individual benchmark result with metadata
- `benchmark`: Benchmark name
- `category`: Evaluation category (reasoning, coding, math, language, bias, safety)
- `score`: Raw score (0-100 scale)
- `weight`: Relative weight for aggregation
- `num_problems`, `num_correct`: Problem counts
- `metadata`: Additional benchmark-specific data

**ScoreReport**: Aggregated report with:
- `overall_score`: Weighted average across all benchmarks
- `category_scores`: Scores grouped by category
- `benchmark_scores`: Individual benchmark scores
- `improvements`: Ranked list of benchmarks by improvement

**ScoreAggregator**: Core scoring engine:
- `compute_overall_score()`: Weighted average across all registered benchmarks
- `compute_category_score(category)`: Average score for a specific category
- `compute_benchmark_score(name)`: Score for a specific benchmark
- `rank_improvements()`: Rank benchmarks by improvement between runs
- `generate_score_report()`: Generate full ScoreReport with history tracking

### 2.4 Evaluation Layer

The evaluation layer (`src/benchmark/full_evaluation_suite.py`) orchestrates full benchmark runs:

**FullEvaluationSuite**: Main orchestration class
- `register_benchmark(name, benchmark, category)`: Register a benchmark with category
- `run_all_benchmarks()`: Execute all registered benchmarks
- `get_overall_score()`: Get weighted overall score (0-100)
- `get_category_scores()`: Get scores grouped by category
- `get_benchmark_scores()`: Get individual benchmark scores
- `get_improvements()`: Get improvement recommendations
- `generate_report()`: Generate full EvalReport

**EvalCategory**: Enum for benchmark categories
- REASONING, CODING, MATH, LANGUAGE, BIAS, SAFETY, GENERAL

**EvalResult**: Result of a single benchmark evaluation
- benchmark, category, total, passed, failed, score, duration_ms

**EvalReport**: Full evaluation report
- timestamp, overall_score, total_problems, total_passed, total_failed
- category_scores, benchmark_scores, improvements, results

### 2.5 Executive Agent Layer

The executive agent (`src/agent/executive_agent.py`) coordinates benchmark solving:

**ExecutiveAgent**: Central coordinator
- `register_benchmark(name, benchmark)`: Register a benchmark
- `create_plan(benchmark_names, strategy)`: Create evaluation plan
- `execute_plan(plan_id)`: Execute all tasks in a plan
- `get_overall_progress(plan_id)`: Get execution progress
- `get_plan_summary(plan_id)`: Get plan summary

**AgentTask**: Individual evaluation task
- id, benchmark, task_type, priority, status, result

**AgentPlan**: Collection of tasks with strategy
- id, tasks, strategy, progress tracking

---

## 3. Data Flow

### 3.1 Evaluation Pipeline

```
1. Register benchmarks → BenchmarkManager/FullEvaluationSuite
2. Load problems → benchmark.load_problems()
3. Execute evaluation → benchmark.run_all() / run_sample()
4. Collect results → benchmark.get_pass_rate()
5. Aggregate scores → ScoreAggregator.compute_overall_score()
6. Generate report → FullEvaluationSuite.generate_report()
```

### 3.2 Scoring Pipeline

```
1. Benchmark results → BenchmarkScore objects
2. Category grouping → ScoreAggregator.compute_category_score()
3. Weighted aggregation → ScoreAggregator.compute_overall_score()
4. Improvement ranking → ScoreAggregator.rank_improvements()
5. Report generation → ScoreAggregator.generate_score_report()
```

---

## 4. Module Inventory

### 4.1 Benchmark Modules

| Module | File | Tests | Problems |
|--------|------|-------|----------|
| HumanEval | human_eval_benchmark.py | 33 | 164 |
| MBPP | mbpp_benchmark.py | 33 | 974+ |
| SWE-bench Pro | swe_bench_pro_benchmark.py | 26 | Variable |
| SWE-bench Verified | swe_bench_verified_benchmark.py | 24 | Variable |
| HellaSwag | hellaswag_benchmark.py | 20 | 10,000 |
| BoolQ | boolq_benchmark.py | 22 | 15,000 |
| PIQA | piqa_benchmark.py | 20 | Variable |
| OpenBookQA | openbookqa_benchmark.py | 16 | 500 |
| SIQA | siqa_benchmark.py | 16 | 1,000 |
| WinoGrande | wino_grande_benchmark.py | 22 | 440 |
| Winogender | winogender_benchmark.py | 35 | 120 |
| MMLU | mmlu_benchmark.py | 20 | 15,908 |
| GSM8K | gsm8k_benchmark.py | 18 | 1,319 |
| ARC-AGI-3 | arc_agi_3_full_eval.py | 33 | 183 |
| RealToxicityPrompts | real_toxicity_prompts_benchmark.py | 18 | Variable |

### 4.2 Core Modules

| Module | File | Purpose |
|--------|------|---------|
| Adapters | adapters.py | Unified benchmark interface |
| Score Aggregator | score_aggregator.py | Weighted scoring engine |
| Full Evaluation Suite | full_evaluation_suite.py | Orchestration and reporting |
| Executive Agent | executive_agent.py | Benchmark coordination |

### 4.3 Test Coverage

| Test File | Tests |
|-----------|-------|
| test_adapters.py | 49 |
| test_score_aggregator.py | 37 |
| test_full_evaluation.py | 50 |
| test_executive_agent.py | 26 |
| test_siqa_benchmark.py | 16 |
| test_openbookqa.py | 16 |
| test_winogender_benchmark.py | 35 |
| test_mbpp.py | 33 |
| **Total** | **262+** |

---

## 5. Scoring Methodology

### 5.1 Score Computation

Each benchmark produces a raw score between 0 and 1. Scores are normalized to 0-100 scale for reporting.

**Per-Benchmark Score:**
```
score = (passed / total) * 100
```

**Category Score:**
```
category_score = sum(score_i * weight_i) / sum(weight_i)
```

**Overall Score:**
```
overall_score = sum(score_i * weight_i) / sum(weight_i)
```

### 5.2 Default Weights

All benchmarks have equal weight (1.0) by default. Weights can be adjusted based on priority:

```python
aggregator.add_score(BenchmarkScore(
    benchmark="mmlu",
    category="language",
    score=85.0,
    num_problems=100,
    num_correct=85,
    weight=1.0,  # Adjust based on priority
))
```

### 5.3 Improvement Tracking

The ScoreAggregator tracks score history across runs. `rank_improvements()` compares the most recent two scores for each benchmark and returns a ranked list of benchmarks by improvement magnitude.

---

## 6. Plugin System

The harness includes a plugin system for extensibility:

- **Action Plugins**: Extend agent action capabilities
- **Learning Plugins**: Add new learning strategies
- **Perception Plugins**: Enhance input processing
- **Reasoning Plugins**: Add reasoning strategies
- **Safety Plugins**: Add safety checks and constraints

Each plugin implements a base interface and is registered with the PluginManager.

---

## 7. Safety Architecture

### 7.1 Safety Modules

- **Safety Auditor**: Audits system behavior against safety invariants
- **Safety Enforcer**: Enforces safety constraints during execution
- **Threat Modeler**: Identifies potential threat vectors
- **Risk Assessor**: Evaluates risk levels of operations
- **Incident Responder**: Handles safety incidents

### 7.2 Safety Benchmarks

- **RealToxicityPrompts**: Measures toxicity in generated text
- **Winogender**: Detects gender bias in coreference resolution
- **Bias Detection**: Integrated across all benchmarks

---

## 8. Reporting

### 8.1 Report Types

**EvalReport**: Full evaluation report with:
- Overall score and category breakdowns
- Per-benchmark scores and statistics
- Improvement recommendations
- Execution metadata

**ScoreReport**: Aggregated scoring report with:
- Weighted overall score
- Category scores
- Benchmark scores
- Improvement rankings

**SWEBenchmarkReport**: SWE-bench specific report with:
- Resolution rate
- Per-repo breakdown
- Difficulty analysis

### 8.2 Report Persistence

Reports can be serialized to JSON for persistence and historical tracking. The ScoreAggregator maintains a history of all generated reports.

---

## 9. Threading and Concurrency

All benchmark modules use `threading.RLock` for thread safety. The FullEvaluationSuite supports concurrent benchmark execution for improved performance.

```python
class FullEvaluationSuite:
    def __init__(self):
        self._lock = threading.RLock()
        self._benchmarks: dict[str, Any] = {}
        self._results: list[EvalResult] = []
```

---

## 10. Future Extensions

### 10.1 Planned Benchmarks

- **MMLU-Pro**: Extended MMLU with harder problems
- **GPQA**: Graduate-level physics questions
- **GAIA**: General AI assistant benchmark
- **Terminal**: Terminal/command-line tasks

### 10.2 Architecture Improvements

- **Distributed Execution**: Run benchmarks across multiple machines
- **Incremental Evaluation**: Only re-run changed benchmarks
- **Adaptive Difficulty**: Adjust problem difficulty based on performance
- **Multi-Modal Support**: Extend beyond text to images, audio, video

---

## 11. Conclusion

The Hermes AGI/ASI Harness Architecture v2 provides a comprehensive, extensible framework for evaluating AI agent capabilities across 14+ benchmarks spanning reasoning, coding, math, language, bias, and safety dimensions. The modular design with unified adapters, weighted scoring, and plugin-based extensibility ensures the system can evolve with new benchmarks and evaluation methodologies.

The architecture's layered design—benchmark, adapter, scoring, evaluation, and executive agent—provides clear separation of concerns while enabling powerful cross-benchmark analysis and reporting. With 262+ tests across all modules, the system is robust and ready for production use.
