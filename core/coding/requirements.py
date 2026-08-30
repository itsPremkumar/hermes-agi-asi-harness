"""
Requirement Engineering — Compile natural language into testable requirements.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MIGRATION = "migration"

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Requirement:
    id: str
    type: RequirementType
    description: str
    priority: Priority = Priority.MEDIUM
    acceptance_criteria: List[str] = field(default_factory=list)
    testable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompiledRequirements:
    id: str
    source_text: str
    functional: List[Requirement] = field(default_factory=list)
    non_functional: List[Requirement] = field(default_factory=list)
    constraints: List[Requirement] = field(default_factory=list)
    assumptions: List[Requirement] = field(default_factory=list)
    security: List[Requirement] = field(default_factory=list)
    performance: List[Requirement] = field(default_factory=list)
    migration: List[Requirement] = field(default_factory=list)
    all_requirements: List[Requirement] = field(default_factory=list)
    
    def get_all(self) -> List[Requirement]:
        return self.all_requirements
    
    def get_by_type(self, req_type: RequirementType) -> List[Requirement]:
        mapping = {
            RequirementType.FUNCTIONAL: self.functional,
            RequirementType.NON_FUNCTIONAL: self.non_functional,
            RequirementType.CONSTRAINT: self.constraints,
            RequirementType.ASSUMPTION: self.assumptions,
            RequirementType.SECURITY: self.security,
            RequirementType.PERFORMANCE: self.performance,
            RequirementType.MIGRATION: self.migration,
        }
        return mapping.get(req_type, [])
    
    def get_by_priority(self, priority: Priority) -> List[Requirement]:
        return [r for r in self.all_requirements if r.priority == priority]
    
    def get_testable(self) -> List[Requirement]:
        return [r for r in self.all_requirements if r.testable]
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "total": len(self.all_requirements),
            "functional": len(self.functional),
            "non_functional": len(self.non_functional),
            "constraints": len(self.constraints),
            "testable": len(self.get_testable()),
            "critical": len(self.get_by_priority(Priority.CRITICAL)),
        }


class RequirementsCompiler:
    """Compile natural language requirements into structured form."""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    def compile(self, text: str) -> CompiledRequirements:
        """Compile natural language requirements."""
        result = CompiledRequirements(
            id=str(uuid.uuid4()),
            source_text=text,
        )
        
        # Parse sentences and classify
        sentences = [s.strip() for s in text.replace('\n', '.').split('.') if s.strip()]
        
        for sentence in sentences:
            req = self._parse_sentence(sentence)
            if req:
                result.all_requirements.append(req)
                if req.type == RequirementType.FUNCTIONAL:
                    result.functional.append(req)
                elif req.type == RequirementType.NON_FUNCTIONAL:
                    result.non_functional.append(req)
                elif req.type == RequirementType.CONSTRAINT:
                    result.constraints.append(req)
                elif req.type == RequirementType.ASSUMPTION:
                    result.assumptions.append(req)
                elif req.type == RequirementType.SECURITY:
                    result.security.append(req)
                elif req.type == RequirementType.PERFORMANCE:
                    result.performance.append(req)
                elif req.type == RequirementType.MIGRATION:
                    result.migration.append(req)
        
        return result
    
    def _parse_sentence(self, sentence: str) -> Optional[Requirement]:
        """Parse a single sentence into a requirement."""
        sentence_lower = sentence.lower()
        
        # Determine type
        req_type = RequirementType.FUNCTIONAL
        priority = Priority.MEDIUM
        
        if any(word in sentence_lower for word in ['should', 'must', 'shall', 'will']):
            req_type = RequirementType.FUNCTIONAL
        if any(word in sentence_lower for word in ['fast', 'performance', 'latency', 'throughput', 'speed']):
            req_type = RequirementType.PERFORMANCE
        if any(word in sentence_lower for word in ['secure', 'authentication', 'authorization', 'encrypt']):
            req_type = RequirementType.SECURITY
        if any(word in sentence_lower for word in ['cannot', 'must not', 'constraint', 'limitation']):
            req_type = RequirementType.CONSTRAINT
        if any(word in sentence_lower for word in ['assume', 'assumption', 'given']):
            req_type = RequirementType.ASSUMPTION
        if any(word in sentence_lower for word in ['migrate', 'migration', 'upgrade', 'transition']):
            req_type = RequirementType.MIGRATION
        
        # Determine priority
        if any(word in sentence_lower for word in ['critical', 'essential', 'must']):
            priority = Priority.CRITICAL
        elif any(word in sentence_lower for word in ['important', 'should']):
            priority = Priority.HIGH
        elif any(word in sentence_lower for word in ['nice', 'could', 'optional']):
            priority = Priority.LOW
        
        # Generate acceptance criteria
        acceptance_criteria = self._generate_acceptance_criteria(sentence, req_type)
        
        return Requirement(
            id=str(uuid.uuid4()),
            type=req_type,
            description=sentence,
            priority=priority,
            acceptance_criteria=acceptance_criteria,
            testable=len(acceptance_criteria) > 0,
        )
    
    def _generate_acceptance_criteria(self, sentence: str, req_type: RequirementType) -> List[str]:
        """Generate acceptance criteria for a requirement."""
        criteria = []
        
        if req_type == RequirementType.FUNCTIONAL:
            criteria.append(f"Verify that: {sentence}")
            criteria.append(f"Test case: {sentence} works as expected")
        elif req_type == RequirementType.PERFORMANCE:
            criteria.append(f"Performance test: {sentence}")
            criteria.append(f"Benchmark: {sentence} meets SLA")
        elif req_type == RequirementType.SECURITY:
            criteria.append(f"Security test: {sentence}")
            criteria.append(f"Penetration test: {sentence} is secure")
        
        return criteria
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "id": self.id,
        }
