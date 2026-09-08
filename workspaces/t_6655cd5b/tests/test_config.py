"""Tests for deepresearch.config."""
from __future__ import annotations

import os
import pytest

from deepresearch.config import ResearchConfig, DEFAULT_CONFIG


class TestResearchConfig:
    """Tests for ResearchConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = ResearchConfig()
        assert config.arxiv_max_results == 15
        assert config.pubmed_max_results == 15
        assert config.max_retries == 3
        assert config.request_timeout == 60

    def test_default_config_instance(self):
        """Test DEFAULT_CONFIG is a ResearchConfig."""
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, ResearchConfig)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ResearchConfig(arxiv_max_results=30, max_retries=5)
        assert config.arxiv_max_results == 30
        assert config.max_retries == 5

    def test_model_settings(self):
        """Test model settings contain expected values."""
        config = ResearchConfig()
        assert "laguna" in config.literature_model or "free" in config.literature_model
        assert "laguna" in config.hypothesis_model or "free" in config.hypothesis_model

    def test_pipeline_flags(self):
        """Test pipeline feature flags."""
        config = ResearchConfig()
        assert config.enable_simulation is True
        assert config.generate_latex is True
        assert config.min_papers == 10

    def test_memory_backend(self):
        """Test memory backend settings."""
        config = ResearchConfig()
        assert config.memory_backend == "sqlite"
        assert config.sqlite_path == "deepresearch_memory.db"

    def test_env_override(self, monkeypatch):
        """Test environment variable overrides via importlib.reload."""
        import importlib
        import deepresearch.config as config_mod
        monkeypatch.setenv("DR_LITERATURE_MODEL", "custom/model:lite")
        importlib.reload(config_mod)
        config = config_mod.ResearchConfig()
        assert config.literature_model == "custom/model:lite"
        importlib.reload(config_mod)
