"""LangChain LLM wrapper and chat model integration."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from .errors import HarnessError

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM wrapper."""

    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout: float = 30.0
    api_key: str | None = None
    base_url: str | None = None


@dataclass
class ChatMessage:
    """A chat message."""

    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMResponse:
    """Response from an LLM."""

    def __init__(self, content: str, *, model: str = "", usage: dict[str, int] | None = None, metadata: dict[str, Any] | None = None) -> None:
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.metadata = metadata or {}
        self.id = str(uuid.uuid4())[:8]

    def __repr__(self) -> str:
        return f"<LLMResponse model={self.model} tokens={self.usage.get('total_tokens', '?')}>"


class ChatModel:
    """LangChain-style chat model wrapper."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self._call_count = 0
        self._total_tokens = 0

    def invoke(self, messages: str | list[ChatMessage]) -> LLMResponse:
        self._call_count += 1
        if isinstance(messages, str):
            messages = [ChatMessage(role="user", content=messages)]
        content = f"Response to: {messages[-1].content[:50]}..."
        usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        self._total_tokens += usage["total_tokens"]
        return LLMResponse(content=content, model=self.config.model_name, usage=usage)

    async def ainvoke(self, messages: str | list[ChatMessage]) -> LLMResponse:
        return self.invoke(messages)

    def generate(self, messages_list: list[list[ChatMessage]]) -> list[LLMResponse]:
        return [self.invoke(msgs) for msgs in messages_list]

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def total_tokens(self) -> int:
        return self._total_tokens


class OutputParser:
    """Base output parser."""

    def parse(self, text: str) -> Any:
        return text

    def get_format_instructions(self) -> str:
        return ""


class JsonOutputParser(OutputParser):
    """Parse JSON output."""

    def parse(self, text: str) -> Any:
        import json
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end + 1])
            raise HarnessError(f"Failed to parse JSON from: {text[:100]}")

    def get_format_instructions(self) -> str:
        return "Return output as JSON."


class StrOutputParser(OutputParser):
    """Parse string output."""

    def parse(self, text: str) -> str:
        return text.strip()


@dataclass
class ToolDefinition:
    """LangChain-style tool definition."""

    name: str
    description: str
    parameters: dict[str, Any]
    func: callable | None = None

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def invoke(self, **kwargs: Any) -> Any:
        if self.func is None:
            raise HarnessError(f"Tool {self.name} has no implementation")
        return self.func(**kwargs)


class ConversationBuffer:
    """LangChain-style conversation memory buffer."""

    def __init__(self, max_messages: int = 100) -> None:
        self.max_messages = max_messages
        self._messages: list[ChatMessage] = []

    def add_message(self, message: ChatMessage) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def add_user_message(self, content: str) -> None:
        self.add_message(ChatMessage(role="user", content=content))

    def add_ai_message(self, content: str) -> None:
        self.add_message(ChatMessage(role="assistant", content=content))

    @property
    def messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def to_string(self) -> str:
        return "\n".join(f"{m.role}: {m.content}" for m in self._messages)
