"""Episodic reflection store for the Reflexion agent.

A :class:`MemoryStore` accumulates (task, attempt, score, feedback) tuples as
``Reflection`` objects inside an in-memory buffer.  The buffer is the
"episodic memory" that gets injected back into the agent prompt on retry so
the agent can reason about its own past failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Sequence


@dataclass
class Reflection:
    """A single reflection entry.

    Attributes:
        task_id: identifier of the task this reflection belongs to.
        attempt: the agent's output text for the attempt.
        score: normalized score in [0, 1] assigned by the evaluator.
        feedback: verbal feedback string produced by the evaluator.
        reflection: the agent's own written reflection on the feedback.
    """

    task_id: str
    attempt: str
    score: float
    feedback: str
    reflection: str
    order: int = 0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "attempt": self.attempt,
            "score": self.score,
            "feedback": self.feedback,
            "reflection": self.reflection,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Reflection":
        return cls(
            task_id=data["task_id"],
            attempt=data["attempt"],
            score=float(data["score"]),
            feedback=data["feedback"],
            reflection=data["reflection"],
            order=int(data.get("order", 0)),
        )


@dataclass
class MemoryStore:
    """In-memory, serializable episodic memory buffer.

    The buffer is per-task.  Reflections are stored in insertion order and
    are always associated with the task they pertain to.
    """

    _buffer: dict[str, List[Reflection]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # core operations
    # ------------------------------------------------------------------
    def add(self, reflection: Reflection) -> None:
        """Append *reflection* to the buffer for its task."""
        bucket = self._buffer.setdefault(reflection.task_id, [])
        reflection.order = len(bucket)
        bucket.append(reflection)

    def get(self, task_id: str) -> List[Reflection]:
        """Return all reflections for *task_id* (empty list if none)."""
        return list(self._buffer.get(task_id, []))

    def clear(self, task_id: Optional[str] = None) -> None:
        """Clear a single task's buffer or the entire store."""
        if task_id is None:
            self._buffer.clear()
        else:
            self._buffer.pop(task_id, None)

    def __len__(self) -> int:
        return sum(len(v) for v in self._buffer.values())

    def __contains__(self, task_id: str) -> bool:
        return task_id in self._buffer

    def __iter__(self) -> Iterator[Reflection]:
        for bucket in self._buffer.values():
            yield from bucket

    # ------------------------------------------------------------------
    # serialization
    # ------------------------------------------------------------------
    def to_list(self) -> List[dict]:
        return [r.to_dict() for r in self]

    def save(self) -> List[dict]:
        """Serialize the buffer to a list of dicts (JSON-friendly)."""
        return self.to_list()

    @classmethod
    def load(cls, data: Optional[Sequence[dict]] = None) -> "MemoryStore":
        """Reconstruct a :class:`MemoryStore` from serialized dicts."""
        store = cls()
        if data:
            for raw in data:
                store.add(Reflection.from_dict(raw))
        return store

    # ------------------------------------------------------------------
    # retrieval helpers
    # ------------------------------------------------------------------
    def format_history(self, task_id: str, limit: Optional[int] = None) -> str:
        """Render the episodic history for *task_id* as a prompt-friendly string."""
        reflections = self.get(task_id)
        if not reflections:
            return ""
        if limit is not None:
            reflections = reflections[-limit:]
        lines: List[str] = []
        for r in reflections:
            lines.append(f"--- Prior attempt (score {r.score:.2f}) ---")
            lines.append(f"Attempt: {r.attempt.strip()}")
            lines.append(f"Feedback: {r.feedback.strip()}")
            lines.append(f"Reflection: {r.reflection.strip()}")
        return "\n".join(lines)
