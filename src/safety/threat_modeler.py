"""Threat Modeler — identify and model security threats for AI agent systems."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ThreatSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(Enum):
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DENIAL_OF_SERVICE = "denial_of_service"
    MODEL_MANIPULATION = "model_manipulation"
    CREDENTIAL_THEFT = "credential_theft"
    UNAUTHORIZED_ACCESS = "unauthorized_input"
    SIDE_CHANNEL = "side_channel"


@dataclass
class Threat:
    threat_id: str
    name: str
    category: ThreatCategory
    severity: ThreatSeverity
    description: str
    attack_vector: str
    impact: str
    likelihood: float
    mitigations: list[str] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def risk_score(self) -> float:
        severity_map = {
            ThreatSeverity.CRITICAL: 1.0,
            ThreatSeverity.HIGH: 0.8,
            ThreatSeverity.MEDIUM: 0.5,
            ThreatSeverity.LOW: 0.2,
            ThreatSeverity.INFO: 0.05,
        }
        return severity_map[self.severity] * self.likelihood


@dataclass
class ThreatModel:
    model_id: str
    target_system: str
    threats: list[Threat] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def total_risk(self) -> float:
        return sum(t.risk_score for t in self.threats)

    @property
    def critical_count(self) -> int:
        return sum(1 for t in self.threats if t.severity == ThreatSeverity.CRITICAL)

    def by_severity(self, severity: ThreatSeverity) -> list[Threat]:
        return [t for t in self.threats if t.severity == severity]

    def by_category(self, category: ThreatCategory) -> list[Threat]:
        return [t for t in self.threats if t.category == category]


class ThreatModeler:
    """Analyze AI agent systems for security threats."""

    PATTERNS = {
        ThreatCategory.PROMPT_INJECTION: [
            r"ignore.*previous.*instructions",
            r"you are now",
            r"system.*override",
            r"jailbreak",
            r"pretend.*you.*are",
        ],
        ThreatCategory.DATA_EXFILTRATION: [
            r"send.*to.*external",
            r"exfiltrate",
            r"upload.*credentials",
            r"POST.*http",
        ],
        ThreatCategory.PRIVILEGE_ESCALATION: [
            r"sudo",
            r"admin.*access",
            r"root.*privileges",
            r"escalate",
        ],
        ThreatCategory.DENIAL_OF_SERVICE: [
            r"infinite.*loop",
            r"resource.*exhaustion",
            r"flood",
            r"throttle",
        ],
        ThreatCategory.CREDENTIAL_THEFT: [
            r"API.*key",
            r"secret",
            r"password",
            r"token.*leak",
        ],
    }

    def __init__(self):
        self._models: dict[str, ThreatModel] = {}

    def create_model(self, target_system: str) -> str:
        model_id = hashlib.sha256(f"{target_system}{time.time()}".encode()).hexdigest()[:12]
        model = ThreatModel(model_id=model_id, target_system=target_system)
        self._models[model_id] = model
        return model_id

    def analyze_input(self, model_id: str, user_input: str) -> list[Threat]:
        """Analyze user input for threat patterns."""
        model = self._models.get(model_id)
        if not model:
            return []

        threats = []
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                import re
                if re.search(pattern, user_input, re.IGNORECASE):
                    threat = Threat(
                        threat_id=hashlib.sha256(f"{pattern}{time.time()}".encode()).hexdigest()[:8],
                        name=f"{category.value}_detected",
                        category=category,
                        severity=ThreatSeverity.HIGH,
                        description=f"Detected potential {category.value} pattern",
                        attack_vector=user_input[:100],
                        impact="Potential security breach",
                        likelihood=0.7,
                        mitigations=[
                            "Sanitize user input",
                            "Apply rate limiting",
                            "Log and monitor",
                        ],
                    )
                    threats.append(threat)
                    model.threats.append(threat)

        model.updated_at = time.time()
        return threats

    def analyze_code(self, model_id: str, code: str, language: str = "python") -> list[Threat]:
        """Analyze code for security vulnerabilities."""
        model = self._models.get(model_id)
        if not model:
            return []

        threats = []
        # Check for hardcoded secrets
        import re
        secret_patterns = [
            (r"sk-[a-zA-Z0-9]{32,}", "hardcoded_api_key", ThreatSeverity.CRITICAL),
            (r"ghp_[a-zA-Z0-9]{36}", "hardcoded_github_token", ThreatSeverity.CRITICAL),
            (r"password\s*=\s*['\"]", "hardcoded_password", ThreatSeverity.HIGH),
            (r"secret\s*=\s*['\"]", "hardcoded_secret", ThreatSeverity.HIGH),
        ]

        for pattern, name, severity in secret_patterns:
            if re.search(pattern, code):
                threat = Threat(
                    threat_id=hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:8],
                    name=name,
                    category=ThreatCategory.CREDENTIAL_THEFT,
                    severity=severity,
                    description=f"Potential {name} in code",
                    attack_vector="Source code",
                    impact="Credential exposure",
                    likelihood=0.8,
                    mitigations=[
                        "Use environment variables",
                        "Apply secret scanning",
                        "Rotate exposed credentials",
                    ],
                )
                threats.append(threat)
                model.threats.append(threat)

        model.updated_at = time.time()
        return threats

    def get_model(self, model_id: str) -> ThreatModel | None:
        return self._models.get(model_id)

    def generate_report(self, model_id: str) -> dict[str, Any]:
        """Generate a threat model report."""
        model = self._models.get(model_id)
        if not model:
            return {"error": "model not found"}

        return {
            "model_id": model.model_id,
            "target_system": model.target_system,
            "total_threats": len(model.threats),
            "total_risk": model.total_risk,
            "critical_count": model.critical_count,
            "threats_by_severity": {
                "critical": len(model.by_severity(ThreatSeverity.CRITICAL)),
                "high": len(model.by_severity(ThreatSeverity.HIGH)),
                "medium": len(model.by_severity(ThreatSeverity.MEDIUM)),
                "low": len(model.by_severity(ThreatSeverity.LOW)),
            },
            "threats": [
                {
                    "id": t.threat_id,
                    "name": t.name,
                    "category": t.category.value,
                    "severity": t.severity.value,
                    "risk_score": t.risk_score,
                }
                for t in model.threats
            ],
        }
