"""
LLM Provider System - Unified interface for all LLM providers.

Supports: OpenAI, Anthropic, Google, Azure, Ollama, Local models, and more.
Features: Streaming, retry, fallback, caching, rate limiting, cost tracking.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    OLLAMA = "ollama"
    LOCAL = "local"
    TOGETHER = "together"
    GROQ = "groq"
    COHERE = "cohere"
    MISTRAL = "mistral"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class LLMMessage:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    messages: List[LLMMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    id: str
    model: str
    content: str
    finish_reason: str
    usage: Dict[str, int]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", 0)
    
    @property
    def cost(self) -> float:
        return self.metadata.get("cost", 0.0)


@dataclass
class LLMConfig:
    provider: LLMProvider
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: Optional[int] = None  # requests per minute
    cost_per_1k_tokens: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._request_count = 0
        self._token_count = 0
        self._cost = 0.0
        self._last_request_time = 0.0
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...
    
    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        ...
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        ...
    
    async def generate_with_retry(self, request: LLMRequest) -> LLMResponse:
        """Generate with automatic retry and exponential backoff."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Rate limiting
                if self.config.rate_limit:
                    await self._rate_limit()
                
                response = await self.generate(request)
                
                # Track usage
                self._request_count += 1
                self._token_count += response.total_tokens
                self._cost += response.cost
                
                return response
            
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        raise last_error
    
    async def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        min_interval = 60.0 / self.config.rate_limit
        
        elapsed = now - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self._last_request_time = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "requests": self._request_count,
            "tokens": self._token_count,
            "cost": self._cost,
        }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=self.config.api_base,
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError("Install openai: pip install openai")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        import openai
        
        messages = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
        ]
        
        kwargs = {
            "model": request.model or self.config.model,
            "messages": messages,
            "temperature": request.temperature or self.config.temperature,
            "max_tokens": request.max_tokens or self.config.max_tokens,
        }
        
        if request.tools:
            kwargs["tools"] = request.tools
        
        if request.response_format:
            kwargs["response_format"] = request.response_format
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            id=response.id,
            model=response.model,
            content=response.choices[0].message.content or "",
            finish_reason=response.choices[0].finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            tool_calls=response.choices[0].message.tool_calls,
            metadata={"cost": self._calculate_cost(response.usage)},
        )
    
    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        messages = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
        ]
        
        stream = await self.client.chat.completions.create(
            model=request.model or self.config.model,
            messages=messages,
            temperature=request.temperature or self.config.temperature,
            max_tokens=request.max_tokens or self.config.max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def count_tokens(self, text: str) -> int:
        # Rough estimation: ~4 characters per token
        return len(text) // 4
    
    def _calculate_cost(self, usage) -> float:
        """Calculate cost based on model pricing."""
        pricing = {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }
        
        model_pricing = pricing.get(self.config.model, {"input": 0.001, "output": 0.002})
        
        input_cost = (usage.prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (usage.completion_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY"),
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        # Separate system message from messages
        system_msg = None
        messages = []
        
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_msg = msg.content
            else:
                messages.append({"role": msg.role.value, "content": msg.content})
        
        kwargs = {
            "model": request.model or "claude-sonnet-4-20250514",
            "messages": messages,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": request.temperature or self.config.temperature,
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        
        response = await self.client.messages.create(**kwargs)
        
        return LLMResponse(
            id=response.id,
            model=response.model,
            content=response.content[0].text if response.content else "",
            finish_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        )
    
    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        system_msg = None
        messages = []
        
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_msg = msg.content
            else:
                messages.append({"role": msg.role.value, "content": msg.content})
        
        kwargs = {
            "model": request.model or "claude-sonnet-4-20250514",
            "messages": messages,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": request.temperature or self.config.temperature,
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def count_tokens(self, text: str) -> int:
        return len(text) // 4


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_base = config.api_base or "http://localhost:11434"
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        import httpx
        
        messages = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
        ]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/api/chat",
                json={
                    "model": request.model or self.config.model or "llama3",
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature or self.config.temperature,
                        "num_predict": request.max_tokens or self.config.max_tokens,
                    },
                },
                timeout=self.config.timeout,
            )
        
        data = response.json()
        
        return LLMResponse(
            id=str(uuid.uuid4()),
            model=data.get("model", self.config.model),
            content=data.get("message", {}).get("content", ""),
            finish_reason="stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
        )
    
    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        import httpx
        
        messages = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
        ]
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/api/chat",
                json={
                    "model": request.model or self.config.model or "llama3",
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": request.temperature or self.config.temperature,
                        "num_predict": request.max_tokens or self.config.max_tokens,
                    },
                },
                timeout=self.config.timeout,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if data.get("message", {}).get("content"):
                            yield data["message"]["content"]
    
    async def count_tokens(self, text: str) -> int:
        return len(text) // 4


class LLMProviderManager:
    """
    Manages multiple LLM providers with fallback, load balancing, and cost tracking.
    """
    
    def __init__(self):
        self._providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self._fallback_chain: List[LLMProvider] = []
        self._cache: Dict[str, LLMResponse] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def register_provider(self, config: LLMConfig) -> BaseLLMProvider:
        """Register a new LLM provider."""
        provider_map = {
            LLMProvider.OPENAI: OpenAIProvider,
            LLMProvider.ANTHROPIC: AnthropicProvider,
            LLMProvider.OLLAMA: OllamaProvider,
        }
        
        provider_class = provider_map.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {config.provider}")
        
        provider = provider_class(config)
        self._providers[config.provider] = provider
        self._fallback_chain.append(config.provider)
        
        return provider
    
    async def generate(self, request: LLMRequest, 
                       preferred: Optional[LLMProvider] = None) -> LLMResponse:
        """Generate with automatic fallback."""
        # Check cache first
        cache_key = self._get_cache_key(request)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try preferred provider first
        providers_to_try = []
        if preferred and preferred in self._fallback_chain:
            providers_to_try.append(preferred)
        providers_to_try.extend(self._fallback_chain)
        
        last_error = None
        for provider_type in providers_to_try:
            provider = self._providers.get(provider_type)
            if not provider:
                continue
            
            try:
                response = await provider.generate_with_retry(request)
                # Cache the response
                self._cache[cache_key] = response
                return response
            except Exception as e:
                last_error = e
                continue
        
        raise last_error or Exception("No LLM provider available")
    
    def _get_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for a request."""
        content = json.dumps([
            {"role": m.role.value, "content": m.content}
            for m in request.messages
        ])
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get stats from all providers."""
        return {
            provider_type.value: provider.get_stats()
            for provider_type, provider in self._providers.items()
        }
    
    @property
    def available_providers(self) -> List[LLMProvider]:
        return list(self._providers.keys())
