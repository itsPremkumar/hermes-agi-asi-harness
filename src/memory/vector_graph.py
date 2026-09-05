"""
HERMES MEMORY — VECTOR + GRAPH BACKENDS (offline-first, pluggable)
===================================================================
Cold tier stays JSONL. This module adds:
- VectorStore: token-hash vectors + cosine; optional embedding backend
  via set_embedding_backend(fn) (same hook as ranking.py).
- KnowledgeGraph: typed edges (works_on, uses, depends_on, requires, ...).
Both persist under .hermes/memory/ and degrade gracefully offline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes.memory.vector_graph")

_EMBED_FN: Optional[Callable[[str], List[float]]] = None


def set_embedding_backend(fn: Optional[Callable[[str], List[float]]]) -> None:
    global _EMBED_FN
    _EMBED_FN = fn
    try:
        from .ranking import set_embedding_backend as _set2

        _set2(fn)
    except Exception:
        pass


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _hash_vec(text: str, dim: int = 128) -> List[float]:
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim
        vec[h] += 1.0
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class VectorStore:
    """Small persistent vector index for semantic retrieval."""

    def __init__(self, workspace_root: str = ".", dim: int = 128):
        self.workspace_root = workspace_root
        self.dim = dim
        self._file = Path(workspace_root) / ".hermes" / "memory" / "vector_index.jsonl"
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._docs: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _vec(self, text: str) -> List[float]:
        if _EMBED_FN is not None:
            try:
                v = _EMBED_FN(text)
                if v and len(v) == self.dim:
                    return v
            except Exception:
                pass
        return _hash_vec(text, self.dim)

    def _load(self) -> None:
        try:
            if self._file.exists():
                for line in self._file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        d = json.loads(line)
                        self._docs[d["doc_id"]] = d
        except Exception as e:
            logger.debug("vector load failed: %s", e)

    def _save(self) -> None:
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                for d in self._docs.values():
                    f.write(
                        json.dumps(
                            {
                                "doc_id": d["doc_id"],
                                "text": d["text"][:2000],
                                "tags": d.get("tags", []),
                            }
                        )
                        + "\n"
                    )
        except Exception:
            pass

    def add(self, doc_id: str, text: str, tags: Optional[List[str]] = None) -> None:
        self._docs[doc_id] = {
            "doc_id": doc_id,
            "text": text,
            "tags": list(tags or []),
            "_vec": self._vec(text),
        }
        self._save()

    def search(self, query: str, limit: int = 8) -> List[Tuple[str, float]]:
        qv = self._vec(query)
        scored = []
        for doc_id, d in self._docs.items():
            v = d.get("_vec") or self._vec(d["text"])
            s = _cosine(qv, v)
            if s > 0:
                scored.append((doc_id, round(s, 4)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


class KnowledgeGraph:
    """Typed relationship graph: Person→works_on→Project, Goal→requires→Skill, ..."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._file = Path(workspace_root) / ".hermes" / "memory" / "knowledge_graph.json"
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self._file.exists():
                data = json.loads(self._file.read_text(encoding="utf-8"))
                self._nodes = data.get("nodes", {})
                self._edges = data.get("edges", [])
        except Exception as e:
            logger.debug("kg load failed: %s", e)

    def _save(self) -> None:
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(
                json.dumps({"nodes": self._nodes, "edges": self._edges}, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def add_node(
        self, node_id: str, ntype: str, label: str = "", props: Optional[Dict[str, Any]] = None
    ) -> None:
        self._nodes[node_id] = {
            "id": node_id,
            "type": ntype,
            "label": label or node_id,
            "props": props or {},
        }
        self._save()

    def add_edge(
        self, src: str, rel: str, dst: str, props: Optional[Dict[str, Any]] = None
    ) -> None:
        if src not in self._nodes:
            self.add_node(src, "entity")
        if dst not in self._nodes:
            self.add_node(dst, "entity")
        self._edges.append({"src": src, "rel": rel, "dst": dst, "props": props or {}})
        self._save()

    def query(
        self,
        node_id: Optional[str] = None,
        rel: Optional[str] = None,
        ntype: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        out = []
        for e in self._edges:
            if node_id and e["src"] != node_id and e["dst"] != node_id:
                continue
            if rel and e["rel"] != rel:
                continue
            if (
                ntype
                and self._nodes.get(e["src"], {}).get("type") != ntype
                and self._nodes.get(e["dst"], {}).get("type") != ntype
            ):
                continue
            out.append(e)
            if len(out) >= limit:
                break
        return out

    def neighbors(self, node_id: str, limit: int = 20) -> List[str]:
        out = []
        for e in self._edges:
            if e["src"] == node_id:
                out.append(f"{e['rel']}→{e['dst']}")
            elif e["dst"] == node_id:
                out.append(f"{e['src']}→{e['rel']}")
            if len(out) >= limit:
                break
        return out

    def stats(self) -> Dict[str, Any]:
        return {"nodes": len(self._nodes), "edges": len(self._edges)}
