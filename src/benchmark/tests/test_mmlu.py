"""Tests for MMLU benchmark — 53 tests."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.benchmark.mmlu_benchmark import (
    MMLUBenchmark,
    Question,
    CategoryResult,
    QuestionStatus,
    MMLU_CATEGORIES,
    QUESTIONS_PER_CATEGORY,
)


def test_benchmark_init():
    """Test benchmark initialization."""
    bench = MMLUBenchmark()
    assert bench._questions == {}
    assert bench._category_index == {}


def test_load_categories():
    """Test loading categories."""
    bench = MMLUBenchmark()
    categories = bench.load_categories()
    assert len(categories) == 57
    assert "abstract_algebra" in categories
    assert "world_religions" in categories


def test_generate_questions():
    """Test generating questions for a category."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=10)
    assert len(questions) == 10
    assert all(q.category == "high_school_mathematics" for q in questions)


def test_generate_all():
    """Test generating all questions."""
    bench = MMLUBenchmark()
    total = bench.generate_all()
    assert total == 57 * QUESTIONS_PER_CATEGORY


def test_count_questions():
    """Test counting questions."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    assert bench.count_questions() == 5


def test_run_question():
    """Test running a single question."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=1)
    qid = questions[0].id
    correct = questions[0].correct_answer
    result = bench.run_question(qid, correct)
    assert result is True


def test_run_question_incorrect():
    """Test running a question with wrong answer."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=1)
    qid = questions[0].id
    wrong = (questions[0].correct_answer + 1) % 4
    result = bench.run_question(qid, wrong)
    assert result is False


def test_run_question_not_found():
    """Test running a non-existent question."""
    bench = MMLUBenchmark()
    result = bench.run_question("nonexistent", 0)
    assert result is False


def test_run_questions():
    """Test running multiple questions."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=3)
    answers = {q.id: q.correct_answer for q in questions}
    results = bench.run_questions(answers)
    assert len(results) == 3
    assert all(results.values())


def test_get_accuracy():
    """Test getting accuracy."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=4)
    for q in questions[:2]:
        bench.run_question(q.id, q.correct_answer)
    for q in questions[2:]:
        bench.run_question(q.id, (q.correct_answer + 1) % 4)
    acc = bench.get_accuracy("high_school_mathematics")
    assert acc == 0.5


def test_get_accuracy_no_questions():
    """Test getting accuracy with no questions."""
    bench = MMLUBenchmark()
    acc = bench.get_accuracy("high_school_mathematics")
    assert acc == 0.0


def test_get_overall():
    """Test getting overall results."""
    bench = MMLUBenchmark()
    bench.generate_all()
    overall = bench.get_overall()
    assert overall["total_questions"] == 57 * QUESTIONS_PER_CATEGORY
    assert overall["categories"] == 57


def test_get_category_results():
    """Test getting category results."""
    bench = MMLUBenchmark()
    bench.generate_all()
    results = bench.get_category_results()
    assert len(results) == 57


def test_question_status_enum():
    """Test QuestionStatus enum values."""
    assert QuestionStatus.PENDING.value == "pending"
    assert QuestionStatus.CORRECT.value == "correct"
    assert QuestionStatus.INCORRECT.value == "incorrect"
    assert QuestionStatus.SKIPPED.value == "skipped"


def test_question_dataclass():
    """Test Question dataclass."""
    q = Question(
        id="test_001",
        category="high_school_mathematics",
        text="What is 2+2?",
        options=["3", "4", "5", "6"],
        correct_answer=1,
    )
    assert q.id == "test_001"
    assert q.category == "high_school_mathematics"
    assert q.correct_answer == 1
    assert q.status == QuestionStatus.PENDING


def test_category_result_dataclass():
    """Test CategoryResult dataclass."""
    result = CategoryResult(
        category="high_school_mathematics",
        total=10,
        correct=7,
        incorrect=3,
        accuracy=0.7,
    )
    assert result.category == "high_school_mathematics"
    assert result.total == 10
    assert result.accuracy == 0.7


def test_get_state():
    """Test getting benchmark state."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    state = bench.get_state()
    assert state["total_questions"] == 5
    assert state["categories"] == 1


def test_search_by_category():
    """Test searching by category."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    results = bench.search(category="high_school_mathematics")
    assert len(results) == 5


def test_search_by_query():
    """Test searching by query."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    results = bench.search(category="high_school_mathematics", query="Question 1")
    assert len(results) >= 1


