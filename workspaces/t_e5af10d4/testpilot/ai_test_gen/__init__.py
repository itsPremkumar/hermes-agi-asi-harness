"""AI test case generation from requirements."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from testpilot.models import TestCaseSpec, TestType


class AITestGenerator:
    """Generates test case specifications from natural language requirements."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        api_key: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def generate(
        self,
        requirement: str,
        test_type: TestType = TestType.UNIT,
        context: str | None = None,
    ) -> TestCaseSpec:
        """Generate a test case from a natural language requirement."""
        # Try LLM-based generation if API key is available
        if self.api_key:
            try:
                return self._generate_with_llm(requirement, test_type, context)
            except Exception:
                pass

        # Fallback: rule-based generation
        return self._generate_rule_based(requirement, test_type)

    def _generate_with_llm(
        self,
        requirement: str,
        test_type: TestType,
        context: str | None,
    ) -> TestCaseSpec:
        """Generate test case using an LLM API."""
        import httpx

        prompt = self._build_prompt(requirement, test_type, context)
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a test generation expert. Generate structured test specifications in JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return TestCaseSpec(**parsed)

    def _generate_rule_based(
        self, requirement: str, test_type: TestType
    ) -> TestCaseSpec:
        """Generate test case using rule-based heuristics (no LLM)."""
        # Extract key action verbs and entities
        words = requirement.lower().split()
        action_verbs = [
            "create",
            "read",
            "update",
            "delete",
            "login",
            "logout",
            "register",
            "search",
            "filter",
            "sort",
            "validate",
            "submit",
            "cancel",
            "approve",
            "reject",
            "send",
            "receive",
            "upload",
            "download",
        ]
        found_verbs = [v for v in action_verbs if v in words]

        # Build test name from requirement
        test_name = self._requirement_to_test_name(requirement)

        # Generate assertions based on detected patterns
        assertions: list[str] = []
        setup_steps: list[str] = []

        if "login" in words or "authenticate" in words:
            setup_steps.extend([
                "Create a test user with valid credentials",
                "Navigate to the login page",
            ])
            assertions.extend([
                "Response status is 200",
                "Session token is returned",
                "User is redirected to dashboard",
            ])
        elif "create" in words or "add" in words or "register" in words:
            setup_steps.extend([
                "Prepare valid input data",
                "Ensure no conflicting records exist",
            ])
            assertions.extend([
                "Response status is 201",
                "Created resource is returned",
                "Resource exists in database",
            ])
        elif "delete" in words or "remove" in words:
            setup_steps.extend([
                "Create a resource to delete",
                "Verify resource exists",
            ])
            assertions.extend([
                "Response status is 204 or 200",
                "Resource no longer exists in database",
            ])
        elif "validate" in words:
            setup_steps.extend([
                "Prepare valid and invalid input samples",
            ])
            assertions.extend([
                "Valid input is accepted",
                "Invalid input returns appropriate error",
                "Error message is descriptive",
            ])
        else:
            setup_steps.append("Set up test preconditions")
            assertions.extend([
                "Operation completes successfully",
                "Result matches expected output",
                "No exceptions are raised",
            ])

        return TestCaseSpec(
            name=test_name,
            description=requirement,
            test_type=test_type,
            requirements=[requirement],
            setup_steps=setup_steps,
            assertions=assertions,
            tags=found_verbs or ["generated"],
        )

    @staticmethod
    def _requirement_to_test_name(requirement: str) -> str:
        """Convert a requirement string to a valid test function name."""
        # Remove special characters, convert to snake_case
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", requirement)
        words = cleaned.lower().split()[:6]  # Limit length
        return "test_" + "_".join(words)

    def _build_prompt(
        self,
        requirement: str,
        test_type: TestType,
        context: str | None,
    ) -> str:
        """Build the LLM prompt for test generation."""
        prompt = f"""Generate a test case specification for the following requirement:

Requirement: {requirement}
Test Type: {test_type.value}
"""
        if context:
            prompt += f"\nContext:\n{context}\n"

        prompt += """
Return a JSON object with these fields:
- name: test function name (snake_case, prefixed with test_)
- description: brief description
- requirements: list of requirement strings
- setup_steps: list of setup step descriptions
- assertions: list of assertion descriptions
- tags: list of tag strings
"""
        return prompt

    def generate_test_code(self, spec: TestCaseSpec) -> str:
        """Generate pytest code from a test case spec."""
        lines = [
            "import pytest",
            "",
            "",
            f"def {spec.name}():",
            f'    """{spec.description}"""',
        ]

        for i, step in enumerate(spec.setup_steps, 1):
            lines.append(f"    # Setup {i}: {step}")

        lines.append("    # Arrange")
        lines.append("    # TODO: Implement setup")
        lines.append("")
        lines.append("    # Act")
        lines.append("    # TODO: Execute the operation")
        lines.append("")
        lines.append("    # Assert")
        for assertion in spec.assertions:
            lines.append(f"    # {assertion}")
        lines.append("    pass  # TODO: Replace with actual assertions")

        return "\n".join(lines)

    def generate_to_file(
        self,
        requirement: str,
        output_dir: str | Path,
        test_type: TestType = TestType.UNIT,
    ) -> Path:
        """Generate a test case and write it to a file."""
        spec = self.generate(requirement, test_type)
        code = self.generate_test_code(spec)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"{spec.name}.py"
        file_path.write_text(code, encoding="utf-8")
        return file_path
