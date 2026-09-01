"""Safety Plugins — Guardrails, BiasDetection, AdversarialDefense, Privacy, Explainability, Alignment."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginMetadata:
    provides: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)


class BasePlugin:
    def __init__(self, plugin_id: str, provides: list[str]):
        self.id = plugin_id
        self.metadata = PluginMetadata(provides=provides)
        self._loaded = False

    def on_load(self) -> None:
        self._loaded = True

    def on_unload(self) -> None:
        self._loaded = False

    def health_check(self) -> dict[str, Any]:
        return {"healthy": self._loaded}


class GuardrailsPlugin(BasePlugin):
    def __init__(self):
        super().__init__("safety.guardrails", ["guardrails", "limits", "boundaries"])
        self._rules: list[dict] = []

    def add_rule(self, pattern: str, action: str) -> None:
        self._rules.append({"pattern": pattern, "action": action})

    def check(self, text: str) -> dict[str, Any]:
        for rule in self._rules:
            if re.search(rule["pattern"], text, re.IGNORECASE):
                return {"violation": True, "action": rule["action"]}
        return {"violation": False}


class BiasDetectionPlugin(BasePlugin):
    def __init__(self):
        super().__init__("safety.bias", ["bias", "fairness", "equity"])

    def analyze(self, data: list[str]) -> dict[str, Any]:
        return {"bias_score": 0.15, "flagged": []}


class AdversarialDefensePlugin(BasePlugin):
    def __init__(self):
        super().__init__("safety.adversarial", ["adversarial", "robustness", "defense"])

    def detect(self, input_text: str) -> dict[str, Any]:
        return {"is_adversarial": False, "confidence": 0.9}


class PrivacyPlugin(BasePlugin):
    def __init__(self):
        super().__init__("safety.privacy", ["privacy", "pii", "redaction"])

    def redact(self, text: str) -> dict[str, Any]:
        redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED]", text)
        return {"redacted": redacted, "pii_found": 1}

    def pii_types(self) -> list[str]:
        return ["ssn", "email", "phone", "credit_card"]


class ExplainabilityPlugin(BasePlugin):
    def __init__(self):
        super().__init__("safety.explainability", ["explain", "interpret", "transparency"])

    def explain(self, decision: str) -> dict[str, Any]:
        return {"explanation": f"Because of factors A, B, C", "confidence": 0.85}


class AlignmentPlugin(BasePlugin):
    def __init__(self):
        super().__init__("safety.alignment", ["alignment", "values", "intent"])

    def check_alignment(self, action: str, intent: str) -> dict[str, Any]:
        return {"aligned": True, "score": 0.9}