def test_search_no_results():
    """Test searching with no results."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    results = bench.search(category="nonexistent")
    assert len(results) == 0


def test_multiple_categories():
    """Test generating questions for multiple categories."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    bench.generate_questions("high_school_biology", count=3)
    assert bench.count_questions() == 8
    assert len(bench._category_index) == 2


def test_load_questions_all():
    """Test loading all questions."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    questions = bench.load_questions()
    assert len(questions) == 5


def test_load_questions_by_category():
    """Test loading questions by category."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    bench.generate_questions("high_school_biology", count=3)
    math_questions = bench.load_questions("high_school_mathematics")
    assert len(math_questions) == 5


def test_accuracy_per_category():
    """Test accuracy per category."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=4)
    bench.generate_questions("high_school_biology", count=4)
    
    math_qs = bench.load_questions("high_school_mathematics")
    for q in math_qs[:2]:
        bench.run_question(q.id, q.correct_answer)
    for q in math_qs[2:]:
        bench.run_question(q.id, (q.correct_answer + 1) % 4)
    
    math_acc = bench.get_accuracy("high_school_mathematics")
    assert math_acc == 0.5
    
    bio_acc = bench.get_accuracy("high_school_biology")
    assert bio_acc == 0.0


def test_all_categories_generated():
    """Test that all 57 categories can be generated."""
    bench = MMLUBenchmark()
    total = bench.generate_all()
    assert total == 14022


def test_category_results_count():
    """Test that category results returns all 57 categories."""
    bench = MMLUBenchmark()
    bench.generate_all()
    results = bench.get_category_results()
    assert len(results) == 57


def test_questions_have_unique_ids():
    """Test that generated questions have unique IDs."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=10)
    ids = [q.id for q in questions]
    assert len(ids) == len(set(ids))


def test_questions_have_four_options():
    """Test that questions have exactly 4 options."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=5)
    for q in questions:
        assert len(q.options) == 4


def test_correct_answer_in_range():
    """Test that correct_answer is in valid range."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=10)
    for q in questions:
        assert q.correct_answer in [0, 1, 2, 3]


def test_question_status_after_run():
    """Test that question status updates after run."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=1)
    q = questions[0]
    
    assert q.status == QuestionStatus.PENDING
    
    bench.run_question(q.id, q.correct_answer)
    assert q.status == QuestionStatus.CORRECT
    
    q2 = bench.generate_questions("high_school_biology", count=1)[0]
    bench.run_question(q2.id, (q2.correct_answer + 1) % 4)
    assert q2.status == QuestionStatus.INCORRECT


def test_get_overall_after_run():
    """Test overall results after running questions."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=4)
    questions = bench.load_questions("high_school_mathematics")
    
    for q in questions[:2]:
        bench.run_question(q.id, q.correct_answer)
    for q in questions[2:]:
        bench.run_question(q.id, (q.correct_answer + 1) % 4)
    
    overall = bench.get_overall()
    assert overall["attempted"] == 4
    assert overall["correct"] == 2
    assert overall["accuracy"] == 0.5


def test_mmlu_categories_constant():
    """Test MMLU_CATEGORIES constant."""
    assert len(MMLU_CATEGORIES) == 57
    assert "abstract_algebra" in MMLU_CATEGORIES
    assert "world_religions" in MMLU_CATEGORIES


def test_questions_per_category_constant():
    """Test QUESTIONS_PER_CATEGORY constant."""
    assert QUESTIONS_PER_CATEGORY == 246


def test_benchmark_id_is_unique():
    """Test that each benchmark has a unique ID."""
    bench1 = MMLUBenchmark()
    bench2 = MMLUBenchmark()
    assert bench1.id != bench2.id


def test_empty_benchmark_state():
    """Test empty benchmark state."""
    bench = MMLUBenchmark()
    state = bench.get_state()
    assert state["total_questions"] == 0
    assert state["categories"] == 0


def test_generate_questions_twice():
    """Test generating questions for same category twice."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    bench.generate_questions("high_school_mathematics", count=3)
    assert bench.count_questions() == 8


def test_run_same_question_twice():
    """Test running the same question twice."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=1)
    q = questions[0]
    
    result1 = bench.run_question(q.id, q.correct_answer)
    assert result1 is True
    
    result2 = bench.run_question(q.id, q.correct_answer)
    assert result2 is True


