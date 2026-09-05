"""Code Generation Loop — Spec → Context → Design → Implement → Static Check → Test → Review → Commit."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GenerationStage(str, Enum):
    INIT = "init"
    CONTEXT_RETRIEVAL = "context_retrieval"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    STATIC_CHECK = "static_check"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    REVIEW = "review"
    COMMIT = "commit"
    FAILED = "failed"

@dataclass
class GenerationResult:
    id: str
    stage: GenerationStage
    code: str = ""
    errors: list[str] = field(default_factory=list)
    test_results: dict[str, Any] = field(default_factory=dict)
    review_comments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

class CodeGenerationLoop:
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    def generate(self, spec: str, context: dict[str, Any]) -> GenerationResult:
        result = GenerationResult(id=str(uuid.uuid4()), stage=GenerationStage.INIT)
        
        # Stage 1: Context Retrieval
        result.stage = GenerationStage.CONTEXT_RETRIEVAL
        retrieved_context = self._retrieve_context(spec, context)
        
        # Stage 2: Design
        result.stage = GenerationStage.DESIGN
        design = self._design(spec, retrieved_context)
        
        # Stage 3: Implementation
        result.stage = GenerationStage.IMPLEMENTATION
        code = self._implement(spec, design, retrieved_context)
        result.code = code
        
        # Stage 4: Static Check
        result.stage = GenerationStage.STATIC_CHECK
        static_errors = self._static_check(code)
        if static_errors:
            result.errors.extend(static_errors)
            result.stage = GenerationStage.FAILED
            return result
        
        # Stage 5: Unit Test
        result.stage = GenerationStage.UNIT_TEST
        unit_results = self._run_unit_tests(code)
        result.test_results = unit_results
        if unit_results.get("failed", 0) > 0:
            result.stage = GenerationStage.FAILED
            return result
        
        # Stage 6: Review
        result.stage = GenerationStage.REVIEW
        review = self._review(code, spec)
        result.review_comments = review.get("comments", [])
        
        # Stage 7: Commit
        result.stage = GenerationStage.COMMIT
        return result
    
    def _retrieve_context(self, spec: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"files": context.get("files", []), "symbols": context.get("symbols", [])}
    
    def _design(self, spec: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"approach": "direct_implementation", "files_to_modify": []}
    
    def _implement(self, spec: str, design: dict[str, Any], context: dict[str, Any]) -> str:
        return f"# Implementation for: {spec}\n"
    
    def _static_check(self, code: str) -> list[str]:
        return []
    
    def _run_unit_tests(self, code: str) -> dict[str, Any]:
        return {"passed": 1, "failed": 0, "total": 1}
    
    def _review(self, code: str, spec: str) -> dict[str, Any]:
        return {"passed": True, "comments": []}
    
    def get_state(self) -> dict[str, Any]:
        return {"id": self.id}
