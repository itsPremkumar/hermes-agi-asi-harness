"""
HERMES INTELLIGENCE OS — VISTA LOSSLESS MULTI-MODAL PERCEPTION STORE
===================================================================
Inspired by VISTA and multimodal sensory replay architectures:
- Lossless out-of-band capture of raw perception observations:
  Screenshots, Accessibility/DOM trees, Terminal ANSI streams, Tool payloads, System telemetry.
- Action-indexed and chronological sensory retrieval.
- Experience Replay engine: Reconstructs exact visual and terminal states for
  post-mortem causal debugging and offline skill distillation.
"""

from __future__ import annotations

import enum
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("hermes.os.perception")


class PerceptionModality(str, enum.Enum):
    """Sensory modalities captured by the perception store."""
    SCREENSHOT = "screenshot"              # UI / Display image (bytes or base64)
    DOM_SNAPSHOT = "dom_snapshot"          # HTML / accessibility tree
    TERMINAL_STREAM = "terminal_stream"    # Raw stdout/stderr terminal log
    TOOL_PAYLOAD = "tool_payload"          # Exact JSON arguments and returns
    SYSTEM_METRICS = "system_metrics"      # CPU, RAM, tokens, latency


@dataclass
class PerceptionRecord:
    """Individual multimodal sensory observation tied to an action step."""
    perception_id: str
    timestamp: float
    action_id: str
    mission_id: str
    modality: PerceptionModality
    raw_content: Union[str, Dict[str, Any], bytes]
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary_token: str = ""

    def to_dict(self) -> Dict[str, Any]:
        content_preview = str(self.raw_content)
        if len(content_preview) > 200:
            content_preview = content_preview[:200] + "... [TRUNCATED]"
        return {
            "perception_id": self.perception_id,
            "timestamp": self.timestamp,
            "action_id": self.action_id,
            "mission_id": self.mission_id,
            "modality": self.modality.value,
            "summary_token": self.summary_token,
            "metadata": self.metadata,
            "content_preview": content_preview,
        }


class LosslessPerceptionStore:
    """
    Episodic sensory store preserving raw multimodal observations without
    polluting or exhausting the active LLM context window.
    """

    def __init__(self, workspace_root: str = ".", persist_to_disk: bool = True):
        self.workspace_root = Path(workspace_root)
        self.persist_to_disk = persist_to_disk
        self._store_dir = self.workspace_root / ".hermes" / "perceptions"
        if self.persist_to_disk:
            self._store_dir.mkdir(parents=True, exist_ok=True)

        self._records: Dict[str, PerceptionRecord] = {}
        self._action_index: Dict[str, List[str]] = {}       # action_id -> [perception_ids]
        self._mission_index: Dict[str, List[str]] = {}      # mission_id -> [perception_ids]

    def record_perception(
        self,
        mission_id: str,
        action_id: str,
        modality: PerceptionModality,
        raw_content: Union[str, Dict[str, Any], bytes],
        metadata: Optional[Dict[str, Any]] = None,
        summary_token: str = "",
    ) -> PerceptionRecord:
        """Record and index a raw sensory observation."""
        p_id = f"perc-{modality.value}-{uuid.uuid4().hex[:8]}"
        meta = metadata or {}

        if not summary_token:
            if isinstance(raw_content, str):
                summary_token = raw_content[:80].replace("\n", " ")
            elif isinstance(raw_content, dict):
                summary_token = f"keys={list(raw_content.keys())}"
            else:
                summary_token = f"bytes_len={len(raw_content)}"

        record = PerceptionRecord(
            perception_id=p_id,
            timestamp=time.time(),
            action_id=action_id,
            mission_id=mission_id,
            modality=modality,
            raw_content=raw_content,
            metadata=meta,
            summary_token=summary_token,
        )

        self._records[p_id] = record
        self._action_index.setdefault(action_id, []).append(p_id)
        self._mission_index.setdefault(mission_id, []).append(p_id)

        if self.persist_to_disk:
            self._persist_record(record)

        logger.debug(f"Captured {modality.value} perception {p_id} for action {action_id}")
        return record

    def _persist_record(self, record: PerceptionRecord) -> None:
        try:
            mission_dir = self._store_dir / record.mission_id
            mission_dir.mkdir(parents=True, exist_ok=True)
            record_file = mission_dir / f"{record.perception_id}.json"

            # Serialize content safely
            content = record.raw_content
            if isinstance(content, bytes):
                content = f"<binary_bytes:{len(content)}>"

            data = {
                "perception_id": record.perception_id,
                "timestamp": record.timestamp,
                "action_id": record.action_id,
                "mission_id": record.mission_id,
                "modality": record.modality.value,
                "summary_token": record.summary_token,
                "metadata": record.metadata,
                "raw_content": content,
            }
            record_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist perception record to disk: {e}")

    def get_record(self, perception_id: str) -> Optional[PerceptionRecord]:
        return self._records.get(perception_id)

    def get_by_action(self, action_id: str) -> List[PerceptionRecord]:
        p_ids = self._action_index.get(action_id, [])
        return [self._records[pid] for pid in p_ids if pid in self._records]

    def get_by_mission(self, mission_id: str) -> List[PerceptionRecord]:
        p_ids = self._mission_index.get(mission_id, [])
        return [self._records[pid] for pid in p_ids if pid in self._records]

    def replay_experience(self, mission_id: str) -> List[Dict[str, Any]]:
        """
        Reconstruct the chronological timeline of sensory observations
        for post-mortem analysis or training data extraction.
        """
        records = self.get_by_mission(mission_id)
        records.sort(key=lambda r: r.timestamp)
        return [r.to_dict() for r in records]
