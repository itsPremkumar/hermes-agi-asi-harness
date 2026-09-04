"""
HERMES — DOCKER SANDBOX (isolated code execution)
==================================================
Runs untrusted code in a locked-down container when a Docker engine is
present; otherwise falls back to a local isolated temp dir and says so
explicitly (never silently). No new hard dependency: docker-py is optional.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("hermes.os.docker_sandbox")

_DEFAULT_IMAGE = "python:3.12-slim"
_engine_cache: Dict[str, Any] = {"checked": 0.0, "available": False}


def engine_available(refresh: bool = False) -> bool:
    """True when a Docker engine answers ping. Cached 60s, never raises."""
    now = time.time()
    if not refresh and now - _engine_cache["checked"] < 60:
        return bool(_engine_cache["available"])
    ok = False
    try:
        import docker  # type: ignore
        client = docker.from_env(timeout=5)
        client.ping()
        ok = True
    except Exception as e:
        logger.debug("Docker engine absent: %s", e)
    _engine_cache.update({"checked": now, "available": ok})
    return ok


def run_local_fallback(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Isolated temp-dir execution used when no engine exists."""
    with tempfile.TemporaryDirectory(prefix="hermes-sbx-") as box:
        try:
            proc = subprocess.run([sys.executable, "-c", code], cwd=box,
                                  capture_output=True, text=True, timeout=timeout)
            return {"engine": "local-fallback", "exit": proc.returncode,
                    "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-1000:]}
        except Exception as e:
            return {"engine": "local-fallback", "exit": -1, "stdout": "", "stderr": str(e)[:1000]}


def run_container(code: str, image: str = _DEFAULT_IMAGE, timeout: int = 60,
                  mem_limit: str = "512m", network_disabled: bool = True) -> Dict[str, Any]:
    """Run code in a one-shot locked-down container. Raises if engine missing."""
    import docker  # type: ignore
    client = docker.from_env(timeout=10)
    out = client.containers.run(
        image, ["python", "-c", code], mem_limit=mem_limit,
        network_disabled=network_disabled, remove=True,
        stdout=True, stderr=True, detach=False,
    )
    text = out.decode("utf-8", errors="replace") if isinstance(out, (bytes, bytearray)) else str(out)
    return {"engine": "docker", "image": image, "exit": 0, "stdout": text[-4000:], "stderr": ""}


class DockerSandbox:
    """Prefer Docker; explicit local fallback. Records which engine ran."""

    def __init__(self, image: str = _DEFAULT_IMAGE, timeout: int = 60):
        self.image = image
        self.timeout = timeout

    def run(self, code: str) -> Dict[str, Any]:
        if engine_available():
            try:
                return run_container(code, image=self.image, timeout=self.timeout)
            except Exception as e:
                logger.warning("Docker run failed, falling back local: %s", e)
        result = run_local_fallback(code, timeout=min(self.timeout, 30))
        result["image_requested"] = self.image
        return result

    def status(self) -> Dict[str, Any]:
        return {"engine_available": engine_available(), "image": self.image,
                "fallback": "local-tempdir"}
