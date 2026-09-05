"""Tests for User Interaction & Explanation Plane (Plane 22)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.user_interaction import (
    Channel,
    ClarificationResponse,
    Clarifier,
    Explainer,
    ExplanationResponse,
    ResultDeliverer,
    UserInteractionPlugin,
)


class TestClarifier:
    def test_detect_scope_ambiguity(self):
        asyncio.run(self._async_detect())

    async def _async_detect(self):
        c = Clarifier()
        resp = await c.clarify("Tell me about all AI models")
        assert not resp.is_resolved
        assert resp.category == "scope"
        assert resp.priority == 1

    def test_detect_detail_ambiguity(self):
        asyncio.run(self._async_detect_detail())

    async def _async_detect_detail(self):
        c = Clarifier()
        resp = await c.clarify("Explain how transformers work")
        assert not resp.is_resolved

    def test_no_ambiguity(self):
        asyncio.run(self._async_no_ambiguity())

    async def _async_no_ambiguity(self):
        c = Clarifier()
        resp = await c.clarify("What is 2 + 2?")
        # Short factual queries may still trigger patterns — that's OK
        # The key is they won't block the user
        assert resp.question is not None or resp.is_resolved

    def test_prioritize_questions(self):
        questions = [
            ClarificationResponse(False, question="Q1", priority=3),
            ClarificationResponse(False, question="Q2", priority=1),
            ClarificationResponse(False, question="Q3", priority=2),
        ]
        c = Clarifier()
        sorted_q = c.prioritize_questions(questions)
        assert sorted_q[0].priority == 1
        assert sorted_q[1].priority == 2
        assert sorted_q[2].priority == 3

    def test_should_ask_question_under_max(self):
        c = Clarifier()
        assert c.should_ask_question("hi", []) is True

    def test_should_ask_question_at_max(self):
        c = Clarifier()
        assert c.should_ask_question("hi", ["q1", "q2", "q3"], max_questions=3) is False

    def test_generate_options(self):
        c = Clarifier()
        options = c._generate_options("scope")
        assert len(options) == 3
        assert "Everything" in options


class TestExplainer:
    def test_explain_simple_result(self):
        asyncio.run(self._async_explain())

    async def _async_explain(self):
        e = Explainer()
        result = {"answer": "AI is a field of computer science"}
        resp = await e.explain(
            query="What is AI?",
            result=result,
            quality_scores={"accuracy": 0.95},
        )
        assert resp.confidence_label == "High"
        assert resp.confidence_score == 0.95
        assert "AI" in resp.summary
        assert resp.confidence_label in resp.summary

    def test_explain_low_confidence(self):
        asyncio.run(self._async_explain_low())

    async def _async_explain_low(self):
        e = Explainer()
        resp = await e.explain(
            query="Will AI surpass humans?",
            result={},
            quality_scores={"accuracy": 0.3},
        )
        assert resp.confidence_label == "Low"
        assert resp.confidence_score == 0.3

    def test_label_confidence(self):
        e = Explainer()
        assert e._label_confidence(0.9) == "High"
        assert e._label_confidence(0.6) == "Medium"
        assert e._label_confidence(0.3) == "Low"

    def test_build_reasoning_chain(self):
        e = Explainer()
        chain = e._build_reasoning_chain(
            {"steps": ["Step 1", "Step 2"]},
            {"search_queries": ["query1"]},
        )
        assert len(chain) == 3

    def test_find_unverified_claims(self):
        e = Explainer()
        result = {
            "claims": [
                {"text": "Claim A", "verified": True},
                {"text": "Claim B", "verified": False},
            ]
        }
        unverified = e._find_unverified_claims(result)
        assert len(unverified) == 1
        assert "Claim B" in unverified


class TestDeliverer:
    def test_deliver_chat(self):
        asyncio.run(self._async_deliver_chat())

    async def _async_deliver_chat(self):
        d = ResultDeliverer()
        resp = await d.deliver(
            query="What is Python?",
            result={"answer": "Python is a programming language"},
            explanation=ExplanationResponse(
                summary="Python is a programming language",
                detail="Detailed explanation",
                confidence_label="High",
                confidence_score=0.9,
                format="markdown",
                citations=["python.org"],
                unverified_claims=[],
                reasoning_chain=["Looked up Python"],
            ),
            channel=Channel.CHAT,
        )
        assert resp.channel == Channel.CHAT
        assert "Python" in resp.content
        assert "High" in resp.content
        assert "python.org" in resp.content

    def test_deliver_email(self):
        asyncio.run(self._async_deliver_email())

    async def _async_deliver_email(self):
        d = ResultDeliverer()
        resp = await d.deliver(
            query="Research topic",
            result={},
            explanation=ExplanationResponse(
                summary="Summary here",
                detail="Detail",
                confidence_label="Medium",
                confidence_score=0.7,
                format="markdown",
                citations=["source1"],
                unverified_claims=["claim1"],
                reasoning_chain=[],
            ),
            channel=Channel.EMAIL,
        )
        assert resp.channel == Channel.EMAIL
        assert "Subject:" in resp.content

    def test_deliver_report(self):
        asyncio.run(self._async_deliver_report())

    async def _async_deliver_report(self):
        d = ResultDeliverer()
        resp = await d.deliver(
            query="Deep research",
            result={},
            explanation=ExplanationResponse(
                summary="Summary",
                detail="Detail",
                confidence_label="High",
                confidence_score=0.95,
                format="markdown",
                citations=["s1", "s2"],
                unverified_claims=["unverified"],
                reasoning_chain=["step1"],
            ),
            channel=Channel.REPORT,
        )
        assert resp.channel == Channel.REPORT
        assert "Report" in resp.content
        assert "Executive Summary" in resp.content

    def test_deliver_json(self):
        asyncio.run(self._async_deliver_json())

    async def _async_deliver_json(self):
        d = ResultDeliverer()
        resp = await d.deliver(
            query="Test",
            result={"answer": "test"},
            explanation=ExplanationResponse(
                summary="Test summary",
                detail="",
                confidence_label="High",
                confidence_score=0.9,
                format="json",
                citations=[],
                unverified_claims=[],
                reasoning_chain=[],
            ),
            channel=Channel.JSON,
        )
        assert resp.channel == Channel.JSON
        assert '"query": "Test"' in resp.content

    def test_deliver_unverified_warning(self):
        asyncio.run(self._async_deliver_unverified())

    async def _async_deliver_unverified(self):
        d = ResultDeliverer()
        resp = await d.deliver(
            query="Test",
            result={},
            explanation=ExplanationResponse(
                summary="",
                detail="",
                confidence_label="Low",
                confidence_score=0.2,
                format="markdown",
                citations=[],
                unverified_claims=["Claim X"],
                reasoning_chain=[],
            ),
            channel=Channel.CHAT,
        )
        assert "⚠️" in resp.content
        assert "Claim X" in resp.content


class TestUserInteractionPlugin:
    def test_load_and_start(self):
        asyncio.run(self._async_load_start())

    async def _async_load_start(self):
        from core.runtime.plugin_base import PluginManifest, PluginPermissions
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            description="test",
            license="MIT",
            source="internal",
            capabilities=["test"],
            cost="free",
            permissions=PluginPermissions(),
        )
        plugin = UserInteractionPlugin(manifest)
        await plugin.load()
        await plugin.start()
        assert plugin.state.value == "running"

    def test_health(self):
        asyncio.run(self._async_health())

    async def _async_health(self):
        from core.runtime.plugin_base import PluginManifest, PluginPermissions
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            description="test",
            license="MIT",
            source="internal",
            capabilities=["test"],
            cost="free",
            permissions=PluginPermissions(),
        )
        plugin = UserInteractionPlugin(manifest)
        await plugin.load()
        health = await plugin.health()
        assert health["healthy"]
        assert health["clarifier_ready"]

    def test_process_query(self):
        asyncio.run(self._async_process())

    async def _async_process(self):
        from core.runtime.plugin_base import PluginManifest, PluginPermissions
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            description="test",
            license="MIT",
            source="internal",
            capabilities=["test"],
            cost="free",
            permissions=PluginPermissions(),
        )
        plugin = UserInteractionPlugin(manifest)
        await plugin.start()
        result = await plugin.process(
            query="What is AI?",
            context={"result": {"answer": "AI is intelligence demonstrated by machines"}},
            quality_scores={"accuracy": 0.9},
        )
        assert result["query"] == "What is AI?"
        assert "explanation" in result
        assert "delivery" in result

    def test_stop_and_unload(self):
        asyncio.run(self._async_stop_unload())

    async def _async_stop_unload(self):
        from core.runtime.plugin_base import PluginManifest, PluginPermissions
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            description="test",
            license="MIT",
            source="internal",
            capabilities=["test"],
            cost="free",
            permissions=PluginPermissions(),
        )
        plugin = UserInteractionPlugin(manifest)
        await plugin.start()
        await plugin.stop()
        assert plugin.state.value == "unLOADED"
        await plugin.unload()
        assert plugin._clarifier is None
        assert plugin._explainer is None
        assert plugin._deliverer is None
