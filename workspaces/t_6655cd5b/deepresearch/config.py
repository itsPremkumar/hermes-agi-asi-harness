"""
Configuration for the DeepResearch engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class ResearchConfig:
    """Configuration for running the research pipeline."""

    # API settings
    arxiv_email: str = os.environ.get("ARXIV_EMAIL", "research@deepresearch.dev")
    arxiv_max_results: int = 15
    pubmed_max_results: int = 15

    # Model settings (free-tier aware)
    literature_model: str = os.environ.get(
        "DR_LITERATURE_MODEL", "poolside/laguna-s-2.1:free"
    )
    hypothesis_model: str = os.environ.get(
        "DR_HYPOTHESIS_MODEL", "poolside/laguna-s-2.1:free"
    )
    experiment_model: str = os.environ.get(
        "DR_EXPERIMENT_MODEL", "poolside/laguna-s-2.1:free"
    )
    paper_model: str = os.environ.get(
        "DR_PAPER_MODEL", "poolside/laguna-s-2.1:free"
    )

    # Retry / budget
    max_retries: int = 3
    request_timeout: int = 60

    # Pipeline flags
    enable_simulation: bool = True  # Use LLM sim for experiment outcomes
    generate_latex: bool = True
    min_papers: int = 10

    # Memory backend
    memory_backend: str = os.environ.get("DR_MEMORY_BACKEND", "sqlite")
    sqlite_path: str = os.environ.get(
        "DR_SQLITE_PATH", "deepresearch_memory.db"
    )


DEFAULT_CONFIG = ResearchConfig()
