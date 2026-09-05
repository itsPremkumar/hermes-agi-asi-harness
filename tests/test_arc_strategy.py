"""Tests for ARC-AGI-3 Strategy Optimizer."""
from benchmarks.arc_game.strategy import (
    StrategyOptimizer, StrategyType
)


class TestStrategyOptimizer:
    def test_create(self):
        opt = StrategyOptimizer()
        assert opt._strategies == {}

    def test_register_strategy(self):
        opt = StrategyOptimizer()
        s = opt.register_strategy(StrategyType.GREEDY, "Greedy", "Always pick best")
        assert s.name == "Greedy"
        assert s.strategy_type == StrategyType.GREEDY

    def test_get_strategy(self):
        opt = StrategyOptimizer()
        s = opt.register_strategy(StrategyType.GREEDY, "Greedy")
        result = opt.get_strategy(s.id)
        assert result is not None
        assert result.name == "Greedy"

    def test_list_strategies(self):
        opt = StrategyOptimizer()
        opt.register_strategy(StrategyType.GREEDY, "Greedy")
        opt.register_strategy(StrategyType.BACKTRACK, "Backtrack")
        assert len(opt.list_strategies()) == 2

    def test_evaluate(self):
        opt = StrategyOptimizer()
        s = opt.register_strategy(StrategyType.GREEDY, "Greedy")
        result = opt.evaluate(s.id, "t1", True, 0.8, 100.0)
        assert result.success is True
        assert result.score == 0.8

    def test_best_strategy(self):
        opt = StrategyOptimizer()
        s1 = opt.register_strategy(StrategyType.GREEDY, "Greedy")
        s2 = opt.register_strategy(StrategyType.BACKTRACK, "Backtrack")
        opt.evaluate(s1.id, "t1", True, 0.9, 100.0)
        opt.evaluate(s2.id, "t1", False, 0.1, 100.0)
        best = opt.get_best_strategy()
        assert best is not None
        assert best.success_rate > 0

    def test_get_state(self):
        opt = StrategyOptimizer()
        opt.register_strategy(StrategyType.GREEDY, "Greedy")
        state = opt.get_state()
        assert state["total_strategies"] == 1
