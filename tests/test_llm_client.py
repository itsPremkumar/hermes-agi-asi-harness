"""Tests for the LLM client integration."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.core_suites.llm_client import (
    LLMClient, LLMConfig, LLMResponse, PromptBuilder,
)
from benchmarks.core_suites import BenchmarkTask, BenchmarkType


class TestLLMConfig:
    def test_default_config(self):
        config = LLMConfig()
        assert config.base_url == "http://127.0.0.1:8645/v1"
        assert config.model == "meituan/longcat-2.0:free"
        assert config.max_tokens == 4096

    def test_custom_config(self):
        config = LLMConfig(base_url="http://localhost:8080/v1", model="custom/model")
        assert config.base_url == "http://localhost:8080/v1"
        assert config.model == "custom/model"


class TestLLMClient:
    def test_create_client(self):
        client = LLMClient()
        assert client._config is not None

    def test_check_connection(self):
        client = LLMClient()
        # Connection may or may not be available in test env
        result = client.check_connection()
        assert isinstance(result, bool)

    def test_generate(self):
        client = LLMClient()
        response = client.generate("You are a helpful assistant.", "Say hello.")
        assert isinstance(response, LLMResponse)
        # Response may be empty if no LLM available
        if response.error:
            assert response.content == ""
        else:
            assert response.content != ""

    def test_generate_code(self):
        client = LLMClient()
        response = client.generate_code("Write a function that adds two numbers.")
        assert isinstance(response, LLMResponse)

    def test_generate_reasoning(self):
        client = LLMClient()
        response = client.generate_reasoning("What is 2+2?")
        assert isinstance(response, LLMResponse)

    def test_generate_patch(self):
        client = LLMClient()
        response = client.generate_patch("Fix the bug in the add function.")
        assert isinstance(response, LLMResponse)


class TestPromptBuilder:
    def test_human_eval(self):
        task = BenchmarkTask(
            task_id="he1",
            benchmark=BenchmarkType.HUMAN_EVAL,
            prompt="def add(a, b):\n    '''Add two numbers.'''",
            ground_truth="def add(a, b): return a + b",
        )
        system, user = PromptBuilder.human_eval(task)
        assert "Python" in system
        assert "def add" in user

    def test_mbpp(self):
        task = BenchmarkTask(
            task_id="mb1",
            benchmark=BenchmarkType.MBPP,
            prompt="Write a function that adds two numbers.",
            ground_truth="def add(a,b): return a+b",
        )
        system, user = PromptBuilder.mbpp(task)
        assert "Python" in system
        assert "adds two numbers" in user

    def test_swe_bench(self):
        task = BenchmarkTask(
            task_id="sw1",
            benchmark=BenchmarkType.SWE_BENCH,
            prompt="Fix the bug.",
            ground_truth="diff --git a.py b.py",
            metadata={"repo": "test/repo", "problem_statement": "Bug in add function."},
        )
        system, user = PromptBuilder.swe_bench(task)
        assert "patch" in system.lower()
        assert "diff --git" in system
        assert "test/repo" in user

    def test_gaia(self):
        task = BenchmarkTask(
            task_id="ga1",
            benchmark=BenchmarkType.GAIA,
            prompt="What is the capital of France?",
            ground_truth="Paris",
        )
        system, user = PromptBuilder.gaia(task)
        assert "reasoning" in system.lower()
        assert "France" in user

    def test_terminal_bench(self):
        task = BenchmarkTask(
            task_id="tb1",
            benchmark=BenchmarkType.TERMINAL_BENCH,
            prompt="List all files in the current directory.",
            ground_truth="file1.txt",
        )
        system, user = PromptBuilder.terminal_bench(task)
        assert "commands" in system.lower()

    def test_gpqa(self):
        task = BenchmarkTask(
            task_id="gp1",
            benchmark=BenchmarkType.GPQA,
            prompt="What is E=mc^2?",
            ground_truth="A",
            metadata={"choices": ["A) Energy equals mass times speed of light squared", "B) None", "C) Both", "D) Neither"]},
        )
        system, user = PromptBuilder.gpqa(task)
        assert "scientist" in system.lower() or "expert" in system.lower()
        assert "E=mc^2" in user


class TestLLMResponse:
    def test_create_response(self):
        response = LLMResponse(content="Hello", model="test-model", tokens_used=10, duration=0.5)
        assert response.content == "Hello"
        assert response.model == "test-model"
        assert response.tokens_used == 10
        assert response.duration == 0.5
        assert response.error == ""

    def test_create_error_response(self):
        response = LLMResponse(content="", model="test-model", error="Connection failed")
        assert response.error == "Connection failed"
        assert response.content == ""
