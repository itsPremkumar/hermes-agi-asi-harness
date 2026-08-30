
"""
Mission Compiler — Transforms ambiguous objectives into verified, structured missions.

Extracted from SKILL.md v9.0 ASI section 4:
- Mission object with full metadata
- Goal compiler pipeline
- Constraint detection
- Evidence requirements
- Verification standards
"""

from __future__ import annotations
import uuid
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .soul import Mission, RiskTier, EpistemicStatus, Claim


class MissionCompiler:
    """
    Compiles natural-language missions into structured, verifiable mission objects.
    
    Pipeline:
        natural-language mission
          → Goal → Subgoals → Outcomes → Constraints → Acceptance Tests → Formal Properties
          → Task Graph → Execution Policy → Verification Plan → Proof Obligations
    """

    def __init__(self):
        self._ambiguity_patterns = [
            r"^(make|do|fix|improve|update|change|add|remove|create|build)\s+(?:a|an|the)?\s*",
            r"(quickly|fast|asap|soon|later|eventually)",
            r"(something|anything|stuff|things)",
            r"(better|good|nice|great|awesome)",
        ]
        self._constraint_patterns = {
            "hard": [r"must", r"required", r"mandatory", r"shall", r"always"],
            "soft": [r"should", r"prefer", r"ideally", r"would be nice"],
            "forbidden": [r"never", r"don't", r"avoid", r"must not", r"prohibited"],
            "legal": [r"legal", r"compliance", r"regulation", r"policy", r"GDPR", r"HIPAA"],
            "ethical": [r"ethical", r"fair", r"unbiased", r"transparent", r"consent"],
            "physical": [r"hardware", r"device", r"robot", r"sensor", r"actuator"],
        }

    def compile(self, raw_request: str, context: Optional[Dict[str, Any]] = None) -> Mission:
        """Compile a raw request into a structured mission."""
        mission = Mission(
            id=str(uuid.uuid4()),
            raw_request=raw_request,
        )

        # 1. Interpret intent
        mission.interpreted_intent = self._interpret_intent(raw_request)

        # 2. Detect superintelligent intent (what user will need next)
        mission.superintelligent_intent = self._detect_latent_needs(raw_request, context)

        # 3. Define desired outcome
        mission.desired_outcome = self._define_outcome(raw_request)

        # 4. Extract constraints
        mission.constraints = self._extract_constraints(raw_request)

        # 5. Determine risk tier
        mission.risk = self._assess_risk(raw_request, mission.constraints)

        # 6. Define acceptance criteria
        mission.acceptance_criteria = self._define_acceptance_criteria(raw_request)

        # 7. Set evidence requirements
        mission.evidence_requirements = self._define_evidence_requirements(raw_request)

        # 8. Set verification standard based on risk
        mission.verification_standard = self._get_verification_standard(mission.risk)

        # 9. Detect assumptions
        mission.assumptions = self._detect_assumptions(raw_request)

        # 10. Identify unknowns
        mission.unknowns = self._identify_unknowns(raw_request)

        # 11. Set budget
        mission.budget = self._estimate_budget(raw_request)

        return mission

    def _interpret_intent(self, request: str) -> str:
        """Extract the core intent from the request."""
        # Remove filler words
        cleaned = request.lower()
        for pattern in self._ambiguity_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _detect_latent_needs(self, request: str, context: Optional[Dict[str, Any]]) -> str:
        """Detect what the user will need next (superintelligent intent)."""
        # Simple heuristic: what would be the next logical step
        if "research" in request.lower():
            return "Synthesize findings into actionable recommendations"
        elif "code" in request.lower() or "build" in request.lower():
            return "Test, document, and deploy the solution"
        elif "analyze" in request.lower():
            return "Present insights with visualizations and recommendations"
        return "Verify outcome and document lessons learned"

    def _define_outcome(self, request: str) -> str:
        """Define the concrete desired outcome."""
        return f"Successfully complete: {request}"

    def _extract_constraints(self, request: str) -> Dict[str, List[str]]:
        """Extract constraints from the request."""
        constraints = {k: [] for k in ["hard", "soft", "forbidden", "physical", "legal", "ethical"]}
        request_lower = request.lower()

        for constraint_type, patterns in self._constraint_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, request_lower)
                if matches:
                    constraints[constraint_type].extend(matches)

        return constraints

    def _assess_risk(self, request: str, constraints: Dict[str, List[str]]) -> RiskTier:
        """Assess risk tier for the mission."""
        if constraints.get("forbidden") or constraints.get("legal"):
            return RiskTier.R4
        if "production" in request.lower() or "deploy" in request.lower():
            return RiskTier.R4
        if "delete" in request.lower() or "remove" in request.lower():
            return RiskTier.R5
        if "self-modify" in request.lower() or "constitution" in request.lower():
            return RiskTier.R6
        if "code" in request.lower() or "write" in request.lower():
            return RiskTier.R2
        if "search" in request.lower() or "research" in request.lower():
            return RiskTier.R1
        return RiskTier.R0

    def _define_acceptance_criteria(self, request: str) -> List[str]:
        """Define measurable acceptance criteria."""
        criteria = []
        if "research" in request.lower():
            criteria.append("At least 5 authoritative sources cited")
            criteria.append("Contradictions identified and resolved")
            criteria.append("Findings synthesized into actionable summary")
        elif "code" in request.lower():
            criteria.append("Code compiles without errors")
            criteria.append("Tests pass")
            criteria.append("Documentation complete")
        else:
            criteria.append("Task completed as requested")
            criteria.append("Outcome verified")
        return criteria

    def _define_evidence_requirements(self, request: str) -> List[str]:
        """Define what evidence is required to prove success."""
        return ["Direct observation of outcome", "Source attribution for claims"]

    def _get_verification_standard(self, risk: RiskTier) -> str:
        """Get verification standard based on risk tier."""
        standards = {
            RiskTier.R0: "test",
            RiskTier.R1: "test",
            RiskTier.R2: "test",
            RiskTier.R3: "independent_verification",
            RiskTier.R4: "independent_verification",
            RiskTier.R5: "proof",
            RiskTier.R6: "proof",
        }
        return standards.get(risk, "test")

    def _detect_assumptions(self, request: str) -> List[str]:
        """Detect hidden assumptions in the request."""
        assumptions = []
        if "the system" in request.lower():
            assumptions.append("System is accessible and operational")
        if "user" in request.lower():
            assumptions.append("User has necessary permissions")
        return assumptions

    def _identify_unknowns(self, request: str) -> List[str]:
        """Identify explicit unknowns."""
        unknowns = []
        if "?" in request:
            unknowns.append("Question explicitly asked")
        return unknowns

    def _estimate_budget(self, request: str) -> Dict[str, Any]:
        """Estimate resource budget for the mission."""
        return {
            "tokens": 10000,
            "tool_calls": 20,
            "time_seconds": 300,
            "compute": "low",
        }

    def detect_ambiguity(self, request: str) -> List[str]:
        """Detect ambiguity in the request."""
        ambiguities = []
        for pattern in self._ambiguity_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                ambiguities.append(f"Ambiguous term: {matches[0]}")
        return ambiguities
