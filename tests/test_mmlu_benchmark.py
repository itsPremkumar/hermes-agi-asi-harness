"""Tests for MMLUBenchmark."""
from benchmarks.mmlu_benchmark import (
    AGENT_API_VERSION,
    MMLU_CATEGORIES,
    QUESTIONS_PER_CATEGORY,
    CategoryResult,
    MMLUBenchmark,
    Question,
    QuestionStatus,
)


class TestMMLUBenchmark:
    def test_create(self):
        bench = MMLUBenchmark()
        assert bench.count_questions() == 0

    def test_load_categories(self):
        bench = MMLUBenchmark()
        categories = bench.load_categories()
        assert len(categories) == 57

    def test_generate_questions(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 10)
        assert len(questions) == 10
        assert bench.count_questions() == 10

    def test_generate_all(self):
        bench = MMLUBenchmark()
        total = bench.generate_all()
        assert total == 57 * QUESTIONS_PER_CATEGORY
        assert bench.count_questions() == 57 * QUESTIONS_PER_CATEGORY

    def test_run_question_correct(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 1)
        q = questions[0]
        assert bench.run_question(q.id, q.correct_answer) is True
        assert q.status == QuestionStatus.CORRECT

    def test_run_question_incorrect(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 1)
        q = questions[0]
        wrong = (q.correct_answer + 1) % 4
        assert bench.run_question(q.id, wrong) is False
        assert q.status == QuestionStatus.INCORRECT

    def test_run_question_not_found(self):
        bench = MMLUBenchmark()
        assert bench.run_question("nonexistent", 0) is False

    def test_run_questions(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 3)
        answers = {q.id: q.correct_answer for q in questions}
        results = bench.run_questions(answers)
        assert all(results.values())
        assert len(results) == 3

    def test_get_accuracy(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 4)
        for i, q in enumerate(questions):
            bench.run_question(q.id, q.correct_answer if i < 3 else (q.correct_answer + 1) % 4)
        accuracy = bench.get_accuracy("abstract_algebra")
        assert accuracy == 0.75

    def test_get_accuracy_empty(self):
        bench = MMLUBenchmark()
        assert bench.get_accuracy("abstract_algebra") == 0.0

    def test_get_overall(self):
        bench = MMLUBenchmark()
        bench.generate_all()
        overall = bench.get_overall()
        assert overall["total_questions"] == 57 * QUESTIONS_PER_CATEGORY
        assert overall["categories"] == 57
        assert overall["accuracy"] == 0.0

    def test_get_overall_after_run(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 4)
        for i, q in enumerate(questions):
            bench.run_question(q.id, q.correct_answer if i < 2 else (q.correct_answer + 1) % 4)
        overall = bench.get_overall()
        assert overall["attempted"] == 4
        assert overall["correct"] == 2
        assert overall["accuracy"] == 0.5

    def test_get_category_results(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 10)
        results = bench.get_category_results()
        assert len(results) == 57
        abstract_algebra = next(r for r in results if r.category == "abstract_algebra")
        assert abstract_algebra.total == 10

    def test_get_category_results_after_run(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 4)
        for i, q in enumerate(questions):
            bench.run_question(q.id, q.correct_answer if i < 3 else (q.correct_answer + 1) % 4)
        results = bench.get_category_results()
        abstract_algebra = next(r for r in results if r.category == "abstract_algebra")
        assert abstract_algebra.correct == 3
        assert abstract_algebra.incorrect == 1
        assert abstract_algebra.accuracy == 0.75

    def test_load_questions_by_category(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 5)
        bench.generate_questions("anatomy", 5)
        questions = bench.load_questions("abstract_algebra")
        assert len(questions) == 5

    def test_load_questions_all(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 5)
        bench.generate_questions("anatomy", 5)
        questions = bench.load_questions()
        assert len(questions) == 10

    def test_load_questions_empty(self):
        bench = MMLUBenchmark()
        assert bench.load_questions("abstract_algebra") == []

    def test_count_categories(self):
        bench = MMLUBenchmark()
        categories = bench.load_categories()
        assert len(categories) == 57
        assert "abstract_algebra" in categories
        assert "world_religions" in categories

    def test_count_questions(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 10)
        assert bench.count_questions() == 10

    def test_question_has_4_options(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 1)
        assert len(questions[0].options) == 4

    def test_question_correct_answer_in_range(self):
        bench = MMLUBenchmark()
        questions = bench.generate_questions("abstract_algebra", 10)
        for q in questions:
            assert 0 <= q.correct_answer <= 3


class TestMMLUCategories:
    def test_57_categories(self):
        assert len(MMLU_CATEGORIES) == 57

    def test_all_unique(self):
        assert len(set(MMLU_CATEGORIES)) == 57

    def test_questions_per_category(self):
        assert QUESTIONS_PER_CATEGORY == 246

    def test_total_questions(self):
        assert len(MMLU_CATEGORIES) * QUESTIONS_PER_CATEGORY == 14022

    def test_categories_contain_stem(self):
        assert "abstract_algebra" in MMLU_CATEGORIES
        assert "machine_learning" in MMLU_CATEGORIES

    def test_categories_contain_humanities(self):
        assert "philosophy" in MMLU_CATEGORIES
        assert "world_religions" in MMLU_CATEGORIES

    def test_categories_contain_social_sciences(self):
        assert "sociology" in MMLU_CATEGORIES
        assert "us_foreign_policy" in MMLU_CATEGORIES


class TestCategoryResult:
    def test_create(self):
        result = CategoryResult(category="abstract_algebra", total=10, correct=8, incorrect=2, accuracy=0.8)
        assert result.category == "abstract_algebra"
        assert result.total == 10
        assert result.accuracy == 0.8


class TestQuestion:
    def test_create(self):
        q = Question(id="q1", category="abstract_algebra", text="What is 1+1?", options=["A", "B", "C", "D"], correct_answer=0)
        assert q.id == "q1"
        assert q.status == QuestionStatus.PENDING


class TestAgentApiVersion:
    def test_version_format(self):
        parts = AGENT_API_VERSION.split(".")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_version_is_1_0(self):
        assert AGENT_API_VERSION == "1.0"


class TestMMLUQuestionStatus:
    def test_pending(self):
        assert QuestionStatus.PENDING.value == "pending"

    def test_correct(self):
        assert QuestionStatus.CORRECT.value == "correct"

    def test_incorrect(self):
        assert QuestionStatus.INCORRECT.value == "incorrect"

    def test_skipped(self):
        assert QuestionStatus.SKIPPED.value == "skipped"


class TestMMLUBenchmarkGetState:
    def test_get_state_empty(self):
        bench = MMLUBenchmark()
        state = bench.get_state()
        assert state["total_questions"] == 0
        assert state["categories"] == 0

    def test_get_state_with_questions(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 10)
        state = bench.get_state()
        assert state["total_questions"] == 10
        assert state["categories"] == 1


class TestMMLUBenchmarkSearch:
    def test_search_by_category(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 5)
        results = bench.search(category="abstract_algebra")
        assert len(results) == 5

    def test_search_all(self):
        bench = MMLUBenchmark()
        bench.generate_questions("abstract_algebra", 5)
        bench.generate_questions("anatomy", 3)
        results = bench.search()
        assert len(results) == 8
