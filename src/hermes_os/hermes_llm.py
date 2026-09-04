"""
HERMES FIRST LLM CHAIN
======================
Default model resolution for the harness — Hermes models first, cloud only
as fallback, deterministic heuristics last:

  H1  Hermes managed local router  (hermes-agent local_runtime state file
      -> 127.0.0.1 OpenAI-compatible /v1, e.g. Qwen GGUF via llama.cpp)
  H2  Hermes-detected llama-server (hermes-agent detect.py fingerprint probe)
  L   Generic local servers        (Ollama 11434, LM Studio 1234)
  C   Cloud providers              (existing LLMClient: OpenRouter/OpenAI)
  D   Deterministic fallback       (return None -> compiler heuristics)

Probes use stdlib urllib with short timeouts and are cached (TTL), so a
missing Hermes server never slows boot or planning. Interface matches what
CognitiveCompiler._deliberate_llm expects: .chat(messages) / .generate(prompt).

Env overrides:
  HERMES_LLM_ORDER    comma list subset of H1,H2,L,C  (default all, in order)
  HERMES_LLM_TIMEOUT  chat timeout seconds (default 120)
  HERMES_LLM_PROBE_TTL seconds to cache tier probes (default 300)
  HERMES_LLM_MODEL    force model id on local tiers
  LLM_MODEL / OPENROUTER_MODEL honoured by the cloud tier (existing behavior)
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes.os.hermes_llm")

PROBE_TIMEOUT = 3.0
OLLAMA_PORTS = (11434,)
LMSTUDIO_PORTS = (1234,)
LLAMACPP_PORTS = (8080,)

# Last successful tier probe: (tier, base_url, api_key, model, timestamp)
_last_probe: Dict[str, Any] = {"tier": None, "ts": 0.0}


def _probe_ttl() -> float:
    try:
        return max(30.0, float(os.getenv("HERMES_LLM_PROBE_TTL", "300")))
    except Exception:
        return 300.0


def _order() -> List[str]:
    raw = os.getenv("HERMES_LLM_ORDER", "H1,H2,L,C")
    wanted = [t.strip().upper() for t in raw.split(",") if t.strip()]
    return [t for t in wanted if t in ("H1", "H2", "L", "C")] or ["H1", "H2", "L", "C"]


def _http_json(url: str, timeout: float, api_key: str = "",
               payload: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    try:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json", **(
                                         {"Authorization": f"Bearer {api_key}"} if api_key else {})})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def _first_model(base_url: str, api_key: str, timeout: float) -> Optional[str]:
    forced = os.getenv("HERMES_LLM_MODEL", "").strip()
    if forced:
        return forced
    status, body = _http_json(f"{base_url}/models", timeout, api_key)
    if status == 200 and isinstance(body, dict):
        data = body.get("data") or []
        if data and isinstance(data[0], dict) and data[0].get("id"):
            return str(data[0]["id"])
    return None


# ----------------------------------------------------------------------
# Tier probes (each returns (base_url, api_key, model) or None; never raises)
# ----------------------------------------------------------------------

def _probe_h1() -> Optional[Tuple[str, str, str]]:
    """Hermes managed router via hermes-agent's own endpoint resolution."""
    try:
        from hermes_cli.local_runtime import endpoint as _ep  # type: ignore
        managed = _ep.managed_root()
        if not managed:
            return None
        base_root, api_key = managed
        base_url = f"{base_root}/v1"
        model = _first_model(base_url, api_key, PROBE_TIMEOUT)
        if model:
            return base_url, api_key, model
        return None
    except Exception as e:
        logger.debug("H1 probe failed: %s", e)
        return None


