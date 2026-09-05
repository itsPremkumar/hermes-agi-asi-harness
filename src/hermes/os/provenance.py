"""
HERMES — PROVENANCE + REPRODUCIBILITY (lineage per artifact)
=============================================================
Every artifact gets provenance.json sidecar:
who/model/agent/tools/sources/version/env/seed/config/inputs-hash.
verify() re-hashes inputs + artifact to prove integrity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.provenance")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


class ProvenanceRecorder:
    def __init__(self, workspace_root: str = ".", harness_version: str = "2.0.0"):
        self.workspace_root = workspace_root
        self.harness_version = harness_version

    def record(
        self,
        artifact_path: str,
        who: str = "system:master",
        model: str = "",
        agent: str = "primary_worker",
        tools: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        seed: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        inputs_text: str = "",
    ) -> Dict[str, Any]:
        art = Path(artifact_path)
        try:
            content = art.read_bytes() if art.exists() else b""
        except Exception:
            content = b""
        prov = {
            "artifact": str(artifact_path),
            "artifact_sha256": hashlib.sha256(content).hexdigest() if content else "",
            "inputs_sha256": _sha(inputs_text),
            "who": who,
            "model": model,
            "agent": agent,
            "tools": list(tools or []),
            "sources": list(sources or []),
            "harness_version": self.harness_version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "seed": seed if seed is not None else int(time.time()) % 100000,
            "config": config or {},
            "ts": time.time(),
        }
        try:
            sidecar = (
                art.parent / (art.name + ".provenance.json")
                if art.suffix
                else Path(str(art) + ".provenance.json")
            )
            sidecar.write_text(json.dumps(prov, indent=2), encoding="utf-8")
            prov["sidecar"] = str(sidecar)
        except Exception as e:
            logger.debug("provenance sidecar failed: %s", e)
        return prov

    def verify(self, artifact_path: str) -> Dict[str, Any]:
        art = Path(artifact_path)
        cands = [art.parent / (art.name + ".provenance.json"), Path(str(art) + ".provenance.json")]
        sidecar = next((c for c in cands if c.exists()), None)
        if sidecar is None:
            return {"verified": False, "reason": "no provenance sidecar"}
        try:
            prov = json.loads(sidecar.read_text(encoding="utf-8"))
            content = art.read_bytes() if art.exists() else b""
            actual = hashlib.sha256(content).hexdigest() if content else ""
            ok = actual == prov.get("artifact_sha256")
            return {
                "verified": ok,
                "artifact_sha256": actual,
                "expected": prov.get("artifact_sha256"),
                "provenance": prov,
            }
        except Exception as e:
            return {"verified": False, "reason": str(e)}
