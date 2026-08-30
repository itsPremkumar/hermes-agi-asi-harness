"""Threat Modeler — identify and model security threats for AI agent systems.

Part of the Advanced Safety Module. Builds threat models from STRIDE-style
categories, scans agent inputs and source code for known attack vectors, and
produces structured reports for downstream risk assessment.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "Threat",
    "ThreatCategory",
    "ThreatModel",
    "ThreatModeler",
    "ThreatSeverity",
]


class ThreatSeverity(Enum):
    """Severity levels for detected threats."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(Enum):
    """STRIDE-style threat categories."""

    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DENIAL_OF_SERVICE = "denial_of_service"
    MODEL_MANIPULATION = "model_manipulation"
    CREDENTIAL_THEFT = "credential_theft"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SIDE_CHANNEL = "side_channel"
    REPLAY_ATTACK = "replay_attack"
    CODE_INJECTION = "code_injection"


_SEVERITY_WEIGHT = {
    ThreatSeverity.CRITICAL: 1.0,
    ThreatSeverity.HIGH: 0.8,
    ThreatSeverity.MEDIUM: 0.5,
    ThreatSeverity.LOW: 0.2,
    ThreatSeverity.INFO: 0.05,
}


@dataclass
class Threat:
    """A single identified threat."""

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
        """Risk score in [0, 1] = severity weight * likelihood."""
        return _SEVERITY_WEIGHT[self.severity] * self.likelihood

    def to_dict(self) -> dict[str, Any]:
        return {
            "threat_id": self.threat_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "attack_vector": self.attack_vector,
            "impact": self.impact,
            "likelihood": self.likelihood,
            "risk_score": self.risk_score,
            "mitigations": list(self.mitigations),
            "detected_at": self.detected_at,
        }


@dataclass
class ThreatModel:
    """A collection of threats for a target system."""

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

    @property
    def high_count(self) -> int:
        return sum(1 for t in self.threats if t.severity == ThreatSeverity.HIGH)

    def by_severity(self, severity: ThreatSeverity) -> list[Threat]:
        return [t for t in self.threats if t.severity == severity]

    def by_category(self, category: ThreatCategory) -> list[Threat]:
        return [t for t in self.threats if t.category == category]

    def top_risks(self, n: int = 5) -> list[Threat]:
        return sorted(self.threats, key=lambda t: t.risk_score, reverse=True)[:n]


