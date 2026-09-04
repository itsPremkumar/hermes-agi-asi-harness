"""
HERMES — MINIMAL STATUS API (localhost operations)
===================================================
Read-mostly FastAPI surface for remote monitoring plus guarded mission
control. Auth: if HERMES_API_KEY is set, every call needs header
X-API-Key; otherwise the server binds 127.0.0.1 only (documented local mode).
Run: python -m hermes_agi api serve [--port 8471]
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
    _HAS_FASTAPI = True
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore
    _HAS_FASTAPI = False


def _require_key(x_api_key: Optional[str] = None) -> None:
    if not _HAS_FASTAPI:
        return
    expected = os.getenv("HERMES_API_KEY", "")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="bad api key")


def create_app(kernel: Any = None):
    if not _HAS_FASTAPI:  # pragma: no cover
        raise RuntimeError("fastapi not installed")
    from fastapi import Depends  # noqa: F401
    app = FastAPI(title="Hermes Harness API", version="2.0.0")
    state: Dict[str, Any] = {"kernel": kernel}

    def get_kernel():
        k = state["kernel"]
        if k is None:
            from .kernel import HermesIntelligenceOS
            k = state["kernel"] = HermesIntelligenceOS()
        return k

    @app.get("/health")
    def health(x_api_key: Optional[str] = Header(default=None)):
        _require_key(x_api_key)
        k = get_kernel()
        return {"kernel": "healthy", "hermes": k.hermes.health() if k.hermes else None,
                "daemon": k.daemon.stats()}

    @app.get("/status")
    def status(x_api_key: Optional[str] = Header(default=None)):
        _require_key(x_api_key)
        k = get_kernel()
        return {"daemon": k.daemon.stats(),
                "scheduler": k.scheduler.stats() if k.scheduler else None,
                "watchdog": k.watchdog.incidents() if getattr(k, "watchdog", None) else [],
                "kill": k.safety_kernel.kill_engaged()}

    @app.get("/ledger")
    def ledger(x_api_key: Optional[str] = Header(default=None)):
        _require_key(x_api_key)
        from memory.ledger import EconomicLedger
        k = get_kernel()
        return EconomicLedger(workspace_root=k.workspace_root).totals()

    @app.get("/radar")
    def radar(x_api_key: Optional[str] = Header(default=None)):
        _require_key(x_api_key)
        return {"items": get_kernel().self_research.radar.list()}

    @app.post("/enqueue")
    def enqueue(body: Dict[str, Any], x_api_key: Optional[str] = Header(default=None)):
        _require_key(x_api_key)
        k = get_kernel()
        mid = k.enqueue(str(body.get("request", "")), priority=str(body.get("priority", "normal")))
        return {"mission_id": mid, "pending": k.daemon.pending_count()}

    @app.post("/stop")
    def stop(x_api_key: Optional[str] = Header(default=None)):
        _require_key(x_api_key)
        get_kernel().daemon.request_stop()
        return {"stopped": True}

    return app