def test_category_result_accuracy_calculation():
    """Test category result accuracy calculation."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=4)
    questions = bench.load_questions("high_school_mathematics")
    
    for q in questions[:3]:
        bench.run_question(q.id, q.correct_answer)
    bench.run_question(questions[3].id, (questions[3].correct_answer + 1) % 4)
    
    results = bench.get_category_results()
    math_result = [r for r in results if r.category == "high_school_mathematics"][0]
    assert math_result.accuracy == 0.75


def test_search_case_insensitive():
    """Test that search is case insensitive."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    results = bench.search(category="high_school_mathematics", query="QUESTION")
    assert len(results) == 5


def test_load_questions_nonexistent_category():
    """Test loading questions for non-existent category."""
    bench = MMLUBenchmark()
    questions = bench.load_questions("nonexistent")
    assert len(questions) == 0


def test_get_accuracy_nonexistent_category():
    """Test getting accuracy for non-existent category."""
    bench = MMLUBenchmark()
    acc = bench.get_accuracy("nonexistent")
    assert acc == 0.0


def test_total_questions_after_generate_all():
    """Test total questions after generating all."""
    bench = MMLUBenchmark()
    bench.generate_all()
    assert bench.count_questions() == 14022


def test_category_index_populated():
    """Test that category index is populated."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    assert "high_school_mathematics" in bench._category_index
    assert len(bench._category_index["high_school_mathematics"]) == 5


def test_generate_all_returns_correct_count():
    """Test that generate_all returns correct total."""
    bench = MMLUBenchmark()
    total = bench.generate_all()
    assert total == 14022


def test_multiple_benchmarks_independent():
    """Test that multiple benchmarks are independent."""
    bench1 = MMLUBenchmark()
    bench2 = MMLUBenchmark()
    
    bench1.generate_questions("high_school_mathematics", count=5)
    bench2.generate_questions("high_school_biology", count=3)
    
    assert bench1.count_questions() == 5
    assert bench2.count_questions() == 3


def test_overall_results_structure():
    """Test overall results dictionary structure."""
    bench = MMLUBenchmark()
    bench.generate_all()
    overall = bench.get_overall()
    
    assert "total_questions" in overall
    assert "attempted" in overall
    assert "correct" in overall
    assert "accuracy" in overall
    assert "categories" in overall


def test_category_results_structure():
    """Test category results structure."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=5)
    results = bench.get_category_results()
    
    assert len(results) == 57
    for r in results:
        assert hasattr(r, "category")
        assert hasattr(r, "total")
        assert hasattr(r, "correct")
        assert hasattr(r, "incorrect")
        assert hasattr(r, "accuracy")


def test_question_options_are_abcd():
    """Test that question options are A, B, C, D."""
    bench = MMLUBenchmark()
    questions = bench.generate_questions("high_school_mathematics", count=5)
    for q in questions:
        assert q.options == ["A", "B", "C", "D"]


def test_benchmark_with_all_categories():
    """Test benchmark with all categories."""
    bench = MMLUBenchmark()
    bench.generate_all()
    
    categories = bench.load_categories()
    assert len(categories) == 57
    
    for cat in categories:
        questions = bench.load_questions(cat)
        assert len(questions) == QUESTIONS_PER_CATEGORY


def test_run_all_questions():
    """Test running all questions."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=10)
    questions = bench.load_questions("high_school_mathematics")
    
    results = bench.run_questions({q.id: q.correct_answer for q in questions})
    assert len(results) == 10
    assert all(results.values())


def test_accuracy_with_all_correct():
    """Test accuracy when all answers are correct."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=10)
    questions = bench.load_questions("high_school_mathematics")
    
    for q in questions:
        bench.run_question(q.id, q.correct_answer)
    
    acc = bench.get_accuracy("high_school_mathematics")
    assert acc == 1.0


def test_accuracy_with_all_incorrect():
    """Test accuracy when all answers are incorrect."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=10)
    questions = bench.load_questions("high_school_mathematics")
    
    for q in questions:
        bench.run_question(q.id, (q.correct_answer + 1) % 4)
    
    acc = bench.get_accuracy("high_school_mathematics")
    assert acc == 0.0


def test_get_overall_zero_accuracy():
    """Test overall with zero accuracy."""
    bench = MMLUBenchmark()
    bench.generate_questions("high_school_mathematics", count=4)
    questions = bench.load_questions("high_school_mathematics")
    
    for q in questions:
        bench.run_question(q.id, (q.correct_answer + 1) % 4)
    
    overall = bench.get_overall()
    assert overall["accuracy"] == 0.0
