"""Real Code Generation - LLM-powered code synthesis."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class CodeGenRequest:
    spec: str
    language: str = "python"
    context: Dict[str, Any] = None
    tests: bool = True
    docs: bool = True

@dataclass
class CodeGenResult:
    code: str
    tests: str = ""
    docs: str = ""
    imports: List[str] = None
    metadata: Dict[str, Any] = None

class CodeGenerator:
    """Generate code using LLM with context-aware prompts."""
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
    
    async def generate(self, request: CodeGenRequest) -> CodeGenResult:
        """Generate code from specification."""
        # Build context-aware prompt
        prompt = self._build_prompt(request)
        
        if self.llm:
            response = await self.llm.generate(prompt)
            code = response.content
        else:
            code = self._generate_stub(request)
        
        result = CodeGenResult(
            code=code,
            tests=self._generate_tests(request) if request.tests else "",
            docs=self._generate_docs(request) if request.docs else "",
            imports=self._extract_imports(code),
        )
        
        return result
    
    def _build_prompt(self, request: CodeGenRequest) -> str:
        """Build context-aware generation prompt."""
        prompt = f"Generate {request.language} code for:\n\n{request.spec}\n\n"
        
        if request.context:
            if "existing_code" in request.context:
                prompt += f"\nExisting code context:\n{request.context['existing_code']}\n"
            if "imports" in request.context:
                prompt += f"\nRequired imports: {request.context['imports']}\n"
            if "style" in request.context:
                prompt += f"\nCode style: {request.context['style']}\n"
        
        prompt += "\nRequirements:\n"
        prompt += "- Follow best practices\n"
        prompt += "- Include error handling\n"
        prompt += "- Add type hints\n"
        prompt += "- Write clean, readable code\n"
        
        return prompt
    
    def _generate_stub(self, request: CodeGenRequest) -> str:
        """Generate stub code when LLM is not available."""
        if request.language == "python":
            return f'''"""
{request.spec}
"""

def main():
    # TODO: Implement
    pass

if __name__ == "__main__":
    main()
'''
        return f"// {request.spec}\n"
    
    def _generate_tests(self, request: CodeGenRequest) -> str:
        """Generate tests for the code."""
        if request.language == "python":
            return f'''"""
Tests for: {request.spec}
"""

import pytest

def test_basic():
    # TODO: Implement test
    pass
'''
        return ""
    
    def _generate_docs(self, request: CodeGenRequest) -> str:
        """Generate documentation."""
        return f"# {request.spec}\n\n## Usage\n\n```\n# TODO: Add usage examples\n```\n"
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract imports from generated code."""
        imports = []
        for line in code.split('\n'):
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line.strip())
        return imports
