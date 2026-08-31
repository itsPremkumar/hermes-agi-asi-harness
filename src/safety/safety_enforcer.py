"""Safety Enforcer — enforce safety policies and block dangerous operations."""

from __future__ import annotations

import re
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable

from src.safety.threat_modeler import Threat, ThreatCategory, ThreatSeverity


class PolicyType(Enum):
    """Types of safety policies that can be enforced."""

    BLOCK_PROMPT_INJECTION = "block_prompt_injection"
    BLOCK_DATA_EXFILTRATION = "block_data_exfiltration"
    BLOCK_PRIVILEGE_ESCALATION = "block_privilege_escalation"
    BLOCK_CREDENTIAL_EXPOSURE = "block_credential_exposure"
    BLOCK_DOS = "block_dos"
    BLOCK_MODEL_MANIPULATION = "block_model_manipulation"
    ALLOWLIST_OPERATIONS = "allowlist_operations"
    BLOCKLIST_OPERATIONS = "blocklist_operations"
    RATE_LIMIT = "rate_limit"
    RESOURCE_QUOTA = "resource_quota"
    CUSTOM = "custom"


class EnforcementAction(Enum):
    """Actions the enforcer can take when a policy is violated."""

    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"
    SANITIZE = "sanitize"
    ESCALATE = "escalate"
    REDIRECT = "redirect"


@dataclass
class PolicyRule:
    """A single safety policy rule."""

    id: str
    policy_type: PolicyType
    name: str
    description: str
    action: EnforcementAction = EnforcementAction.BLOCK
    enabled: bool = True
    # Condition can be a regex pattern (for pattern-based rules) or empty
    # (for always-on rules like global rate limits).
    condition: str = ""
    # Severity threshold: only enforce for threats at or above this severity.
    severity_threshold: ThreatSeverity = ThreatSeverity.LOW
    # Metadata / config specific to this rule.
    config: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    enforced_count: int = 0
    blocked_count: int = 0

    @property
    def is_active(self) -> bool:
        return self.enabled

    def matches(self, threat: Threat) -> bool:
        """Check whether this rule applies to a given threat."""
        if not self.enabled:
            return False

        # Severity threshold check
        severity_order = {
            ThreatSeverity.INFO: 0,
            ThreatSeverity.LOW: 1,
            ThreatSeverity.MEDIUM: 2,
            ThreatSeverity.HIGH: 3,
            ThreatSeverity.CRITICAL: 4,
        }
        threat_level = severity_order.get(threat.severity, 0)
        threshold_level = severity_order.get(self.severity_threshold, 0)
        if threat_level < threshold_level:
            return False

        # If there is a condition, try to match it.
        if self.condition:
            # Check category first
            if self.condition in ThreatCategory.__members__:
                cat = ThreatCategory[self.condition]
                if threat.category != cat:
                    return False
            # Try regex match against description / attack_vector
            else:
                text_to_check = f"{threat.description} {threat.attack_vector}"
                if not re.search(self.condition, text_to_check, re.IGNORECASE):
                    return False

        return True


@dataclass
class EnforcementResult:
    """Result of a policy enforcement decision."""

    rule_id: str
    action: EnforcementAction
    allowed: bool
    reason: str
    threat_detected: Optional[Threat] = None
    blocked_threats: list[Threat] = field(default_factory=list)
    sanitized_content: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def was_blocked(self) -> bool:
        return not self.allowed


@dataclass
class RateLimitState:
    """Rate-limiting state for a key."""

    request_times: list[float] = field(default_factory=list)
    violation_count: int = 0