def _probe_h2() -> Optional[Tuple[str, str, str]]:
    """Hermes-fingerprinted llama-server (hermes-agent detect.py)."""
    try:
        from hermes_cli.local_runtime import detect as _det  # type: ignore
        ports: List[int] = list(getattr(_det, "DEFAULT_PROBE_PORTS", LLAMACPP_PORTS)) or list(LLAMACPP_PORTS)
        for port in ports:
            try:
                found = _det.probe_port(int(port))
            except Exception:
                continue
            if not found or getattr(found, "auth_required", False):
                continue
            base_url = getattr(found, "base_url", f"http://127.0.0.1:{port}/v1")
            model = _first_model(base_url, "", PROBE_TIMEOUT)
            if model:
                return base_url, "", model
        return None
    except Exception as e:
        logger.debug("H2 probe failed: %s", e)
        return None


def _probe_local() -> Optional[Tuple[str, str, str]]:
    """Generic local servers: Ollama + LM Studio (OpenAI-compatible /v1).

    Ports probed concurrently — each closed localhost port can stall ~2s
    on Windows, so serial probing costs 4s+ with nothing running.
    """
    ports = (*OLLAMA_PORTS, *LMSTUDIO_PORTS)
    try:
        import concurrent.futures as _cf

        def _check(port: int) -> Optional[Tuple[str, str, str]]:
            base_url = f"http://127.0.0.1:{port}/v1"
            model = _first_model(base_url, "", PROBE_TIMEOUT)
            return (base_url, "", model) if model else None

        with _cf.ThreadPoolExecutor(max_workers=len(ports)) as pool:
            futs = {pool.submit(_check, p): p for p in ports}
            # Return in priority order, not completion order
            done: Dict[int, Any] = {}
            for fut in _cf.as_completed(futs, timeout=PROBE_TIMEOUT + 2.0):
                try:
                    done[futs[fut]] = fut.result()
                except Exception:
                    done[futs[fut]] = None
            for port in ports:
                if done.get(port):
                    return done[port]
    except Exception:
        for port in ports:
            base_url = f"http://127.0.0.1:{port}/v1"
            model = _first_model(base_url, "", PROBE_TIMEOUT)
            if model:
                return base_url, "", model
    return None


def _probe_cloud() -> Optional[Tuple[str, str, str]]:
    """Cloud tier availability = existing LLMClient has key (no network call)."""
    try:
        from hermes_agi.llm_planning import LLMClient  # type: ignore
        probe = LLMClient()
        if getattr(probe, "api_key", ""):
            return ("cloud", "", getattr(probe, "model", ""))
        return None
    except Exception as e:
        logger.debug("Cloud probe failed: %s", e)
        return None


_PROBERS = {"H1": _probe_h1, "H2": _probe_h2, "L": _probe_local, "C": _probe_cloud}


def resolve_tier(force_refresh: bool = False) -> Dict[str, Any]:
    """Return first available tier {tier, base_url, api_key, model} or {} (→ deterministic).

    Local tiers (H1/H2/L) probe concurrently: on Windows each localhost
    connection costs ~2s, so serial probing stalls planning by 6s+.
    Priority order is preserved (first hit in chain order wins).
    """
    global _last_probe
    now = time.time()
    if not force_refresh and _last_probe.get("tier") and (now - _last_probe.get("ts", 0)) < _probe_ttl():
        return dict(_last_probe)
    order = _order()
    results: Dict[str, Any] = {}
    local_tiers = [t for t in order if t in ("H1", "H2", "L")]
    try:
        import concurrent.futures as _cf

        def _safe_probe(tier: str) -> Any:
            try:
                return _PROBERS[tier]()
            except Exception:
                return None

        with _cf.ThreadPoolExecutor(max_workers=max(1, len(local_tiers))) as pool:
            futs = {pool.submit(_safe_probe, t): t for t in local_tiers}
            for fut in _cf.as_completed(futs, timeout=PROBE_TIMEOUT + 2.0):
                try:
                    results[futs[fut]] = fut.result()
                except Exception:
                    results[futs[fut]] = None
    except Exception as e:
        logger.debug("Concurrent probe failed, falling back serial: %s", e)
    for tier in order:
        if tier in results:
            hit = results[tier]
        else:
            try:
                hit = _PROBERS[tier]()
            except Exception:
                hit = None
        if hit:
            base_url, api_key, model = hit
            _last_probe = {"tier": tier, "base_url": base_url, "api_key": api_key,
                           "model": model, "ts": now}
            logger.info("Hermes-first LLM resolved tier %s model=%s", tier, model)
            return dict(_last_probe)
    _last_probe = {"tier": None, "ts": now}
    return dict(_last_probe)


