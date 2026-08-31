"""Tests for llm.py — LangChain LLM Wrapper."""

from __future__ import annotations


from src.harness.llm import (
    LLMConfig,
    LLMResponse,
    ChatMessage,
    ChatModel,
    OutputParser,
    JsonOutputParser,
    StrOutputParser,
    ToolDefinition,
    ConversationBuffer,
)


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_defaults(self):
        config = LLMConfig()
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.7

    def test_custom(self):
        config = LLMConfig(model_name="custom", temperature=0.5)
        assert config.model_name == "custom"
        assert config.temperature == 0.5


class TestChatMessage:
    """Tests for ChatMessage."""

    def test_create(self):
        msg = ChatMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"


class TestLLMResponse:
    """Tests for LLMResponse."""

    def test_create(self):
        resp = LLMResponse(content="test")
        assert resp.content == "test"
        assert resp.id is not None

    def test_with_usage(self):
        resp = LLMResponse(content="test", usage={"total_tokens": 42})
        assert resp.usage["total_tokens"] == 42


class TestChatModel:
    """Tests for ChatModel."""

    def test_invoke_string(self):
        model = ChatModel()
        resp = model.invoke("hello")
        assert isinstance(resp, LLMResponse)

    def test_invoke_messages(self):
        model = ChatModel()
        messages = [ChatMessage(role="user", content="hi")]
        resp = model.invoke(messages)
        assert isinstance(resp, LLMResponse)

    def test_call_count(self):
        model = ChatModel()
        model.invoke("test")
        model.invoke("test2")
        assert model.call_count == 2


class TestOutputParser:
    """Tests for OutputParser."""

    def test_parse(self):
        parser = OutputParser()
        assert parser.parse("hello") == "hello"


class TestJsonOutputParser:
    """Tests for JsonOutputParser."""

    def test_parse_valid_json(self):
        parser = JsonOutputParser()
        result = parser.parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_with_extra_text(self):
        parser = JsonOutputParser()
        result = parser.parse('prefix {"key": "value"} suffix')
        assert result == {"key": "value"}


class TestStrOutputParser:
    """Tests for StrOutputParser."""

    def test_parse(self):
        parser = StrOutputParser()
        assert parser.parse("  hello  ") == "hello"


class TestToolDefinition:
    """Tests for ToolDefinition."""

    def test_to_schema(self):
        td = ToolDefinition("test", "A tool", {"type": "object"})
        schema = td.to_schema()
        assert schema["name"] == "test"

    def test_invoke(self):
        td = ToolDefinition("test", "A tool", {}, func=lambda: "result")
        assert td.invoke() == "result"


class TestConversationBuffer:
    """Tests for ConversationBuffer."""

    def test_add_message(self):
        buf = ConversationBuffer()
        buf.add_message(ChatMessage(role="user", content="hi"))
        assert len(buf.messages) == 1

    def test_add_user_message(self):
        buf = ConversationBuffer()
        buf.add_user_message("hello")
        assert buf.messages[0].role == "user"

    def test_clear(self):
        buf = ConversationBuffer()
        buf.add_user_message("hello")
        buf.clear()
        assert len(buf.messages) == 0

    def test_to_string(self):
        buf = ConversationBuffer()
        buf.add_user_message("hi")
        buf.add_ai_message("hello")
        s = buf.to_string()
        assert "user" in s
        assert "assistant" in s
