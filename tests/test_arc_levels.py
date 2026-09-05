"""Tests for ARC-AGI-3 Level Tracker."""
from benchmarks.arc_game.level_tracker import Difficulty, LevelStatus, LevelTracker


class TestLevelTracker:
    def test_create(self):
        tracker = LevelTracker()
        assert tracker.get_total_count() == 0

    def test_register_level(self):
        tracker = LevelTracker()
        level = tracker.register_level("Level 1", "First level", Difficulty.EASY)
        assert level.name == "Level 1"
        assert level.difficulty == Difficulty.EASY
        assert tracker.get_total_count() == 1

    def test_get_level(self):
        tracker = LevelTracker()
        level = tracker.register_level("Level 1", "First", Difficulty.EASY)
        result = tracker.get_level(level.id)
        assert result is not None
        assert result.name == "Level 1"

    def test_list_levels(self):
        tracker = LevelTracker()
        tracker.register_level("A", "Desc", Difficulty.EASY)
        tracker.register_level("B", "Desc", Difficulty.HARD)
        assert len(tracker.list_levels()) == 2

    def test_unlock(self):
        tracker = LevelTracker()
        level = tracker.register_level("A", "Desc", Difficulty.EASY)
        assert tracker.unlock(level.id) is True
        assert tracker.get_level(level.id).status == LevelStatus.UNLOCKED

    def test_start_level(self):
        tracker = LevelTracker()
        level = tracker.register_level("A", "Desc", Difficulty.EASY)
        assert tracker.start_level(level.id) is True
        assert tracker.get_level(level.id).status == LevelStatus.IN_PROGRESS

    def test_record_attempt_success(self):
        tracker = LevelTracker()
        level = tracker.register_level("A", "Desc", Difficulty.EASY)
        attempt = tracker.record_attempt(level.id, True, 0.9, 100.0)
        assert attempt.success is True
        assert attempt.score == 0.9
        assert tracker.get_level(level.id).solved is True
        assert tracker.get_level(level.id).status == LevelStatus.COMPLETED

    def test_record_attempt_failure(self):
        tracker = LevelTracker()
        level = tracker.register_level("A", "Desc", Difficulty.EASY)
        attempt = tracker.record_attempt(level.id, False, 0.1, 100.0)
        assert attempt.success is False
        assert tracker.get_level(level.id).status == LevelStatus.FAILED

    def test_get_attempts(self):
        tracker = LevelTracker()
        level = tracker.register_level("A", "Desc", Difficulty.EASY)
        tracker.record_attempt(level.id, False, 0.1)
        tracker.record_attempt(level.id, True, 0.9)
        attempts = tracker.get_attempts(level.id)
        assert len(attempts) == 2

    def test_get_solved_count(self):
        tracker = LevelTracker()
        l1 = tracker.register_level("A", "Desc", Difficulty.EASY)
        l2 = tracker.register_level("B", "Desc", Difficulty.HARD)
        tracker.record_attempt(l1.id, True, 0.9)
        tracker.record_attempt(l2.id, False, 0.1)
        assert tracker.get_solved_count() == 1

    def test_get_progress(self):
        tracker = LevelTracker()
        l1 = tracker.register_level("A", "Desc", Difficulty.EASY)
        tracker.register_level("B", "Desc", Difficulty.HARD)
        tracker.record_attempt(l1.id, True, 0.9)
        assert tracker.get_progress() == 0.5

    def test_get_state(self):
        tracker = LevelTracker()
        tracker.register_level("A", "Desc", Difficulty.EASY)
        state = tracker.get_state()
        assert state["total"] == 1
        assert state["solved"] == 0

    def test_level_status_flow(self):
        tracker = LevelTracker()
        level = tracker.register_level("A", "Desc", Difficulty.EASY)
        assert level.status == LevelStatus.LOCKED
        tracker.unlock(level.id)
        assert tracker.get_level(level.id).status == LevelStatus.UNLOCKED
        tracker.start_level(level.id)
        assert tracker.get_level(level.id).status == LevelStatus.IN_PROGRESS
