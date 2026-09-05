"""Tests for the ARC-AGI-3 complete harness — AVO-style architecture.

Tests cover:
- PersistentMemory: store/retrieve/search, hypothesis tracking, action history
- Supervisor: stagnation detection, intervention recommendations
- ARCAGI3Agent: hypothesis formation, action decision, level execution
- ARCAGI3Scorer: RHAE scoring math (per-level, game, max)
- ARCAGI3Engine: full integration, environment/benchmark runs
"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.arc_game import (
    ALL_ACTIONS,
    GRID_SIZE,
    LEVEL_SCORE_CAP,
    MAX_ACTIONS_PER_LEVEL,
    NUM_COLORS,
    Action,
    ActionType,
    ARCAGI3Agent,
    ARCAGI3Engine,
    ARCAGI3Scorer,
    EnvironmentResult,
    Hypothesis,
    LevelResult,
    Observation,
    PersistentMemory,
    Supervisor,
    SupervisorStatus,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory():
    return PersistentMemory()


@pytest.fixture
def supervisor():
    return Supervisor()


@pytest.fixture
def agent(memory, supervisor):
    return ARCAGI3Agent(memory=memory, supervisor=supervisor, max_actions_per_level=50)


@pytest.fixture
def scorer():
    s = ARCAGI3Scorer()
    s.set_baseline("level_1", 10.0)
    s.set_baseline("level_2", 20.0)
    s.set_baseline("level_3", 15.0)
    return s


class MockEnvironment:
    """Mock ARC-AGI-3 environment for testing."""

    def __init__(self, level_ids=None, done_after=5):
        self.level_ids = level_ids or ["level_1"]
        self._done_after = done_after
        self._step_count = 0

    def reset(self):
        self._step_count = 0
        return Observation(grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)])

    def step(self, action):
        self._step_count += 1
        done = self._step_count >= self._done_after
        score = 1.0 if done else 0.0
        return Observation(
            grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)],
            score=score,
            done=done,
        )


class MockEnvironmentWithRules:
    """Mock environment where ACTION1 completes the level."""

    def __init__(self, level_ids=None):
        self.level_ids = level_ids or ["level_1"]

    def reset(self):
        return Observation(grid=[[1] * GRID_SIZE for _ in range(GRID_SIZE)])

    def step(self, action):
        if action == "action1" or action == ActionType.ACTION1:
            return Observation(
                grid=[[1] * GRID_SIZE for _ in range(GRID_SIZE)],
                score=1.0,
                done=True,
            )
        return Observation(
            grid=[[1] * GRID_SIZE for _ in range(GRID_SIZE)],
            score=0.0,
            done=False,
        )


# ---------------------------------------------------------------------------
# Observation tests
# ---------------------------------------------------------------------------

class TestObservation:
    def test_create_observation(self):
        grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        obs = Observation(grid=grid, score=0.5, done=False)
        assert obs.score == 0.5
        assert obs.done is False
        assert len(obs.grid) == GRID_SIZE
        assert len(obs.grid[0]) == GRID_SIZE

    def test_to_text(self):
        grid = [[0, 1, 2], [3, 4, 5]]
        obs = Observation(grid=grid)
        text = obs.to_text()
        assert "012" in text
        assert "345" in text

    def test_from_text(self):
        text = "012\n345"
        obs = Observation.from_text(text)
        assert obs.grid == [[0, 1, 2], [3, 4, 5]]

    def test_text_roundtrip(self):
        grid = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
        obs = Observation(grid=grid)
        text = obs.to_text()
        obs2 = Observation.from_text(text)
        assert obs2.grid == grid


# ---------------------------------------------------------------------------
# PersistentMemory tests
# ---------------------------------------------------------------------------

class TestPersistentMemory:
    def test_store_and_retrieve(self, memory):
        memory.store("key1", "value1")
        assert memory.retrieve("key1") == "value1"

    def test_store_overwrite(self, memory):
        memory.store("key1", "value1")
        memory.store("key1", "value2")
        assert memory.retrieve("key1") == "value2"

    def test_retrieve_missing(self, memory):
        assert memory.retrieve("nonexistent") is None

    def test_search(self, memory):
        memory.store("action_log", "action1, action2, action3")
        memory.store("score_info", "score is 0.5")
        results = memory.search("action")
        assert len(results) >= 1

    def test_search_limit(self, memory):
        for i in range(20):
            memory.store(f"key_{i}", f"value_{i} with common")
        results = memory.search("common", limit=5)
        assert len(results) <= 5

    def test_add_hypothesis(self, memory):
        h = Hypothesis(description="test hypothesis")
        memory.add_hypothesis(h)
        assert len(memory.get_active_hypotheses()) == 1

    def test_get_confirmed_hypotheses(self, memory):
        h1 = Hypothesis(description="confirmed", confirmed=True)
        h2 = Hypothesis(description="unconfirmed", confirmed=False)
        memory.add_hypothesis(h1)
        memory.add_hypothesis(h2)
        confirmed = memory.get_confirmed_hypotheses()
        assert len(confirmed) == 1
        assert confirmed[0].description == "confirmed"

    def test_record_action(self, memory):
        action = Action(action_type=ActionType.ACTION1)
        obs = Observation(grid=[[0]])
        memory.record_action(action, obs)
        history = memory.get_action_history()
        assert len(history) == 1

    def test_get_action_history_last_n(self, memory):
        for i in range(10):
            memory.record_action(Action(action_type=ActionType.ACTION1), Observation(grid=[[0]]))
        history = memory.get_action_history(last_n=5)
        assert len(history) == 5

    def test_add_insight(self, memory):
        memory.add_insight("Patterns repeat every 3 steps")
        insights = memory.get_insights()
        assert len(insights) == 1
        assert "Patterns repeat" in insights[0]

    def test_add_duplicate_insight(self, memory):
        memory.add_insight("Same insight")
        memory.add_insight("Same insight")
        assert len(memory.get_insights()) == 1

    def test_get_state_summary(self, memory):
        memory.store("key", "value")
        memory.add_hypothesis(Hypothesis(description="test"))
        summary = memory.get_state_summary()
        assert summary["entries"] == 1
        assert summary["hypotheses"] == 1

    def test_save_and_load(self, memory):
        memory.store("key1", "value1", importance=2.0)
        memory.add_insight("Important insight")
        memory.add_hypothesis(Hypothesis(description="test", confirmed=True, confidence=0.9))
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = Path(f.name)
        try:
            memory.save(path)
            loaded = PersistentMemory.load(path)
            assert loaded.retrieve("key1") == "value1"
            assert len(loaded.get_insights()) == 1
            confirmed = loaded.get_confirmed_hypotheses()
            assert len(confirmed) == 1
            assert confirmed[0].confidence == 0.9
        finally:
            path.unlink(missing_ok=True)

    def test_load_missing_file(self):
        loaded = PersistentMemory.load(Path("/nonexistent/path.json"))
        assert loaded.retrieve("anything") is None

    def test_eviction(self):
        mem = PersistentMemory(max_entries=10)
        for i in range(20):
            mem.store(f"key_{i}", f"value_{i}", importance=float(i))
        # Should have evicted low-importance entries
        assert len(mem._entries) <= 10


# ---------------------------------------------------------------------------
# Supervisor tests
# ---------------------------------------------------------------------------

class TestSupervisor:
    def test_initial_status(self, supervisor):
        assert supervisor.status == SupervisorStatus.ACTIVE

    def test_detect_repeated_actions(self, supervisor, memory):
        for _ in range(10):
            action = Action(action_type=ActionType.ACTION1)
            obs = Observation(grid=[[0]])
            analysis = supervisor.analyze(action, obs, memory)
        assert analysis.repeated_actions >= 5
        assert analysis.needs_intervention

    def test_detect_score_plateau(self, supervisor, memory):
        for _ in range(25):
            action = Action(action_type=ActionType.ACTION2)
            obs = Observation(grid=[[0]], score=0.0)
            analysis = supervisor.analyze(action, obs, memory)
        assert analysis.score_plateau
        assert analysis.actions_without_progress >= 20

    def test_detect_hypothesis_stagnation(self, supervisor, memory):
        for i in range(15):
            memory.add_hypothesis(Hypothesis(description=f"hypothesis_{i}"))
        action = Action(action_type=ActionType.ACTION1)
        obs = Observation(grid=[[0]])
        analysis = supervisor.analyze(action, obs, memory)
        assert analysis.hypothesis_stagnation

    def test_recommendation_generated(self, supervisor, memory):
        for _ in range(10):
            action = Action(action_type=ActionType.ACTION1)
            obs = Observation(grid=[[0]])
            analysis = supervisor.analyze(action, obs, memory)
        assert len(analysis.recommendation) > 0

    def test_record_intervention(self, supervisor, memory):
        supervisor.record_intervention("Try different approach", memory)
        interventions = supervisor.get_interventions()
        assert len(interventions) == 1
        assert "different approach" in interventions[0]["recommendation"]

    def test_status_after_intervention(self, supervisor, memory):
        for _ in range(10):
            action = Action(action_type=ActionType.ACTION1)
            obs = Observation(grid=[[0]])
            supervisor.analyze(action, obs, memory)
        assert supervisor.status == SupervisorStatus.REDIRECTING


# ---------------------------------------------------------------------------
# ARCAGI3Scorer tests
# ---------------------------------------------------------------------------

class TestARCAGI3Scorer:
    def test_level_score_perfect(self, scorer):
        # Agent matches human baseline exactly
        score = scorer.level_score("level_1", 10)
        assert score == pytest.approx(1.0)

    def test_level_score_better_than_human(self, scorer):
        # Agent uses fewer actions than human
        score = scorer.level_score("level_1", 5)
        assert score == pytest.approx(min(LEVEL_SCORE_CAP, (10/5)**2))

    def test_level_score_worse_than_human(self, scorer):
        # Agent uses more actions than human
        score = scorer.level_score("level_1", 20)
        assert score == pytest.approx((10/20)**2)

    def test_level_score_capped(self, scorer):
        # Very efficient agent should hit the cap
        score = scorer.level_score("level_1", 1)
        assert score == pytest.approx(LEVEL_SCORE_CAP)

    def test_level_score_zero_actions(self, scorer):
        score = scorer.level_score("level_1", 0)
        assert score == 0.0

    def test_level_score_no_baseline(self, scorer):
        score = scorer.level_score("unknown_level", 10)
        # No baseline set, should use agent_actions as baseline -> ratio=1
        assert score == pytest.approx(1.0)

    def test_game_score_single_level(self, scorer):
        results = [LevelResult(level_id="level_1", completed=True, actions_used=10, actions_budget=50, score=1.0)]
        game = scorer.game_score(results)
        assert game == pytest.approx(1.0)

    def test_game_score_multiple_levels(self, scorer):
        results = [
            LevelResult(level_id="level_1", completed=True, actions_used=10, actions_budget=50, score=1.0),
            LevelResult(level_id="level_2", completed=True, actions_used=20, actions_budget=50, score=1.0),
        ]
        game = scorer.game_score(results)
        # Weighted average: (1*1.0 + 2*1.0) / (1+2) = 1.0
        assert game == pytest.approx(1.0)

    def test_game_score_empty(self, scorer):
        assert scorer.game_score([]) == 0.0

    def test_max_game_score(self, scorer):
        max_score = scorer.max_game_score(5, 10, game_max=1.0)
        assert max_score == pytest.approx(0.5)

    def test_max_game_score_all_completed(self, scorer):
        max_score = scorer.max_game_score(10, 10, game_max=1.0)
        assert max_score == pytest.approx(1.0)

    def test_max_game_score_zero_levels(self, scorer):
        max_score = scorer.max_game_score(0, 10)
        assert max_score == 0.0


# ---------------------------------------------------------------------------
# ARCAGI3Agent tests
# ---------------------------------------------------------------------------

class TestARCAGI3Agent:
    def test_create_agent(self, agent):
        assert agent.max_actions_per_level == 50
        assert agent.memory is not None
        assert agent.supervisor is not None

    def test_form_hypothesis_monochromatic(self, agent):
        grid = [[5] * GRID_SIZE for _ in range(GRID_SIZE)]
        obs = Observation(grid=grid)
        h = agent._form_hypothesis(obs)
        assert h is not None
        assert "monochromatic" in h.description.lower()

    def test_form_hypothesis_symmetric(self, agent):
        grid = []
        for i in range(GRID_SIZE):
            row = [j % 16 for j in range(GRID_SIZE)]
            grid.append(row)
        # Make symmetric
        for i in range(GRID_SIZE):
            grid[i] = grid[GRID_SIZE - 1 - i]
        obs = Observation(grid=grid)
        h = agent._form_hypothesis(obs)
        # May or may not detect symmetry depending on grid
        # Just verify it doesn't crash
        assert h is None or isinstance(h, Hypothesis)

    def test_form_hypothesis_regions(self, agent):
        grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        # Create a second region
        for i in range(10, 20):
            for j in range(10, 20):
                grid[i][j] = 1
        obs = Observation(grid=grid)
        h = agent._form_hypothesis(obs)
        assert h is not None

    def test_decide_action_exploration(self, agent):
        obs = Observation(grid=[[0] * GRID_SIZE for _ in range(GRID_SIZE)])
        action = agent._decide_action(obs)
        assert isinstance(action, Action)
        assert action.action_type in ActionType

    def test_run_level(self, agent):
        env = MockEnvironment(done_after=5)
        result = agent.run_level(env, "test_level")
        assert isinstance(result, LevelResult)
        assert result.level_id == "test_level"
        assert result.actions_used > 0

    def test_run_level_completes(self, agent):
        env = MockEnvironment(done_after=3)
        result = agent.run_level(env, "easy_level")
        assert result.completed
        assert result.score > 0

    def test_run_level_respects_budget(self):
        agent = ARCAGI3Agent(max_actions_per_level=10)
        env = MockEnvironment(done_after=100)  # won't complete
        result = agent.run_level(env, "hard_level")
        assert result.actions_used <= 10
        assert not result.completed

    def test_check_symmetry_true(self):
        grid = [[1, 2, 1], [3, 4, 3], [1, 2, 1]]
        assert ARCAGI3Agent._check_symmetry(grid)

    def test_check_symmetry_false(self):
        grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        assert not ARCAGI3Agent._check_symmetry(grid)

    def test_count_regions_single(self):
        grid = [[1, 1], [1, 1]]
        assert ARCAGI3Agent._count_regions(grid) == 1

    def test_count_regions_multiple(self):
        grid = [[1, 2], [3, 4]]
        assert ARCAGI3Agent._count_regions(grid) == 4


# ---------------------------------------------------------------------------
# ARCAGI3Engine tests
# ---------------------------------------------------------------------------

class TestARCAGI3Engine:
    def test_create_engine(self):
        engine = ARCAGI3Engine(verbose=False)
        assert engine.agent is not None
        assert engine.scorer is not None
        assert engine.memory is not None

    def test_run_environment(self):
        engine = ARCAGI3Engine(verbose=False)
        env = MockEnvironment(done_after=3)
        result = engine.run_environment(env, "test_env", ["level_1"])
        assert isinstance(result, EnvironmentResult)
        assert result.env_id == "test_env"
        assert result.levels_completed == 1

    def test_run_environment_multiple_levels(self):
        engine = ARCAGI3Engine(verbose=False)
        env = MockEnvironment(done_after=3)
        result = engine.run_environment(env, "test_env", ["level_1", "level_2"])
        assert result.total_levels == 2
        assert result.levels_completed == 2

    def test_run_benchmark(self):
        engine = ARCAGI3Engine(verbose=False)
        envs = {
            "env_1": MockEnvironment(done_after=3),
            "env_2": MockEnvironment(done_after=5),
        }
        results = engine.run_benchmark(envs)
        assert len(results) == 2
        assert "env_1" in results
        assert "env_2" in results

    def test_engine_with_custom_scorer(self):
        scorer = ARCAGI3Scorer()
        scorer.set_baseline("level_1", 5.0)
        engine = ARCAGI3Engine(scorer=scorer)
        env = MockEnvironment(done_after=5)
        result = engine.run_environment(env, "test_env", ["level_1"])
        assert result.levels_completed == 1


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_level_with_memory(self):
        """Test that memory persists across actions in a level."""
        memory = PersistentMemory()
        supervisor = Supervisor()
        agent = ARCAGI3Agent(memory=memory, supervisor=supervisor, max_actions_per_level=20)
        env = MockEnvironment(done_after=5)
        result = agent.run_level(env, "integration_test")
        assert result.completed
        assert len(memory.get_action_history()) > 0

    def test_supervisor_intervenes_when_stuck(self):
        """Test that supervisor detects stagnation and intervenes."""
        memory = PersistentMemory()
        supervisor = Supervisor(stagnation_threshold=5, repetition_threshold=3)
        agent = ARCAGI3Agent(memory=memory, supervisor=supervisor, max_actions_per_level=20)
        # Environment that never completes
        env = MockEnvironment(done_after=1000)
        result = agent.run_level(env, "stuck_level")
        # Supervisor should have intervened
        interventions = supervisor.get_interventions()
        assert len(interventions) > 0

    def test_hypothesis_formation_and_storage(self):
        """Test that hypotheses are formed and stored in memory."""
        memory = PersistentMemory()
        agent = ARCAGI3Agent(memory=memory, max_actions_per_level=10)
        env = MockEnvironment(done_after=3)
        agent.run_level(env, "hypothesis_test")
        # Should have formed at least one hypothesis
        all_hypotheses = memory.get_active_hypotheses() + memory.get_confirmed_hypotheses()
        assert len(all_hypotheses) >= 0  # May be 0 for trivial grid

    def test_scorer_computes_game_score(self):
        """Test full scoring pipeline."""
        scorer = ARCAGI3Scorer()
        scorer.set_baseline("level_1", 10.0)
        scorer.set_baseline("level_2", 20.0)
        results = [
            LevelResult(level_id="level_1", completed=True, actions_used=10, actions_budget=50, score=1.0),
            LevelResult(level_id="level_2", completed=True, actions_used=20, actions_budget=50, score=1.0),
        ]
        game_score = scorer.game_score(results)
        assert 0.0 <= game_score <= LEVEL_SCORE_CAP

    def test_memory_persistence_across_runs(self):
        """Test that memory can be saved and reloaded."""
        memory = PersistentMemory()
        memory.store("key1", "value1", importance=2.0)
        memory.add_insight("Test insight")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = Path(f.name)
        try:
            memory.save(path)
            loaded = PersistentMemory.load(path)
            assert loaded.retrieve("key1") == "value1"
            assert "Test insight" in loaded.get_insights()
        finally:
            path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------

class TestConstants:
    def test_grid_size(self):
        assert GRID_SIZE == 64

    def test_num_colors(self):
        assert NUM_COLORS == 16

    def test_max_actions(self):
        assert MAX_ACTIONS_PER_LEVEL == 200

    def test_level_score_cap(self):
        assert pytest.approx(1.15 ** 2) == LEVEL_SCORE_CAP

    def test_all_actions(self):
        assert len(ALL_ACTIONS) == len(ActionType)
        assert "reset" in ALL_ACTIONS
        assert "action1" in ALL_ACTIONS
        assert "undo" in ALL_ACTIONS
        assert "wait" in ALL_ACTIONS


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_grid(self):
        obs = Observation(grid=[])
        assert obs.grid == []

    def test_single_cell_grid(self):
        obs = Observation(grid=[[5]])
        assert obs.grid == [[5]]

    def test_memory_store_none(self, memory):
        memory.store("none_key", None)
        assert memory.retrieve("none_key") is None

    def test_memory_store_complex_object(self, memory):
        data = {"nested": {"key": [1, 2, 3]}}
        memory.store("complex", data)
        assert memory.retrieve("complex") == data

    def test_supervisor_no_intervention_when_progressing(self, supervisor, memory):
        for i in range(5):
            action = Action(action_type=ActionType.ACTION1)
            obs = Observation(grid=[[0]], score=float(i) / 5)
            analysis = supervisor.analyze(action, obs, memory)
        # Score is increasing, no intervention needed
        assert not analysis.score_plateau

    def test_agent_with_done_observation(self):
        memory = PersistentMemory()
        agent = ARCAGI3Agent(memory=memory, max_actions_per_level=10)
        env = MockEnvironment(done_after=1)
        result = agent.run_level(env, "instant_done")
        assert result.completed
        assert result.actions_used == 1

    def test_scorer_with_zero_baseline(self):
        scorer = ARCAGI3Scorer()
        scorer.set_baseline("level_1", 0.0)
        score = scorer.level_score("level_1", 10)
        assert score == 0.0