class ThreatModeler:
    """Analyze AI agent systems for security threats."""

    # Input-pattern signatures per category (compiled lazily / cached).
    PATTERNS: dict[ThreatCategory, list[str]] = {
        ThreatCategory.PROMPT_INJECTION: [
            r"ignore\s+previous\s+instructions",
            r"you are now\s",
            r"system\s+override",
            r"jailbreak",
            r"pretend\s+you\s+are",
            r"dvp\s+override",
            r"new\s+instructions\s*:",
            r"forget\s+everything",
        ],
        ThreatCategory.DATA_EXFILTRATION: [
            r"send\s+to\s+external",
            r"exfiltrate",
            r"upload\s+credentials",
            r"POST\s+http",
            r"leak\s+to\s+\w",
            r"write\s+to\s+\\.\\.?",
        ],
        ThreatCategory.PRIVILEGE_ESCALATION: [
            r"\bsudo\b",
            r"admin\s+access",
            r"root\s+privileges",
            r"escalate\s+privile",
            r"grant\s+me\s+admin",
        ],
        ThreatCategory.DENIAL_OF_SERVICE: [
            r"infinite\s+loop",
            r"resource\s+exhaustion",
            r"flood\s+",
            r"throttle\s+all",
            r"\bkillall\b",
            r"fork\s+bomb",
        ],
        ThreatCategory.CREDENTIAL_THEFT: [
            r"API\s+key\s*",
            r"\bsecret\b\s*[:=]",
            r"password\s*[:=]",
            r"token\s+leak",
            r"\bprivate_key\b",
        ],
        ThreatCategory.MODEL_MANIPULATION: [
            r"poison\s+training",
            r"adversarial\s+example",
            r"model\s+weights",
            r"\bbackdoor\b",
            r"misalign",
        ],
        ThreatCategory.CODE_INJECTION: [
            r"eval\s*\(",
            r"exec\s*\(",
            r"os\.system\s*\(",
            r"subprocess\..*shell",
            r"__import__\s*\(",
        ],
    }

    # Code-level secret signatures: (regex, label, severity).
    SECRET_PATTERNS: list[tuple[str, str, ThreatSeverity]] = [
        (r"sk-[a-zA-Z0-9]{32,}", "hardcoded_api_key", ThreatSeverity.CRITICAL),
        (r"ghp_[a-zA-Z0-9]{36}", "hardcoded_github_token", ThreatSeverity.CRITICAL),
        (r"AKIA[0-9A-Z]{16}", "hardcoded_aws_key", ThreatSeverity.CRITICAL),
        (r"password\s*=\s*['\"][^'\"]{4,}['\"]", "hardcoded_password", ThreatSeverity.HIGH),
        (r"secret\s*=\s*['\"][^'\"]{4,}['\"]", "hardcoded_secret", ThreatSeverity.HIGH),
    ]

    def __init__(self) -> None:
        self._models: dict[str, ThreatModel] = {}
        self._compiled: dict[ThreatCategory, list[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        for category, patterns in self.PATTERNS.items():
            self._compiled[category] = [re.compile(p, re.IGNORECASE) for p in patterns]

    @staticmethod
    def _gen_id(*parts: str) -> str:
        digest = hashlib.sha256("".join(parts).encode()).hexdigest()
        return digest[:12]

    def create_model(self, target_system: str) -> str:
        """Create a new threat model for *target_system*. Returns the model_id."""
        model_id = self._gen_id(target_system, str(time.time()))
        model = ThreatModel(model_id=model_id, target_system=target_system)
        self._models[model_id] = model
        logger.info("Created threat model %s for %s", model_id, target_system)
        return model_id

    def analyze_input(self, model_id: str, user_input: str) -> list[Threat]:
        """Scan free-form *user_input* for threat patterns."""
        model = self._models.get(model_id)
        if not model:
            return []

        threats: list[Threat] = []
        text = user_input
        for category, compiled in self._compiled.items():
            for pattern in compiled:
                match = pattern.search(text)
                if match:
                    name = f"{category.value}_detected"
                    threat = Threat(
                        threat_id=self._gen_id(name, match.group(), str(time.time())),
                        name=name,
                        category=category,
                        severity=ThreatSeverity.HIGH,
                        description=f"Detected potential {category.value} pattern: {match.group()[:80]}",
                        attack_vector=match.group()[:120],
                        impact="Potential security breach or policy violation",
                        likelihood=0.7,
                        mitigations=[
                            "Sanitize and validate user input",
                            "Apply rate limiting on the affected channel",
                            "Log and monitor for repeated attempts",
                        ],
                    )
                    threats.append(threat)
                    model.threats.append(threat)

        model.updated_at = time.time()
        return threats

    def analyze_code(self, model_id: str, code: str, language: str = "python") -> list[Threat]:
        """Scan *code* for hardcoded secrets and injection vectors."""
        model = self._models.get(model_id)
        if not model:
            return []

        threats: list[Threat] = []
        for pattern, name, severity in self.SECRET_PATTERNS:
            match = re.search(pattern, code)
            if match:
                threat = Threat(
                    threat_id=self._gen_id(name, match.group(), str(time.time())),
                    name=name,
                    category=ThreatCategory.CREDENTIAL_THEFT,
                    severity=severity,
                    description=f"Potential {name} in source code",
                    attack_vector="Source code scan",
                    impact="Credential exposure and unauthorized access",
                    likelihood=0.85,
                    mitigations=[
                        "Use environment variables / secret manager",
                        "Apply secret scanning in CI",
                        "Rotate exposed credentials immediately",
                    ],
                )
                threats.append(threat)
                model.threats.append(threat)

        model.updated_at = time.time()
        return threats

    def add_threat(self, model_id: str, threat: Threat) -> bool:
        """Manually attach a *threat* to a model. Returns whether it was added."""
        model = self._models.get(model_id)
        if not model:
            return False
        model.threats.append(threat)
        model.updated_at = time.time()
        return True

    def get_model(self, model_id: str) -> ThreatModel | None:
        return self._models.get(model_id)

    def list_models(self) -> list[str]:
        return list(self._models.keys())

    def generate_report(self, model_id: str) -> dict[str, Any]:
        """Produce a JSON-serializable threat model report."""
        model = self._models.get(model_id)
        if not model:
            return {"error": "model not found", "model_id": model_id}

        by_sev = {s.value: len(model.by_severity(s)) for s in ThreatSeverity}
        by_cat = {c.value: len(model.by_category(c)) for c in ThreatCategory}

        return {
            "model_id": model.model_id,
            "target_system": model.target_system,
            "total_threats": len(model.threats),
            "total_risk": round(model.total_risk, 4),
            "critical_count": model.critical_count,
            "high_count": model.high_count,
            "by_severity": by_sev,
            "by_category": by_cat,
            "top_risks": [t.to_dict() for t in model.top_risks(5)],
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
