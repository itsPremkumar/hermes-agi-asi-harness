"""
Curriculum Engine Plugin — Adaptive Learning Task Selection

Implements: difficulty progression, skill coverage, prior knowledge,
spaced repetition, mastery tracking. Selects next learning task based
on current skill levels.
"""

import time
import random
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import defaultdict


@dataclass
class LearningTask:
    task_id: str
    name: str
    description: str
    domain: str
    difficulty: float  # 0-1
    prerequisites: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    estimated_minutes: int = 30


@dataclass
class SkillMastery:
    skill: str
    mastery: float = 0.0  # 0-1
    attempts: int = 0
    successes: int = 0
    last_attempt: float = 0.0
    forgetting_factor: float = 0.95  # How fast mastery decays


class CurriculumEngine:
    """Adaptive learning curriculum engine."""

    def __init__(self):
        self._tasks: Dict[str, LearningTask] = {}
        self._mastery: Dict[str, SkillMastery] = {}

    def add_task(self, task: LearningTask):
        self._tasks[task.task_id] = task

    def update_mastery(self, skill: str, success: bool, quality: float = 1.0):
        """Update skill mastery after a task attempt."""
        if skill not in self._mastery:
            self._mastery[skill] = SkillMastery(skill=skill)

        m = self._mastery[skill]
        m.attempts += 1
        if success:
            m.successes += 1
        m.last_attempt = time.time()

        # Bayesian update
        if success:
            m.mastery = min(1.0, m.mastery * 0.7 + quality * 0.3)
        else:
            m.mastery = max(0.0, m.mastery * 0.5)

    def select_next_task(self, available_time_minutes: int = 30) -> Optional[LearningTask]:
        """Select next learning task based on curriculum principles."""
        candidates = []

        for task in self._tasks.values():
            # Filter: estimated time fits
            if task.estimated_minutes > available_time_minutes:
                continue

            # Filter: prerequisites met
            if not self._prerequisites_met(task):
                continue

            # Score based on:
            # 1. Mastery level (slightly challenging - not mastered, not too hard)
            avg_mastery = self._avg_mastery_for_task(task)
            difficulty_match = 1.0 - abs(task.difficulty - (1.0 - avg_mastery))

            # 2. Skill coverage (unmastered skills preferred)
            unmastered_bonus = sum(1 for s in task.skills
                                  if self._mastery.get(s, SkillMastery(s)).mastery < 0.7)

            # 3. Recency (tasks not done recently)
            recency_bonus = self._recency_bonus(task)

            score = difficulty_match * 0.4 + unmastered_bonus * 0.3 + recency_bonus * 0.3
            candidates.append((score, task))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][1]

    def _prerequisites_met(self, task: LearningTask) -> bool:
        for prereq in task.prerequisites:
            mastery = self._mastery.get(prereq, SkillMastery(skill=prereq))
            if mastery.mastery < 0.6:
                return False
        return True

    def _avg_mastery_for_task(self, task: LearningTask) -> float:
        if not task.skills:
            return 0.0
        return sum(self._mastery.get(s, SkillMastery(skill=s)).mastery
                  for s in task.skills) / len(task.skills)

    def _recency_bonus(self, task: LearningTask) -> float:
        # Get most recent attempt for any of the task's skills
        most_recent = 0
        for skill in task.skills:
            mastery = self._mastery.get(skill)
            if mastery and mastery.last_attempt > most_recent:
                most_recent = mastery.last_attempt
        if most_recent == 0:
            return 1.0
        hours_ago = (time.time() - most_recent) / 3600
        # Spaced repetition: prefer tasks that haven't been done in a while
        return min(1.0, hours_ago / 24)

    def get_learning_path(self, target_skill: str) -> List[LearningTask]:
        """Generate a learning path to master a target skill."""
        path = []
        visited = set()
        queue = [target_skill]

        # BFS through prerequisites
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find tasks that teach this skill
            for task in self._tasks.values():
                if current in task.skills and task.task_id not in [t.task_id for t in path]:
                    path.append(task)
                    queue.extend(task.prerequisites)

        # Sort by difficulty (ascending - fundamentals first)
        path.sort(key=lambda t: t.difficulty)
        return path

    def get_curriculum_stats(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "tracked_skills": len(self._mastery),
            "mastered_skills": sum(1 for m in self._mastery.values() if m.mastery >= 0.8),
            "in_progress": sum(1 for m in self._mastery.values() if 0.3 <= m.mastery < 0.8),
            "beginner_skills": sum(1 for m in self._mastery.values() if m.mastery < 0.3),
            "avg_mastery": sum(m.mastery for m in self._mastery.values()) / max(1, len(self._mastery)),
        }


class CurriculumEnginePlugin:
    def __init__(self):
        self.engine = CurriculumEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_curriculum_stats(),
        }


async def create(kernel=None):
    plugin = CurriculumEnginePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
