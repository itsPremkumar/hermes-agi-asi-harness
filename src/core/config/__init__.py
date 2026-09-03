"""Configuration System - YAML-based config with env overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "llama3"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    max_retries: int = 3

@dataclass
class DatabaseConfig:
    url: str = "sqlite+aiosqlite:///hermes_agi.db"
    echo: bool = False

@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

@dataclass
class SecurityConfig:
    enabled: bool = True
    sandbox: bool = True
    max_file_size_mb: int = 10

@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    extra: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> Config:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            llm=LLMConfig(**data.get("llm", {})),
            database=DatabaseConfig(**data.get("database", {})),
            api=APIConfig(**data.get("api", {})),
            security=SecurityConfig(**data.get("security", {})),
            extra=data.get("extra", {}),
        )
    
    @classmethod
    def from_env(cls) -> Config:
        config = cls()
        if os.getenv("LLM_PROVIDER"): config.llm.provider = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_MODEL"): config.llm.model = os.getenv("LLM_MODEL")
        if os.getenv("OPENAI_API_KEY"): config.llm.api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("DATABASE_URL"): config.database.url = os.getenv("DATABASE_URL")
        if os.getenv("API_PORT"): config.api.port = int(os.getenv("API_PORT"))
        return config

def load_config(path: str | None = None) -> Config:
    config = Config()
    if path and Path(path).exists():
        config.merge(Config.from_yaml(path))
    config.merge(Config.from_env())
    return config
    
    def merge(self, other: Config):
        for f in self.__dataclass_fields__:
            v = getattr(other, f)
            if v and v != getattr(self, f):
                setattr(self, f, v)
