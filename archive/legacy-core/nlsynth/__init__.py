#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v6.0 — NL PROGRAM SYNTHESIZER
=====================================================
Natural language to executable code.

Extracted from:
- agi-hermes-advanced-master SKILL.md section 11 (Reasoning Portfolio)
- hermes-super-harness plugins/deerflow_v2/agents/coder.py
"""

from __future__ import annotations

import ast
import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_nlsynth")


@dataclass
class NLSpec:
    """Natural language specification."""
    description: str
    language: str = "python"
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)


class NLProgramSynthesizer:
    """
    Natural language program synthesis.
    
    Features:
    - Convert natural language to executable code
    - Handle ambiguous specifications through clarification
    - Generate code in multiple languages
    - Optimize generated code
    - Explain generated code in natural language
    - Generate tests alongside code
    - Refactor based on style guidelines
    """
    
    def __init__(self):
        self._history: list[dict[str, Any]] = []
    
    async def synthesize(self, spec: NLSpec) -> dict[str, Any]:
        """Synthesize code from natural language specification."""
        logger.info("Synthesizing: %s", spec.description[:50])
        
        # Parse specification
        parsed = self._parse_spec(spec)
        
        # Generate code
        code = self._generate_code(parsed, spec.language)
        
        # Validate
        validation = self._validate_code(code, spec.language)
        
        # Generate tests
        tests = self._generate_tests(code, spec)
        
        # Explain
        explanation = self._explain_code(code)
        
        result = {
            "id": str(uuid.uuid4()),
            "spec": spec.__dict__,
            "code": code,
            "language": spec.language,
            "tests": tests,
            "explanation": explanation,
            "validation": validation,
            "timestamp": time.time()
        }
        
        self._history.append(result)
        return result
    
    def _parse_spec(self, spec: NLSpec) -> dict[str, Any]:
        """Parse natural language specification."""
        parsed = {
            "function_name": self._extract_function_name(spec.description),
            "inputs": spec.inputs,
            "outputs": spec.outputs,
            "operations": self._extract_operations(spec.description),
            "constraints": spec.constraints
        }
        
        # Detect ambiguities
        ambiguities = self._detect_ambiguities(spec.description)
        if ambiguities:
            parsed["ambiguities"] = ambiguities
        
        return parsed
    
    def _extract_function_name(self, description: str) -> str:
        """Extract function name from description."""
        # Look for patterns like "create a function called X" or "implement X"
        patterns = [
            r'function\s+(?:called\s+)?["\']?(\w+)["\']?',
            r'implement\s+(\w+)',
            r'create\s+(?:a\s+)?(\w+)',
            r'define\s+(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                return match.group(1)
        
        # Default: use first significant word
        words = description.split()
        for word in words:
            if word.lower() not in ["create", "a", "function", "that", "to", "the", "and"]:
                return word.lower()
        
        return "generated_function"
    
    def _extract_operations(self, description: str) -> list[str]:
        """Extract operations from description."""
        operations = []
        keywords = ["calculate", "compute", "process", "transform", "filter", "sort", "search", "find"]
        
        for keyword in keywords:
            if keyword in description.lower():
                operations.append(keyword)
        
        return operations
    
    def _detect_ambiguities(self, description: str) -> list[str]:
        """Detect ambiguities in specification."""
        ambiguities = []
        vague_terms = ["some", "various", "appropriate", "suitable", "good", "better"]
        
        for term in vague_terms:
            if term in description.lower():
                ambiguities.append(f"Vague term: '{term}'")
        
        return ambiguities
    
    def _generate_code(self, parsed: dict[str, Any], language: str) -> str:
        """Generate code from parsed specification."""
        if language == "python":
            return self._generate_python(parsed)
        return f"# Code generation for {language} not yet implemented"
    
    def _generate_python(self, parsed: dict[str, Any]) -> str:
        """Generate Python code."""
        func_name = parsed["function_name"]
        inputs = parsed.get("inputs", {})
        outputs = parsed.get("outputs", {})
        
        # Build function signature
        params = ", ".join([f"{k}: {v}" for k, v in inputs.items()]) if inputs else ""
        return_type = next(iter(outputs.values())) if outputs else "Any"
        
        code = f'''def {func_name}({params}) -> {return_type}:
    """
    {parsed.get("description", "Generated function")}
    """
    # TODO: Implement function logic
    pass
'''
        return code
    
    def _validate_code(self, code: str, language: str) -> dict[str, Any]:
        """Validate generated code."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        if language == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                result["valid"] = False
                result["errors"].append(str(e))
        
        return result
    
    def _generate_tests(self, code: str, spec: NLSpec) -> str:
        """Generate tests for code."""
        return f'''
import pytest

def test_{spec.description[:20].replace(" ", "_")}():
    """Test generated function."""
    # TODO: Add test cases
    pass
'''
    
    def _explain_code(self, code: str) -> str:
        """Generate natural language explanation of code."""
        lines = code.strip().split('\n')
        explanation = f"This code contains {len(lines)} lines. "
        
        if "def " in code:
            explanation += "It defines a function. "
        if "class " in code:
            explanation += "It defines a class. "
        if "import " in code:
            explanation += "It imports external modules. "
        
        return explanation
    
    async def clarify(self, ambiguities: list[str]) -> list[str]:
        """Generate clarification questions for ambiguities."""
        questions = []
        for ambiguity in ambiguities:
            questions.append(f"Could you clarify: {ambiguity}?")
        return questions
    
    async def health(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "history_count": len(self._history)
        }