class SafetyEnforcer:
    """Enforce safety policies and block dangerous operations."""

    # Default built-in rules for common AI safety threats.
    DEFAULT_RULES: list[dict[str, Any]] = [
        {
            "id": "rule_prompt_injection",
            "policy_type": PolicyType.BLOCK_PROMPT_INJECTION,
            "name": "Block Prompt Injection",
            "description": "Block inputs attempting to override system instructions",
            "action": EnforcementAction.BLOCK,
            "condition": "PROMPT_INJECTION",
            "severity_threshold": ThreatSeverity.LOW,
        },
        {
            "id": "rule_data_exfil",
            "policy_type": PolicyType.BLOCK_DATA_EXFILTRATION,
            "name": "Block Data Exfiltration",
            "description": "Block attempts to exfiltrate sensitive data",
            "action": EnforcementAction.BLOCK,
            "condition": "DATA_EXFILTRATION",
            "severity_threshold": ThreatSeverity.LOW,
        },
        {
            "id": "rule_priv_esc",
            "policy_type": PolicyType.BLOCK_PRIVILEGE_ESCALATION,
            "name": "Block Privilege Escalation",
            "description": "Block privilege escalation attempts",
            "action": EnforcementAction.BLOCK,
            "condition": "PRIVILEGE_ESCALATION",
            "severity_threshold": ThreatSeverity.LOW,
        },
        {
            "id": "rule_cred_theft",
            "policy_type": PolicyType.BLOCK_CREDENTIAL_EXPOSURE,
            "name": "Block Credential Exposure",
            "description": "Block attempts to expose credentials",
            "action": EnforcementAction.BLOCK,
            "condition": "CREDENTIAL_THEFT",
            "severity_threshold": ThreatSeverity.LOW,
        },
        {
            "id": "rule_dos",
            "policy_type": PolicyType.BLOCK_DOS,
            "name": "Block Denial of Service",
            "description": "Block DoS / resource exhaustion attempts",
            "action": EnforcementAction.BLOCK,
            "condition": ThreatCategory.DENIAL_OF_SERVICE.value,
            "severity_threshold": ThreatSeverity.LOW,
        },
        {
            "id": "rule_model_manip",
            "policy_type": PolicyType.BLOCK_MODEL_MANIPULATION,
            "name": "Block Model Manipulation",
            "description": "Block model manipulation and jailbreaking attempts",
            "action": EnforcementAction.BLOCK,
            "condition": "MODEL_MANIPULATION",
            "severity_threshold": ThreatSeverity.LOW,
        },
    ]

    def __init__(self):
        self._lock = threading.RLock()
        self._rules: dict[str, PolicyRule] = {}
        self._rate_limit_state: dict[str, RateLimitState] = {}
        self._custom_callbacks: dict[str, Callable] = {}
        self._decision_log: list[dict[str, Any]] = []
        self._rule_counter = 0

        # Install default rules
        for rule_spec in self.DEFAULT_RULES:
            self._add_rule_from_spec(rule_spec)

    def _add_rule_from_spec(self, spec: dict[str, Any]) -> None:
        rule = PolicyRule(
            id=spec["id"],
            policy_type=spec["policy_type"],
            name=spec["name"],
            description=spec["description"],
            action=spec.get("action", EnforcementAction.BLOCK),
            enabled=spec.get("enabled", True),
            condition=spec.get("condition", ""),
            severity_threshold=spec.get(
                "severity_threshold", ThreatSeverity.LOW
            ),
            config=spec.get("config", {}),
        )
        self._rules[rule.id] = rule

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: PolicyRule) -> bool:
        """Register a new policy rule."""
        with self._lock:
            if rule.id in self._rules:
                return False
            self._rules[rule.id] = rule
            return True

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a policy rule by ID."""
        with self._lock:
            return self._rules.pop(rule_id, None) is not None

    def enable_rule(self, rule_id: str, enabled: bool = True) -> bool:
        """Enable or disable a rule."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            rule.enabled = enabled
            return True

    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[PolicyRule]:
        """List all registered rules (including built-in defaults)."""
        return list(self._rules.values())

    def list_active_rules(self) -> list[PolicyRule]:
        """List only enabled rules."""
        return [r for r in self._rules.values() if r.enabled]

    # ------------------------------------------------------------------
    # Enforcement
    # ------------------------------------------------------------------

    def enforce(self, threats: list[Threat]) -> EnforcementResult:
        """Evaluate a list of threats against all active rules.

        Returns an EnforcementResult describing whether the action is allowed
        and which threats (if any) were blocked.
        """
        with self._lock:
            blocked_threats: list[Threat] = []
            matched_rules: list[str] = []
            reasons: list[str] = []

            for threat in threats:
                for rule in self._rules.values():
                    if not rule.enabled:
                        continue
                    if rule.matches(threat):
                        rule.enforced_count += 1
                        matched_rules.append(rule.id)
                        reasons.append(
                            f"Rule '{rule.name}' matched threat "
                            f"'{threat.name}' ({threat.category.value}, "
                            f"{threat.severity.value})"
                        )

                        if rule.action == EnforcementAction.BLOCK:
                            blocked_threats.append(threat)
                            rule.blocked_count += 1
                        elif rule.action == EnforcementAction.WARN:
                            # Warn but still allow
                            pass
                        elif rule.action == EnforcementAction.SANITIZE:
                            blocked_threats.append(threat)
                            rule.blocked_count += 1

            allowed = len(blocked_threats) == 0
            action = EnforcementAction.BLOCK if blocked_threats else EnforcementAction.ALLOW

            result = EnforcementResult(
                rule_id=matched_rules[0] if matched_rules else "",
                action=action,
                allowed=allowed,
                reason="; ".join(reasons) if reasons else "All clear",
                blocked_threats=blocked_threats,
                metadata={
                    "matched_rules": matched_rules,
                    "total_threats": len(threats),
                    "blocked_count": len(blocked_threats),
                },
            )

            self._decision_log.append({
                "timestamp": time.time(),
                "action": action.value,
                "allowed": allowed,
                "threat_count": len(threats),
                "blocked_count": len(blocked_threats),
                "matched_rules": matched_rules,
            })

            return result

    def enforce_input(self, user_input: str) -> EnforcementResult:
        """Quick enforcement of a raw user input string.

        Scans for simple danger patterns and returns a result.  This is a
        lightweight convenience method that does not require a ThreatModeler
        — useful for fast pre-checks.
        """
        dangerous_patterns = [
            (r"(?i)\b(ignore\s+previous|system\s+override|jailbreak)",
             ThreatCategory.PROMPT_INJECTION, ThreatSeverity.HIGH),
            (r"(?i)\b(exfiltrate|send.*to.*external)",
             ThreatCategory.DATA_EXFILTRATION, ThreatSeverity.HIGH),
            (r"(?i)\b(sudo|root\s+privileges)",
             ThreatCategory.PRIVILEGE_ESCALATION, ThreatSeverity.MEDIUM),
            (r"(?i)\b(password|secret\s*=|api\s*key)",
             ThreatCategory.CREDENTIAL_THEFT, ThreatSeverity.CRITICAL),
            (r"(?i)\b(infinite\s+loop|resource\s+exhaustion)",
             ThreatCategory.DENIAL_OF_SERVICE, ThreatSeverity.MEDIUM),
        ]

        detected_threats: list[Threat] = []
        import hashlib

        for pattern, category, severity in dangerous_patterns:
            if re.search(pattern, user_input):
                tid = hashlib.sha256(
                    f"{user_input}{time.time()}{category.value}".encode()
                ).hexdigest()[:8]
                threat = Threat(
                    threat_id=tid,
                    name=f"{category.value}_in_input",
                    category=category,
                    severity=severity,
                    description=f"Detected {category.value} pattern in user input",
                    attack_vector=user_input[:200],
                    impact="Potential security breach",
                    likelihood=0.85,
                    mitigations=["Block the input", "Alert security team"],
                )
                detected_threats.append(threat)

        return self.enforce(detected_threats)

    def check_operation(
        self,
        operation: str,
        context: dict[str, Any] | None = None,
        allowlist: list[str] | None = None,
        blocklist: list[str] | None = None,
    ) -> EnforcementResult:
        """Check whether an operation is allowed, optionally against
        allowlist / blocklist."""
        context = context or {}

        # Check blocklist first (more dangerous if explicitly blocked)
        if blocklist:
            for blocked in blocklist:
                if re.search(blocked, operation, re.IGNORECASE):
                    return EnforcementResult(
                        rule_id="blocklist_check",
                        action=EnforcementAction.BLOCK,
                        allowed=False,
                        reason=f"Operation matches blocklist pattern: {blocked}",
                        metadata={"operation": operation, "blocklist_match": blocked},
                    )

        # Then check allowlist
        if allowlist:
            for allowed_pattern in allowlist:
                if re.search(allowed_pattern, operation, re.IGNORECASE):
                    return EnforcementResult(
                        rule_id="allowlist_check",
                        action=EnforcementAction.ALLOW,
                        allowed=True,
                        reason=f"Operation matches allowlist pattern: {allowed_pattern}",
                        metadata={"operation": operation, "allowlist_match": allowed_pattern},
                    )
            # Did not match any allowlist entry
            if not allowlist:
                return EnforcementResult(
                    rule_id="allowlist_check",
                    action=EnforcementAction.BLOCK,
                    allowed=False,
                    reason="Operation not in allowlist",
                    metadata={"operation": operation},
                )
            return EnforcementResult(
                rule_id="allowlist_check",
                action=EnforcementAction.BLOCK,
                allowed=False,
                reason="Operation not in allowlist",
                metadata={"operation": operation},
            )

        # No allowlist or blocklist — default allow
        return EnforcementResult(
            rule_id="default",
            action=EnforcementAction.ALLOW,
            allowed=True,
            reason="No allowlist or blocklist configured",
            metadata={"operation": operation},
        )

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> bool:
        """Check if a key has exceeded its rate limit.

        Returns True if the request is ALLOWED, False if rate-limited.
        """
        with self._lock:
            now = time.time()
            state = self._rate_limit_state.setdefault(key, RateLimitState())

            # Prune old timestamps
            state.request_times = [
                t for t in state.request_times if now - t < window_seconds
            ]

            if len(state.request_times) >= max_requests:
                state.violation_count += 1
                return False

            state.request_times.append(now)
            return True

    def get_rate_limit_state(self, key: str) -> Optional[RateLimitState]:
        return self._rate_limit_state.get(key)

    def reset_rate_limit(self, key: str) -> None:
        with self._lock:
            self._rate_limit_state.pop(key, None)

    # ------------------------------------------------------------------
    # Custom rules
    # ------------------------------------------------------------------

    def add_custom_rule(
        self,
        name: str,
        check_fn: Callable[[Threat], bool],
        action: EnforcementAction = EnforcementAction.BLOCK,
        severity_threshold: ThreatSeverity = ThreatSeverity.LOW,
    ) -> str:
        """Register a custom callable-based rule."""
        with self._lock:
            self._rule_counter += 1
            rule_id = f"custom_{self._rule_counter}"
            self._custom_callbacks[rule_id] = check_fn

            rule = PolicyRule(
                id=rule_id,
                policy_type=PolicyType.CUSTOM,
                name=name,
                description=f"Custom rule: {name}",
                action=action,
                severity_threshold=severity_threshold,
            )
            # Store the check function on the rule for later use
            rule.config["check_fn"] = check_fn
            self._rules[rule_id] = rule
            return rule_id

    # ------------------------------------------------------------------
    # Audit / stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_rules": len(self._rules),
                "active_rules": len(self.list_active_rules()),
                "decision_log_entries": len(self._decision_log),
                "total_blocks": sum(r.blocked_count for r in self._rules.values()),
                "total_enforcements": sum(r.enforced_count for r in self._rules.values()),
                "rate_limit_keys": len(self._rate_limit_state),
            }

    def get_decision_log(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._decision_log[-limit:])

    def clear_decision_log(self) -> None:
        with self._lock:
            self._decision_log.clear()

    def reset(self) -> None:
        """Reset all state (rules revert to defaults, logs cleared)."""
        with self._lock:
            self._rules.clear()
            self._rate_limit_state.clear()
            self._custom_callbacks.clear()
            self._decision_log.clear()
            self._rule_counter = 0
            for rule_spec in self.DEFAULT_RULES:
                self._add_rule_from_spec(rule_spec)


__all__ = [
    "PolicyType",
    "EnforcementAction",
    "PolicyRule",
    "EnforcementResult",
    "RateLimitState",
    "SafetyEnforcer",
]
