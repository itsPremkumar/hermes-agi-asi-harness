"""LLM client for the benchmark harness.

Connects to the Hermes proxy (OpenAI-compatible) to generate predictions
for benchmark tasks. Supports any model available through the proxy.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    """Configuration for the LLM client."""
    base_url: str = "http://127.0.0.1:8645/v1"
    api_key: str = "hermes-proxy"
    model: str = "meituan/longcat-2.0:free"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str
    model: str
    tokens_used: int = 0
    duration: float = 0.0
    error: str = ""


class LLMClient:
    """OpenAI-compatible LLM client for benchmark predictions."""

    def __init__(self, config: LLMConfig | None = None):
        self._config = config or LLMConfig()

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Generate a response from the LLM."""
        start_time = time.time()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": self._config.model,
            "messages": messages,
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }

        try:
            req = urllib.request.Request(
                f"{self._config.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._config.api_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self._config.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            content = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("total_tokens", 0)

            return LLMResponse(
                content=content,
                model=result.get("model", self._config.model),
                tokens_used=tokens,
                duration=time.time() - start_time,
            )
        except urllib.error.URLError as e:
            return LLMResponse(
                content="",
                model=self._config.model,
                error=f"Connection error: {e}",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=self._config.model,
                error=str(e),
                duration=time.time() - start_time,
            )

    def generate_code(self, prompt: str, language: str = "python") -> LLMResponse:
        """Generate code for coding benchmarks."""
        system_prompt = f"""You are an expert {language} programmer. Generate clean, correct, well-documented code.
Follow best practices. Only output the code, no explanations."""
        return self.generate(system_prompt, prompt)

    def generate_reasoning(self, prompt: str) -> LLMResponse:
        """Generate reasoning for QA benchmarks."""
        system_prompt = """You are an expert reasoning assistant. Think step by step.
Provide clear, logical reasoning. Give the final answer at the end."""
        return self.generate(system_prompt, prompt)

    def generate_patch(self, prompt: str) -> LLMResponse:
        """Generate a git patch for SWE-bench."""
        system_prompt = """You are an expert software engineer. Generate a git patch that resolves the issue.
Output only the patch in unified diff format, starting with 'diff --git'."""
        return self.generate(system_prompt, prompt)

    def check_connection(self) -> bool:
        """Check if the LLM is reachable."""
        try:
            req = urllib.request.Request(
                f"{self._config.base_url}/models",
                headers={"Authorization": f"Bearer {self._config.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Benchmark-specific prompt builders
# ---------------------------------------------------------------------------

class PromptBuilder:
    """Builds prompts for different benchmark types."""

    @staticmethod
    def human_eval(task: Any) -> tuple[str, str]:
        """Build HumanEval prompt."""
        system = "You are an expert Python programmer. Write a correct implementation of the function described in the docstring. Output only the code."
        user = f"```python\n{task.prompt}\n```"
        return system, user

    @staticmethod
    def mbpp(task: Any) -> tuple[str, str]:
        """Build MBPP prompt."""
        system = "You are an expert Python programmer. Write a function that passes all the test cases. Output only the code."
        user = f"Task: {task.prompt}\n\nWrite the function:"
        return system, user

    @staticmethod
    def swe_bench(task: Any) -> tuple[str, str]:
        """Build SWE-bench prompt."""
        system = "You are an expert software engineer. Generate a git patch that resolves the issue. Output only the unified diff patch starting with 'diff --git'."
        repo = task.metadata.get("repo", "")
        problem = task.metadata.get("problem_statement", task.prompt)
        user = f"Repository: {repo}\n\nIssue:\n{problem}\n\nGenerate a patch:"
        return system, user

    @staticmethod
    def gaia(task: Any) -> tuple[str, str]:
        """Build GAIA prompt."""
        system = "You are an expert reasoning assistant. Think step by step and provide the final answer."
        user = task.prompt
        return system, user

    @staticmethod
    def terminal_bench(task: Any) -> tuple[str, str]:
        """Build Terminal-Bench prompt."""
        system = "You are an expert system administrator. Provide the exact commands needed. Output only the commands, one per line."
        user = task.prompt
        return system, user

    @staticmethod
    def gpqa(task: Any) -> tuple[str, str]:
        """Build GPQA prompt."""
        system = "You are an expert scientist. Think step by step and provide the correct answer choice."
        choices = task.metadata.get("choices", [])
        choices_str = "\n".join(choices) if choices else ""
        user = f"{task.prompt}\n\nChoices:\n{choices_str}\n\nAnswer:"
        return system, user


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "PromptBuilder",
]
