"""Artifact Registry — Artifact-centric engineering communication."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArtifactType(str, Enum):
    PATCH = "patch"
    COMMIT = "commit"
    BRANCH = "branch"
    ADR = "adr"
    TEST_REPORT = "test_report"
    BENCHMARK = "benchmark"
    SECURITY_REPORT = "security_report"
    BUILD_ARTIFACT = "build_artifact"
    DOCKER_IMAGE = "docker_image"
    MIGRATION = "migration"
    RELEASE_CANDIDATE = "release_candidate"

@dataclass
class Artifact:
    id: str
    artifact_type: ArtifactType
    name: str
    content: Any
    producer: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

class ArtifactRegistry:
    def __init__(self):
        self.artifacts: dict[str, Artifact] = {}
    
    def register(self, artifact_type: ArtifactType, name: str,
                 content: Any, producer: str, **kwargs) -> Artifact:
        artifact = Artifact(
            id=str(uuid.uuid4()), artifact_type=artifact_type,
            name=name, content=content, producer=producer,
            timestamp=time.time(), metadata=kwargs,
        )
        self.artifacts[artifact.id] = artifact
        return artifact
    
    def get_by_type(self, artifact_type: ArtifactType) -> list[Artifact]:
        return [a for a in self.artifacts.values() if a.artifact_type == artifact_type]
    
    def get_by_producer(self, producer: str) -> list[Artifact]:
        return [a for a in self.artifacts.values() if a.producer == producer]
    
    def get_state(self) -> dict[str, Any]:
        return {"total": len(self.artifacts), "types": list({a.artifact_type.value for a in self.artifacts.values()})}
