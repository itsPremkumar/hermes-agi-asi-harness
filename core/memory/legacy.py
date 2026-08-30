
"""
Long-term Memory — lessons learned + research findings persisted per run
AND across runs (cross-run RAG-lite retrieval, no external dependencies).

Extracted & enhanced from agx-harness-main:
- memory.py: MemoryStore, record_lesson, recall, retrieve, semantic_search, rank_lessons
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "on", "it",
    "and", "or", "for", "with", "by", "from", "as", "at", "this", "that", "be",
    "been", "being", "have", "has", "had", "we", "you", "they", "but", "not",
    "no", "so", "if", "then", "out", "up", "down", "can", "will", "do", "does",
    "than", "here", "because", "already", "caused", "using", "moving", "slower",
}


def load_memory(path: str) -> dict[str, Any]:
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"lessons": [], "research": []}
    return {"lessons": [], "research": []}


def save_memory(path: str, mem: dict[str, Any]) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2)


def record_lesson(mem: dict[str, Any], kind: str, text: str) -> None:
    mem.setdefault("lessons", []).append(
        {"kind": kind, "text": text, "ts": int(time.time())})


def recall(mem: dict[str, Any], kind: str | None = None, n: int = 10) -> list[Any]:
    items = mem.get("lessons", [])
    if kind:
        items = [x for x in items if x.get("kind") == kind]
    return items[-n:]


def _kw(text: str) -> set:
    return set(re.findall(r"[a-z0-9_]{4,}", (text or "").lower()))


def retrieve(mem: dict[str, Any], query: str, n: int = 5) -> list[Any]:
    """Keyword-relevance recall (RAG-lite) across persisted lessons."""
    q = _kw(query)
    if not q:
        return recall(mem, n=n)
    scored = []
    for item in mem.get("lessons", []):
        overlap = len(q & _kw(item.get("text", "")))
        if overlap:
            scored.append((overlap, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:n]]


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", (text or "").lower())
            if len(t) >= 3 and t not in _STOP]


def _vectorize(text: str) -> dict[str, float]:
    vec: dict[str, float] = {}
    for t in _tokenize(text):
        vec[t] = vec.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {k: v / norm for k, v in vec.items()}


_EMBED_FN: Callable[[str], dict[str, float]] = _vectorize


def set_embedding_backend(fn: Callable[[str], dict[str, float]]) -> None:
    global _EMBED_FN
    _EMBED_FN = fn


def _embed(text: str) -> dict[str, float]:
    return _EMBED_FN(text)


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    return sum(a[k] * b[k] for k in (set(a) & set(b)))


def rank_lessons(lessons: list[dict[str, Any]], query: str) -> list[Any]:
    """Order lessons by cosine similarity, keeping every lesson."""
    q = _embed(query)
    if not q:
        return list(lessons)
    scored = [(_cosine(q, _embed(it.get("text", ""))), i, it)
              for i, it in enumerate(lessons)]
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    return [it for _, _, it in scored]


def semantic_search(lessons: list[dict[str, Any]], query: str,
                    n: int = 5, min_sim: float = 0.0) -> list[Any]:
    """Rank lessons by cosine similarity (concept recall, not just keyword)."""
    q = _embed(query)
    if not q:
        return lessons[-n:]
    scored = []
    for item in lessons:
        s = _cosine(q, _embed(item.get("text", "")))
        if s > min_sim:
            scored.append((s, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:n]]


class MemoryStore:
    """File-backed persistent memory (cross-run)."""

    def __init__(self, path: str | None):
        self.path = path
        self.data = load_memory(path)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._vecs = {
            i: _embed(item.get("text", ""))
            for i, item in enumerate(self.data.get("lessons", []))
        }

    def record(self, kind: str, text: str) -> None:
        record_lesson(self.data, kind, text)
        idx = len(self.data["lessons"]) - 1
        self._vecs[idx] = _embed(text)
        save_memory(self.path, self.data)

    def recall(self, kind: str | None = None, n: int = 10) -> list[Any]:
        return recall(self.data, kind=kind, n=n)

    def semantic_search(self, query: str, n: int = 5, min_sim: float = 0.0) -> list[Any]:
        return semantic_search(self.data.get("lessons", []), query, n=n, min_sim=min_sim)

    def retrieve(self, query: str, n: int = 5, semantic: bool = False) -> list[Any]:
        if semantic:
            return self.semantic_search(query, n=n)
        return retrieve(self.data, query, n=n)

    def merge(self, other: dict[str, Any]) -> None:
        for item in other.get("lessons", []):
            if item not in self.data["lessons"]:
                self.data["lessons"].append(item)
        self._rebuild_index()
        save_memory(self.path, self.data)


class _Recorder:
    """Unified sink: writes to in-memory dict and/or a file store."""

    def __init__(self, mem_dict: dict[str, Any], store: MemoryStore | None = None):
        self.mem = mem_dict
        self.store = store

    def record(self, kind: str, text: str) -> None:
        record_lesson(self.mem, kind, text)
        if self.store:
            self.store.record(kind, text)


def make_recorder(state: dict[str, Any], memory_file: str | None) -> _Recorder:
    cfg_mem = state.setdefault("shared_state", {}).setdefault("memory", {})
    store = MemoryStore(memory_file) if memory_file else None
    return _Recorder(cfg_mem, store)

import logging
