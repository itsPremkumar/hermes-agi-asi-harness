"""
HERMES MEMORY — SEMANTIC RANKING (AGX rank_lessons pattern)
===========================================================
Pluggable relevance ranking injected before every planning wave.
Default: token-overlap scoring (offline, zero-dep). Optional embedding
backend via set_embedding_backend(fn(text) -> list[float]) for cosine.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

_EMBED_FN: Optional[Callable[[str], List[float]]] = None


def set_embedding_backend(fn: Optional[Callable[[str], List[float]]]) -> None:
    global _EMBED_FN
    _EMBED_FN = fn


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _overlap_score(query: str, doc: str) -> float:
    q, d = set(_tokens(query)), set(_tokens(doc))
    if not q or not d:
        return 0.0
    inter = len(q & d)
    return inter / math.sqrt(len(q) * len(d))


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def rank_lessons(items: List[Any], query: str, limit: int = 8,
                 text_fn: Callable[[Any], str] | None = None) -> List[Tuple[Any, float]]:
    """Rank arbitrary lesson objects by relevance to query. Returns (item, score)."""
    tf = text_fn or (lambda x: str(getattr(x, "fact", getattr(x, "description", str(x)))))
    scored: List[Tuple[Any, float]] = []
    q_emb = None
    if _EMBED_FN is not None:
        try:
            q_emb = _EMBED_FN(query)
        except Exception:
            q_emb = None
    for it in items:
        doc = tf(it)
        score = _overlap_score(query, doc)
        if q_emb is not None and _EMBED_FN is not None:
            try:
                score = 0.5 * score + 0.5 * _cosine(q_emb, _EMBED_FN(doc))
            except Exception:
                pass
        # Recency/confidence boost when available
        conf = float(getattr(it, "confidence", 0.0) or 0.0)
        if conf:
            score += min(0.1, conf * 0.05)
        if score > 0:
            scored.append((it, round(score, 4)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def memory_str(ranked: List[Tuple[Any, float]], max_chars: int = 2000) -> str:
    """Render ranked lessons as prompt bullets (AGX memory_str pattern)."""
    lines: List[str] = []
    total = 0
    for item, score in ranked:
        fact = str(getattr(item, "fact", getattr(item, "description", str(item))))[:300]
        line = f"- [{score:.2f}] {fact}"
        total += len(line)
        if total > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)
