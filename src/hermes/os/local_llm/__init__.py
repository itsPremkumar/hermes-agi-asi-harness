"""
Local LLM Runtime — Atomic Agent Pattern
=========================================
TurboQuant llama.cpp + GBNF grammar enforcement for valid tool calls.
"""

from .local_llm import (
    LocalLLMRuntime,
    LlamaCppEngine,
    LLMConfig,
    GBNFCompiler,
    GBNFGrammar,
    COMMON_GRAMMARS,
    create_local_llm,
    create_hermes_local_llm,
)

__all__ = [
    "LocalLLMRuntime",
    "LlamaCppEngine",
    "LLMConfig",
    "GBNFCompiler",
    "GBNFGrammar",
    "COMMON_GRAMMARS",
    "create_local_llm",
    "create_hermes_local_llm",
]