def hermes_local_available() -> bool:
    """Cached, network-free check for portfolio routing (uses last probe only)."""
    return _last_probe.get("tier") in ("H1", "H2", "L") and \
        (time.time() - _last_probe.get("ts", 0)) < _probe_ttl()


# ----------------------------------------------------------------------
# Chain client (drop-in for CognitiveCompiler llm_client)
# ----------------------------------------------------------------------

def _chat_openai_compat(base_url: str, api_key: str, model: str,
                        messages: List[Dict[str, str]], timeout: float,
                        temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
    status, body = _http_json(f"{base_url}/chat/completions", timeout, api_key,
                              {"model": model, "messages": messages,
                               "temperature": temperature, "max_tokens": max_tokens})
    try:
        if status == 200 and isinstance(body, dict):
            return str(body["choices"][0]["message"]["content"])
    except Exception:
        pass
    logger.debug("chat compat failed tier model=%s status=%s", model, status)
    return None


@dataclass
class HermesFirstLLMClient:
    """Tries Hermes tiers first, then cloud, then returns None (= deterministic)."""
    timeout: float = field(default_factory=lambda: float(os.getenv("HERMES_LLM_TIMEOUT", "120")))
    active_tier: Optional[str] = None
    active_model: Optional[str] = None

    def _attempt(self, messages: List[Dict[str, str]],
                 temperature: float, max_tokens: int) -> Optional[str]:
        # Walk the chain top-down; re-resolve after each failure so a dead
        # tier falls through to the next one.
        tried: List[str] = []
        for _ in _order():
            try:
                cur = resolve_tier(force_refresh=bool(tried))
            except Exception:
                cur = {}
            tier = cur.get("tier")
            if not tier or tier in tried:
                break
            tried.append(tier)
            hit = cur
            if tier == "C":
                try:
                    from hermes_agi.llm_planning import LLMClient  # type: ignore
                    import asyncio as _aio
                    import concurrent.futures as _cf
                    client = LLMClient()

                    def _run_cloud() -> Optional[str]:
                        return _aio.run(client.chat(messages, temperature=temperature,
                                                    max_tokens=max_tokens))

                    with _cf.ThreadPoolExecutor(max_workers=1) as pool:
                        out = pool.submit(_run_cloud).result(timeout=self.timeout)
                    if out and "LLM unavailable" not in out:
                        self.active_tier, self.active_model = tier, client.model
                        return out
                except Exception as e:
                    logger.debug("Cloud tier chat failed: %s", e)
                continue
            out = _chat_openai_compat(hit["base_url"], hit.get("api_key", ""), hit["model"],
                                      messages, self.timeout, temperature, max_tokens)
            if out:
                self.active_tier, self.active_model = tier, hit["model"]
                global _last_probe
                _last_probe = dict(hit, ts=time.time())
                return out
            # Tier claimed availability but chat failed -> force re-resolve next loop
            resolve_tier(force_refresh=True)
        logger.debug("All LLM tiers exhausted (tried=%s); deterministic fallback", tried)
        return None

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7,
             max_tokens: int = 2048) -> Optional[str]:
        try:
            return self._attempt(messages, temperature, max_tokens)
        except Exception as e:
            logger.debug("Hermes-first chat error: %s", e)
            return None

    def generate(self, prompt: str) -> Optional[str]:
        out = self.chat([{"role": "user", "content": prompt}])
        return out if out is not None else None

    def status(self) -> Dict[str, Any]:
        cur = resolve_tier()
        return {"order": _order(), "active_tier": self.active_tier,
                "active_model": self.active_model, "resolved": cur,
                "probe_ttl_s": _probe_ttl(),
                "tiers": {t: ("up" if cur.get("tier") == t else "unknown")
                          for t in ("H1", "H2", "L", "C")}}
