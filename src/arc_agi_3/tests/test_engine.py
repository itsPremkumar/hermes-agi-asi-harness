"""Tests for ARC-AGI-3 Core Engine."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from arc_agi_3.engine import (
    Engine, Grid, Rule, Strategy, Solution, Task, Diagnostics,
    RuleHypothesizer, StrategySelector, SolutionGenerator, SolutionVerifier,
    Stage, Status,
)


# ============== Grid Tests ==============

class TestGrid:
    def test_create(self):
        grid = Grid([[1, 2], [3, 4]])
        assert grid.width == 2
        assert grid.height == 2

    def test_get(self):
        grid = Grid([[1, 2], [3, 4]])
        assert grid.get(0, 0) == 1
        assert grid.get(1, 1) == 4

    def test_get_out_of_bounds(self):
        grid = Grid([[1, 2]])
        assert grid.get(5, 5) == 0

    def test_set(self):
        grid = Grid([[1, 2]])
        grid.set(2, 0, 5)
        assert grid.get(2, 0) == 5

    def test_equals(self):
        g1 = Grid([[1, 2], [3, 4]])
        g2 = Grid([[1, 2], [3, 4]])
        assert g1.equals(g2) is True

    def test_not_equals(self):
        g1 = Grid([[1, 2]])
        g2 = Grid([[1, 3]])
        assert g1.equals(g2) is False

    def test_fingerprint(self):
        grid = Grid([[1, 2]])
        assert len(grid.fingerprint()) == 16


# ============== Rule Tests ==============

class TestRule:
    def test_create(self):
        rule = Rule(id="r1", name="test", description="test rule")
        assert rule.id == "r1"
        assert rule.confidence == 0.5
        assert rule.evidence == []


# ============== Strategy Tests ==============

class TestStrategy:
    def test_create(self):
        strategy = Strategy(id="s1", name="test", description="test")
        assert strategy.id == "s1"
        assert strategy.estimated_cost == 1.0


# ============== Solution Tests ==============

class TestSolution:
    def test_create(self):
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        assert sol.id == "sol1"
        assert sol.verified is False
        assert sol.score == 0.0


# ============== Task Tests ==============

class TestTask:
    def test_create(self):
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        assert task.id == "t1"
        assert task.status == Status.PENDING
        assert task.solution is None


# ============== Diagnostics Tests ==============

class TestDiagnostics:
    def test_create(self):
        diag = Diagnostics()
        assert diag.issues == []
        assert diag.suggestions == []


# ============== Stage Tests ==============

class TestStage:
    def test_stages(self):
        assert Stage.PERCEIVE.value == "perceive"
        assert Stage.REASON.value == "reason"
        assert Stage.PLAN.value == "plan"
        assert Stage.ACT.value == "act"
        assert Stage.EVALUATE.value == "evaluate"
        assert Stage.DIAGNOSE.value == "diagnose"
        assert Stage.REVISE.value == "revise"


# ============== Status Tests ==============

class TestStatus:
    def test_statuses(self):
        assert Status.PENDING.value == "pending"
        assert Status.RUNNING.value == "running"
        assert Status.COMPLETED.value == "completed"
        assert Status.FAILED.value == "failed"


# ============== RuleHypothesizer Tests ==============

class TestRuleHypothesizer:
    def test_create(self):
        rh = RuleHypothesizer()
        assert rh.get_all_rules() == []

    def test_hypothesize_empty(self):
        rh = RuleHypothesizer()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        rules = rh.hypothesize(task)
        assert rules == []

    def test_hypothesize_with_examples(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[
                (Grid([[1, 2]]), Grid([[1, 2], [3, 4]])),
            ],
        )
        rules = rh.hypothesize(task)
        assert len(rules) >= 1

    def test_hypothesize_symmetry(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2, 1]]),
            examples=[
                (Grid([[1, 2, 1]]), Grid([[1, 2, 1]])),
            ],
        )
        rules = rh.hypothesize(task)
        rule_names = [r.name for r in rules]
        assert "vertical symmetry" in rule_names

    def test_get_rule(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[1, 2], [3, 4]]))],
        )
        rules = rh.hypothesize(task)
        if rules:
            retrieved = rh.get_rule(rules[0].id)
            assert retrieved is not None

    def test_reinforce_success(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[1, 2], [3, 4]]))],
        )
        rules = rh.hypothesize(task)
        if rules:
            rh.reinforce(rules[0].id, True)
            assert rules[0].confidence > 0.5

    def test_reinforce_failure(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[1, 2], [3, 4]]))],
        )
        rules = rh.hypothesize(task)
        if rules:
            rh.reinforce(rules[0].id, False)
            assert rules[0].confidence < 0.5


# ============== StrategySelector Tests ==============

class TestStrategySelector:
    def test_create(self):
        ss = StrategySelector()
        assert len(ss.list_strategies()) == 5

    def test_select_strategy(self):
        ss = StrategySelector()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        strategy = ss.select_strategy(task, [])
        assert strategy is not None

    def test_select_strategy_with_rules(self):
        ss = StrategySelector()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        rules = [Rule(id="r1", name="pattern_match", description="test")]
        strategy = ss.select_strategy(task, rules)
        assert strategy is not None

    def test_record_performance(self):
        ss = StrategySelector()
        ss.record_performance("s1", True)
        ss.record_performance("s1", False)

    def test_get_strategy(self):
        ss = StrategySelector()
        strategy = ss.get_strategy("s1")
        assert strategy is not None
        assert strategy.name == "pattern_match"


# ============== SolutionGenerator Tests ==============

class TestSolutionGenerator:
    def test_create(self):
        sg = SolutionGenerator()
        assert sg.get_solution("nonexistent") is None

    def test_generate_pattern_match(self):
        sg = SolutionGenerator()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        strategy = Strategy(id="s1", name="pattern_match", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) >= 1

    def test_generate_decompose(self):
        sg = SolutionGenerator()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        strategy = Strategy(id="s2", name="decompose", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) >= 1

    def test_generate_brute_force(self):
        sg = SolutionGenerator()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        strategy = Strategy(id="s3", name="brute_force", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) >= 1

    def test_generate_analogy(self):
        sg = SolutionGenerator()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        strategy = Strategy(id="s4", name="analogy", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) >= 1

    def test_generate_abstraction(self):
        sg = SolutionGenerator()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        strategy = Strategy(id="s5", name="abstraction", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) >= 1

    def test_get_solution(self):
        sg = SolutionGenerator()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        strategy = Strategy(id="s1", name="pattern_match", description="test")
        solutions = sg.generate(task, strategy, [])
        if solutions:
            retrieved = sg.get_solution(solutions[0].id)
            assert retrieved is not None


# ============== SolutionVerifier Tests ==============

class TestSolutionVerifier:
    def test_create(self):
        sv = SolutionVerifier()
        assert sv.get_result("nonexistent") is None

    def test_verify_exact_match(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[3, 4]]), target_grid=Grid([[1, 2]]))
        result = sv.verify(sol, task)
        assert result["verified"] is True
        assert result["exact_match"] is True

    def test_verify_mismatch(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[3, 4]]), target_grid=Grid([[5, 6]]))
        result = sv.verify(sol, task)
        assert result["verified"] is False

    def test_verify_no_target(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[3, 4]]))
        result = sv.verify(sol, task)
        assert result["verified"] is False

    def test_similarity(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2], [3, 4]]))
        task = Task(id="t1", input_grid=Grid([[0, 0]]), target_grid=Grid([[1, 2], [3, 5]]))
        result = sv.verify(sol, task)
        assert result["similarity"] == 0.75

    def test_get_result(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[3, 4]]), target_grid=Grid([[1, 2]]))
        sv.verify(sol, task)
        result = sv.get_result("sol1")
        assert result is not None


# ============== Engine Tests ==============

class TestEngine:
    def test_create(self):
        engine = Engine(max_iterations=5)
        assert engine.iteration == 0

    def test_submit_task(self):
        engine = Engine()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        engine.submit_task(task)
        assert engine.get_task("t1") is not None

    def test_solve_simple(self):
        engine = Engine(max_iterations=5)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        result = engine.solve(task)
        assert "solved" in result
        assert "iterations" in result

    def test_solve_completed(self):
        engine = Engine(max_iterations=5)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        engine.solve(task)
        assert task.status in (Status.COMPLETED, Status.FAILED)

    def test_solve_with_string_id(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        engine.submit_task(task)
        result = engine.solve("t1")
        assert "solved" in result

    def test_solve_not_found(self):
        engine = Engine()
        result = engine.solve("nonexistent")
        assert "error" in result

    def test_get_diagnostics(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[9, 9]]),
            examples=[(Grid([[1, 2]]), Grid([[9, 9]]))],
        )
        engine.solve(task)
        diag = engine.get_diagnostics("t1")
        assert diag is not None

    def test_get_status(self):
        engine = Engine()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        engine.submit_task(task)
        status = engine.get_status()
        assert "total_tasks" in status
        assert status["total_tasks"] == 1

    def test_multiple_tasks(self):
        engine = Engine(max_iterations=3)
        for i in range(3):
            task = Task(
                id=f"t{i}",
                input_grid=Grid([[i, i+1]]),
                target_grid=Grid([[i+2, i+3]]),
                examples=[(Grid([[i, i+1]]), Grid([[i+2, i+3]]))],
            )
            engine.submit_task(task)
        status = engine.get_status()
        assert status["total_tasks"] == 3

    def test_rules_generated(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        engine.solve(task)
        status = engine.get_status()
        assert status["rules"] >= 0

    def test_iteration_count(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[9, 9]]),
            examples=[(Grid([[1, 2]]), Grid([[9, 9]]))],
        )
        engine.solve(task)
        assert engine.iteration >= 1

    def test_max_iterations_respected(self):
        engine = Engine(max_iterations=2)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[9, 9]]),
            examples=[(Grid([[1, 2]]), Grid([[9, 9]]))],
        )
        result = engine.solve(task)
        assert result["iterations"] <= 2

    def test_solution_attached(self):
        engine = Engine(max_iterations=5)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        engine.solve(task)
        if task.status == Status.COMPLETED:
            assert task.solution is not None

    def test_custom_components(self):
        rh = RuleHypothesizer()
        ss = StrategySelector()
        sg = SolutionGenerator()
        sv = SolutionVerifier()
        engine = Engine(
            hypothesizer=rh,
            selector=ss,
            generator=sg,
            verifier=sv,
            max_iterations=3,
        )
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        result = engine.solve(task)
        assert "solved" in result

    def test_grid_three_columns(self):
        grid = Grid([[1, 2, 3], [4, 5, 6]])
        assert grid.width == 3
        assert grid.height == 2

    def test_grid_set_expands(self):
        grid = Grid([[1]])
        grid.set(3, 2, 9)
        assert grid.get(3, 2) == 9

    def test_task_with_multiple_examples(self):
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            examples=[
                (Grid([[1]]), Grid([[2]])),
                (Grid([[3]]), Grid([[4]])),
            ],
        )
        assert len(task.examples) == 2

    def test_hypothesize_color_change(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[0, 0]]),
            examples=[(Grid([[0, 0]]), Grid([[1, 1]]))],
        )
        rules = rh.hypothesize(task)
        rule_names = [r.name for r in rules]
        assert any("add colors" in n for n in rule_names)

    def test_hypothesize_horizontal_symmetry(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2, 1]]),
            examples=[(Grid([[1, 2, 1]]), Grid([[1, 2, 1]]))],
        )
        rules = rh.hypothesize(task)
        rule_names = [r.name for r in rules]
        assert "horizontal symmetry" in rule_names

    def test_strategy_with_empty_rules(self):
        ss = StrategySelector()
        task = Task(id="t1", input_grid=Grid([[1]]))
        strategy = ss.select_strategy(task, [])
        assert strategy is not None

    def test_strategy_performance_affects_selection(self):
        ss = StrategySelector()
        task = Task(id="t1", input_grid=Grid([[1]]))
        for _ in range(10):
            ss.record_performance("s5", True)
        strategy = ss.select_strategy(task, [])
        assert strategy.id == "s5"

    def test_generate_empty_examples(self):
        sg = SolutionGenerator()
        task = Task(id="t1", input_grid=Grid([[1, 2]]))
        strategy = Strategy(id="s1", name="pattern_match", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) == 0

    def test_verify_dimension_mismatch(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[0]]), target_grid=Grid([[1, 2], [3, 4]]))
        result = sv.verify(sol, task)
        assert result["dimension_match"] is False

    def test_verify_similarity_partial(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 0], [0, 4]]))
        task = Task(id="t1", input_grid=Grid([[0, 0]]), target_grid=Grid([[1, 2], [3, 4]]))
        result = sv.verify(sol, task)
        assert result["similarity"] == 0.5

    def test_engine_iteration_increments(self):
        engine = Engine(max_iterations=5)
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[9]]),
            examples=[(Grid([[1]]), Grid([[9]]))],
        )
        engine.solve(task)
        assert engine.iteration >= 1

    def test_engine_status_rules_count(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4], [5, 6]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4], [5, 6]]))],
        )
        engine.solve(task)
        status = engine.get_status()
        assert status["rules"] > 0

    def test_solve_returns_iterations(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[9]]),
            examples=[(Grid([[1]]), Grid([[9]]))],
        )
        result = engine.solve(task)
        assert result["iterations"] <= 3

    def test_solution_verified_flag(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[0]]), target_grid=Grid([[1, 2]]))
        sv.verify(sol, task)
        assert sol.verified is True

    def test_diagnostics_has_issues_on_failure(self):
        engine = Engine(max_iterations=2)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[9, 9]]),
            examples=[(Grid([[1, 2]]), Grid([[9, 9]]))],
        )
        engine.solve(task)
        diag = engine.get_diagnostics("t1")
        assert diag is not None

    def test_rule_confidence_bounds(self):
        rh = RuleHypothesizer()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[2]]))],
        )
        rules = rh.hypothesize(task)
        for rule in rules:
            assert 0.0 <= rule.confidence <= 1.0

    def test_grid_single_cell(self):
        grid = Grid([[5]])
        assert grid.width == 1
        assert grid.height == 1
        assert grid.get(0, 0) == 5

    def test_task_status_transitions(self):
        engine = Engine(max_iterations=3)
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[9]]),
            examples=[(Grid([[1]]), Grid([[9]]))],
        )
        assert task.status == Status.PENDING
        engine.solve(task)
        assert task.status in (Status.COMPLETED, Status.FAILED)

    def test_multiple_solutions_generated(self):
        sg = SolutionGenerator()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        strategy = Strategy(id="s3", name="brute_force", description="test")
        solutions = sg.generate(task, strategy, [])
        assert len(solutions) >= 3

    def test_engine_with_one_iteration(self):
        engine = Engine(max_iterations=1)
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[9]]),
            examples=[(Grid([[1]]), Grid([[9]]))],
        )
        result = engine.solve(task)
        assert result["iterations"] == 1

    def test_grid_equals_different_sizes(self):
        g1 = Grid([[1, 2]])
        g2 = Grid([[1, 2], [3, 4]])
        assert g1.equals(g2) is False

    def test_solution_with_metadata(self):
        sol = Solution(id="sol1", grid=Grid([[1]]), metadata={"source": "test"})
        assert sol.metadata["source"] == "test"

    def test_engine_get_nonexistent_task(self):
        engine = Engine()
        assert engine.get_task("nonexistent") is None

    def test_task_solution_initially_none(self):
        task = Task(id="t1", input_grid=Grid([[1]]))
        assert task.solution is None

    def test_rule_evidence_list(self):
        rule = Rule(id="r1", name="test", description="test", evidence=["e1", "e2"])
        assert len(rule.evidence) == 2

    def test_strategy_applicable_when(self):
        strategy = Strategy(id="s1", name="test", description="test", applicable_when="complex")
        assert strategy.applicable_when == "complex"

    def test_verify_exact_match_different_content(self):
        sv = SolutionVerifier()
        sol = Solution(id="sol1", grid=Grid([[1, 2]]))
        task = Task(id="t1", input_grid=Grid([[0]]), target_grid=Grid([[3, 4]]))
        result = sv.verify(sol, task)
        assert result["exact_match"] is False
