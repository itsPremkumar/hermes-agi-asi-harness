"""LangSmith Integration — Advanced tracing and evaluation for Hermes ASI."""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional LangSmith SDK
try:
    from langsmith import Client as LangSmithClientSDK
    from langsmith.run_trees import RunTree
    _LANGSMITH_SDK_AVAILABLE = True
except ImportError:
    _LANGSMITH_SDK_AVAILABLE = False
    LangSmithClientSDK = None  # type: ignore
    RunTree = None  # type: ignore


@dataclass
class LangSmithTraceConfig:
    """Configuration for LangSmith tracing."""
    enabled: bool = False
    api_key: Optional[str] = None
    project_name: str = "hermes-asi-master"
    endpoint: str = "https://api.smith.langchain.com"
    scrub_secrets: bool = True
    local_fallback: bool = True
    sample_rate: float = 1.0  # 1.0 = trace everything

    @classmethod
    def from_env(cls) -> LangSmithTraceConfig:
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() in ("true", "1", "yes")
        enabled = bool(api_key or tracing_v2)
        project = os.getenv("LANGCHAIN_PROJECT") or "hermes-asi-master"
        endpoint = os.getenv("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com"
        return cls(
            enabled=enabled,
            api_key=api_key,
            project_name=project,
            endpoint=endpoint,
            scrub_secrets=True,
            local_fallback=True,
        )


@dataclass
class TraceSpan:
    """A single trace span for LangSmith."""
    name: str
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    error: Optional[str] = None

    def end(self, outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.end_time = time.time()
        self.status = "failed" if error else "completed"
        if outputs:
            self.outputs = outputs
        if error:
            self.error = error

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "error": self.error,
        }


class SecretScrubber:
    """Redacts secrets from trace data."""

    PATTERNS = [
        (re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_OPENAI_KEY]"),
        (re.compile(r"(ghp_[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"(ls__[a-zA-Z0-9]{20,})", re.IGNORECASE), "[REDACTED_LANGSMITH_KEY]"),
        (re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
        (re.compile(r"(password\s*[:=]\s*['\"][^'\"]+['\"])", re.IGNORECASE), "password='[REDACTED_PASSWORD]'"),
    ]

    @classmethod
    def scrub(cls, data: Any) -> Any:
        if isinstance(data, str):
            result = data
            for pattern, replacement in cls.PATTERNS:
                result = pattern.sub(replacement, result)
            return result
        elif isinstance(data, dict):
            return {k: cls.scrub(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.scrub(item) for item in data]
        return data


class LangSmithTracer:
    """
    Advanced LangSmith tracer with span lifecycle management.
    Supports both cloud-connected and offline air-gap modes.
    """

    def __init__(self, config: Optional[LangSmithTraceConfig] = None):
        self.config = config or LangSmithTraceConfig.from_env()
        self._client: Optional[Any] = None
        self._active_spans: Dict[str, Any] = {}
        self._completed_spans: List[Dict[str, Any]] = []
        self._scrubber = SecretScrubber()

        if self.config.enabled and _LANGSMITH_SDK_AVAILABLE and self.config.api_key:
            try:
                self._client = LangSmithClientSDK(
                    api_key=self.config.api_key,
                    api_url=self.config.endpoint,
                )
                logger.info(f"[LangSmith] Connected to project '{self.config.project_name}'")
            except Exception as e:
                logger.warning(f"[LangSmith] Client init failed: {e}. Using local fallback.")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def start_span(
        self,
        name: str,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ) -> TraceSpan:
        """Start a new trace span."""
        scrubbed_inputs = self._scrubber.scrub(inputs or {})
        scrubbed_meta = self._scrubber.scrub(metadata or {})

        if self._client and _LANGSMITH_SDK_AVAILABLE and RunTree is not None:
            try:
                run = RunTree(
                    name=name,
                    run_type="chain",
                    inputs=scrubbed_inputs,
                    project_name=self.config.project_name,
                    extra=scrubbed_meta,
                )
                self._active_spans[run.id] = run
                span = TraceSpan(name=name, span_id=str(run.id), parent_id=parent_id)
                return span
            except Exception as e:
                logger.warning(f"[LangSmith] Failed creating RunTree: {e}")

        # Local fallback
        span = TraceSpan(
            name=name,
            parent_id=parent_id,
            inputs=scrubbed_inputs,
            metadata=scrubbed_meta,
        )
        self._active_spans[span.span_id] = span
        return span

    def end_span(
        self,
        span_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """End a trace span and record it."""
        span = self._active_spans.pop(span_id, None)
        if not span:
            return None

        scrubbed_outputs = self._scrubber.scrub(outputs or {})

        if isinstance(span, TraceSpan):
            span.end(outputs=scrubbed_outputs, error=error)
            span_dict = span.to_dict()
            self._completed_spans.append(span_dict)
            return span_dict

        # RunTree
        try:
            span.end(outputs=scrubbed_outputs, error=error)
            if self.config.api_key:
                span.post()
            result = {
                "span_id": str(getattr(span, "id", "")),
                "name": getattr(span, "name", ""),
                "status": "failed" if error else "completed",
                "outputs": scrubbed_outputs,
            }
            self._completed_spans.append(result)
            return result
        except Exception as e:
            logger.warning(f"[LangSmith] Failed posting span: {e}")
            return {"span_id": span_id, "status": "failed", "error": str(e)}

    def record_evaluation(
        self,
        run_id: str,
        key: str,
        score: float,
        comment: str = "",
    ) -> bool:
        """Record evaluation feedback for a run."""
        if self._client is not None:
            try:
                self._client.create_feedback(
                    run_id=run_id,
                    key=key,
                    score=score,
                    comment=self._scrubber.scrub(comment),
                )
                return True
            except Exception as e:
                logger.warning(f"[LangSmith] Failed recording evaluation: {e}")
        logger.debug(f"[LangSmith Local] Evaluation: run={run_id} key={key} score={score}")
        return True

    def get_completed_traces(self) -> List[Dict[str, Any]]:
        return list(self._completed_spans)

    def clear(self):
        self._active_spans.clear()
        self._completed_spans.clear()
