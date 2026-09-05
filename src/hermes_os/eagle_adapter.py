"""
HERMES — EAGLE ADAPTER (governed Eagle Eye research substrate)
===============================================================
Puts agent_eye capacity behind harness governance:

- Parallel backend fan-out with per-backend timeouts (the raw chain is
  serial and stalls ~60s; here slow backends are skipped, not waited on).
- Every claim returns provenance (backend, url, timestamp); callers mark
  web content tainted via SafetyKernel.
- Cost accounting (query counts + elapsed) for the economic ledger.
- Zero hard failure: missing backends / offline / timeouts degrade to
  fewer sources, never exceptions (unless strict=True).

Env:
  EAGLE_ENABLED      1/0 (default 1; 0 forces legacy heuristics)
  EAGLE_TIMEOUT      per-backend seconds (default 8)
  EAGLE_MAX_BACKENDS fan-out cap (default 6)
  EAGLE_BACKENDS     comma subset to enable (default all known-good)
"""

from __future__ import annotations

import concurrent.futures as _cf
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.os.eagle")


@dataclass
class EagleClaim:
    title: str
    url: str
    snippet: str
    backend: str
    confidence: float = 0.6
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet[:500],
            "backend": self.backend,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


def _env_flag(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _timeout() -> float:
    try:
        return max(2.0, float(os.getenv("EAGLE_TIMEOUT", "8")))
    except Exception:
        return 8.0


def _max_backends() -> int:
    try:
        return max(1, int(os.getenv("EAGLE_MAX_BACKENDS", "6")))
    except Exception:
        return 6


def _normalize(raw: Any, backend: str, limit: int) -> List[EagleClaim]:
    """Defensively normalize wrapper outputs (dict | list | None) to claims."""
    items: List[Any] = []
    try:
        if raw is None:
            return []
        if isinstance(raw, dict):
            if not raw.get("success", True):
                return []
            data = raw.get("data", raw)
            if isinstance(data, dict):
                for key in ("web", "results", "items", "papers", "entries"):
                    if isinstance(data.get(key), list):
                        items.extend(data[key])
                        break
                else:
                    items = [data] if data.get("url") or data.get("title") else []
            elif isinstance(data, list):
                items = data
        elif isinstance(raw, list):
            items = raw
        elif isinstance(raw, str):
            return [EagleClaim(title=raw[:80], url="", snippet=raw, backend=backend)]
    except Exception:
        return []
    claims: List[EagleClaim] = []
    for it in items[:limit]:
        try:
            if isinstance(it, dict):
                url = str(it.get("url") or it.get("link") or "")
                claims.append(
                    EagleClaim(
                        title=str(it.get("title") or it.get("name") or url)[:160],
                        url=url,
                        snippet=str(it.get("snippet") or it.get("body") or it.get("summary") or "")[
                            :800
                        ],
                        backend=backend,
                        confidence=float(it.get("confidence", 0.6)),
                    )
                )
            else:
                claims.append(
                    EagleClaim(title=str(it)[:80], url="", snippet=str(it), backend=backend)
                )
        except Exception:
            continue
    return claims


def _backend_table() -> Dict[str, Callable[..., Any]]:
    """Lazily resolve backend callables; missing ones are simply absent."""
    table: Dict[str, Callable[..., Any]] = {}
    try:
        from agent_eye import core as _core  # type: ignore

        for attr, name in (
            ("_wikipedia_search_wrapper", "wikipedia"),
            ("_github_search", "github"),
            ("_hackernews_search", "hackernews"),
            ("_stackoverflow_search_wrapper", "stackoverflow"),
            ("_mdn_search_wrapper", "mdn"),
            ("_devto_search_wrapper", "devto"),
            ("_lemmy_search_wrapper", "lemmy"),
            ("_ddgs_search", "ddgs"),
            ("_arxiv_search_wrapper", "arxiv"),
            ("_duckgo_news_wrapper", "news"),
        ):
            fn = getattr(_core, attr, None)
            if callable(fn):
                table[name] = fn
    except Exception as e:
        logger.debug("eagle backends unavailable: %s", e)
    wanted = os.getenv("EAGLE_BACKENDS", "")
    if wanted.strip():
        keep = {w.strip().lower() for w in wanted.split(",")}
        table = {k: v for k, v in table.items() if k in keep}
    return table


class EagleAdapter:
    """Governed entry point. All methods degrade; use strict=True to raise."""

    def __init__(self):
        self.queries = 0
        self.elapsed_total = 0.0
        self.backend_hits: Dict[str, int] = {}
        self.backend_fails: Dict[str, int] = {}

    @property
    def enabled(self) -> bool:
        return _env_flag("EAGLE_ENABLED", "1")

    def _fanout(
        self, query: str, limit: int, backends: Optional[List[str]] = None, strict: bool = False
    ) -> List[EagleClaim]:
        table = _backend_table()
        names = [b for b in (backends or list(table)) if b in table][: _max_backends()]
        if not names:
            if strict:
                raise RuntimeError("No Eagle backends available")
            return []
        per = max(1, limit // max(1, len(names)) + 1)
        claims: List[EagleClaim] = []
        timeout = _timeout()

        def _one(name: str) -> List[EagleClaim]:
            t0 = time.time()
            try:
                with _cf.ThreadPoolExecutor(max_workers=1) as pool:
                    raw = pool.submit(table[name], query, limit=per).result(timeout=timeout)
                out = _normalize(raw, name, per)
                self.backend_hits[name] = self.backend_hits.get(name, 0) + 1
                return out
            except Exception as e:
                self.backend_fails[name] = self.backend_fails.get(name, 0) + 1
                logger.debug("eagle backend %s failed: %s", name, e)
                if strict:
                    raise
                return []
            finally:
                self.elapsed_total += time.time() - t0

        with _cf.ThreadPoolExecutor(max_workers=len(names)) as pool:
            futs = {pool.submit(_one, n): n for n in names}
            # Priority order, not completion order
            done: Dict[str, List[EagleClaim]] = {}
            for fut in _cf.as_completed(futs, timeout=timeout + 5.0):
                try:
                    done[futs[fut]] = fut.result()
                except Exception:
                    done[futs[fut]] = []
            for n in names:
                claims.extend(done.get(n, []))
        self.queries += 1
        return claims[:limit]

    def web_search(self, query: str, limit: int = 8, strict: bool = False) -> List[EagleClaim]:
        if not self.enabled:
            return []
        return self._fanout(query, limit, strict=strict)

    def academic_search(self, query: str, limit: int = 6, strict: bool = False) -> List[EagleClaim]:
        if not self.enabled:
            return []
        return self._fanout(query, limit, backends=["arxiv", "wikipedia"], strict=strict)

    def fetch_extract(self, url: str, strict: bool = False) -> Optional[EagleClaim]:
        """Fetch + readability-extract one URL (bounded, tainted)."""
        if not self.enabled:
            return None
        try:
            import urllib.request

            from agent_eye.extractors import smart_extract  # type: ignore

            req = urllib.request.Request(url, headers={"User-Agent": "HermesResearch/2.0"})
            with urllib.request.urlopen(req, timeout=_timeout()) as r:
                raw = r.read(512 * 1024).decode("utf-8", errors="replace")
            text = smart_extract(raw) if callable(smart_extract) else raw
            self.queries += 1
            return EagleClaim(
                title=url[:120], url=url, snippet=str(text)[:1500], backend="fetch", confidence=0.55
            )
        except Exception as e:
            logger.debug("eagle fetch failed %s: %s", url, e)
            if strict:
                raise
            return None

    # -- harness integration -------------------------------------------
    def register_capabilities(self, registry: Any) -> List[str]:
        """Register eagle.* manifests; returns ids. No-op on failure."""
        try:
            from .capabilities import CapabilityKind, CapabilityManifest

            ids = []
            for cid, name, desc, best in (
                (
                    "eagle.web_search",
                    "Eagle Web Search",
                    "Parallel multi-backend web search with provenance",
                    ["market_analysis", "domain_recon"],
                ),
                (
                    "eagle.academic_search",
                    "Eagle Academic Search",
                    "arXiv/Wikipedia evidence with citations",
                    ["literature_review", "fact_check"],
                ),
                (
                    "eagle.fetch_extract",
                    "Eagle Fetch+Extract",
                    "Bounded URL fetch with readability extraction",
                    ["source_verification", "evidence_packet"],
                ),
            ):
                registry.register(
                    CapabilityManifest(
                        id=cid,
                        kind=CapabilityKind.SKILL,
                        name=name,
                        description=desc,
                        inputs=["query_or_url"],
                        outputs=["evidence_packet", "verified_claims"],
                        risk="low",
                        best_for=best,
                    )
                )
                ids.append(cid)
            return ids
        except Exception as e:
            logger.debug("eagle capability registration failed: %s", e)
            return []

    def as_tools(self, tool_env: Any) -> List[str]:
        """Register governed eagle.* tools on a ToolEnvironmentOS."""
        try:
            from .tool_env import ToolDescriptor

            adapter = self

            def _hunt(query: str, limit: int = 8) -> List[Dict[str, Any]]:
                out = adapter.web_search(query, limit=int(limit))
                for c in out:
                    try:
                        tool_env.safety_kernel.register_taint(c.url or c.title, ["unverified_web"])
                    except Exception:
                        pass
                return [c.to_dict() for c in out]

            def _acad(query: str, limit: int = 6) -> List[Dict[str, Any]]:
                out = adapter.academic_search(query, limit=int(limit))
                for c in out:
                    try:
                        tool_env.safety_kernel.register_taint(c.url or c.title, ["unverified_web"])
                    except Exception:
                        pass
                return [c.to_dict() for c in out]

            def _fetch(url: str) -> Dict[str, Any]:
                c = adapter.fetch_extract(url)
                if c is None:
                    return {"success": False, "error": "fetch failed or disabled"}
                try:
                    tool_env.safety_kernel.register_taint(c.url, ["unverified_web"])
                except Exception:
                    pass
                return {"success": True, **c.to_dict()}

            defs = [
                ("eagle_web_search", "Parallel governed web search with provenance", _hunt, 800),
                ("eagle_academic_search", "Academic evidence search with citations", _acad, 600),
                ("eagle_fetch", "Bounded fetch+extract of one URL (tainted)", _fetch, 500),
            ]
            names = []
            for tname, desc, handler, tokens in defs:
                tool_env.register(
                    ToolDescriptor(
                        name=tname,
                        description=desc,
                        handler=handler,
                        required_permission="read",
                        risk_level="low",
                        estimated_cost_tokens=tokens,
                        sandbox_required=False,
                    )
                )
                names.append(tname)
            return names
        except Exception as e:
            logger.debug("eagle tool registration failed: %s", e)
            return []

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "queries": self.queries,
            "elapsed_total": round(self.elapsed_total, 2),
            "hits": dict(self.backend_hits),
            "fails": dict(self.backend_fails),
        }

    def persist_stats(self, workspace_root: str = ".") -> str:
        """Write stats snapshot for dashboard/ledger consumers."""
        import json as _j
        from pathlib import Path as _P

        p = _P(workspace_root) / ".hermes" / "eagle_stats.json"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(_j.dumps({**self.stats(), "ts": time.time()}, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("eagle stats persist failed: %s", e)
        return str(p)

    def health(self) -> Dict[str, Any]:
        """Per-backend health from observed hit/fail counters + availability."""
        table = _backend_table()
        rows = {}
        for name in sorted(set(list(table) + list(self.backend_hits) + list(self.backend_fails))):
            hits = self.backend_hits.get(name, 0)
            fails = self.backend_fails.get(name, 0)
            total = hits + fails
            if name not in table:
                status = "missing"
            elif total == 0:
                status = "unknown"
            elif fails >= 5 and hits == 0:
                status = "broken"
            elif fails > hits:
                status = "degraded"
            else:
                status = "healthy"
            rows[name] = {
                "status": status,
                "hits": hits,
                "fails": fails,
                "available": name in table,
            }
        return {"backends": rows, "queries": self.queries}

    def mcp_specs(self) -> List[Dict[str, Any]]:
        """MCP tool specs for our hub (register via CapabilityRegistry.register_mcp_tools)."""
        return [
            {
                "name": "eagle_web_search",
                "description": "Parallel governed web search with provenance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 8},
                    },
                },
                "risk": "low",
                "side_effects": False,
            },
            {
                "name": "eagle_academic_search",
                "description": "Academic evidence search with citations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 6},
                    },
                },
                "risk": "low",
                "side_effects": False,
            },
            {
                "name": "eagle_fetch",
                "description": "Bounded fetch+extract of one URL (tainted)",
                "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}},
                "risk": "medium",
                "side_effects": False,
            },
        ]
