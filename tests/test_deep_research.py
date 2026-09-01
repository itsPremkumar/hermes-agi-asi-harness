"""Tests for Deep Research Engine — Phase 4: Frontend + Integration."""
import pytest
from src.deep_research.engine import DeepResearchEngine, ResearchSession, ResearchPhase
from src.deep_research.frontend import DeepResearchFrontend, UIComponent


class TestDeepResearchEngine:
    def test_create(self):
        engine = DeepResearchEngine()
        assert engine._sessions == {}

    def test_create_session(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety", depth=3)
        assert session.topic == "AI safety"
        assert session.depth == 3
        assert len(session.phases) > 0
        assert session.id in engine._sessions

    def test_get_session(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety")
        result = engine.get_session(session.id)
        assert result is not None
        assert result.topic == "AI safety"

    def test_list_sessions(self):
        engine = DeepResearchEngine()
        engine.create_session("AI safety")
        engine.create_session("Machine learning")
        sessions = engine.list_sessions()
        assert len(sessions) == 2

    def test_run_phase(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety")
        result = engine.run_phase(session.id, "planning")
        assert "plan_id" in result
        assert "sub_topics" in result

    def test_run_phase_not_found(self):
        engine = DeepResearchEngine()
        result = engine.run_phase("nonexistent", "planning")
        assert "error" in result

    def test_run_all_phases(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety", depth=1)
        results = engine.run_all_phases(session.id)
        assert len(results) == len(session.phases)
        assert all(phase.status == "completed" for phase in session.phases)

    def test_get_progress(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety", depth=1)
        progress = engine.get_progress(session.id)
        assert progress["total_phases"] == len(session.phases)
        assert progress["completed_phases"] == 0

    def test_get_progress_after_run(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety", depth=1)
        engine.run_all_phases(session.id)
        progress = engine.get_progress(session.id)
        assert progress["completed_phases"] == progress["total_phases"]
        assert progress["progress"] == 1.0

    def test_delete_session(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety")
        assert engine.delete_session(session.id) is True
        assert engine.get_session(session.id) is None

    def test_get_stats(self):
        engine = DeepResearchEngine()
        engine.create_session("AI safety")
        engine.create_session("Machine learning")
        stats = engine.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["pending"] == 2

    def test_get_stats_after_run(self):
        engine = DeepResearchEngine()
        session = engine.create_session("AI safety", depth=1)
        engine.run_all_phases(session.id)
        stats = engine.get_stats()
        assert stats["completed"] == 1


class TestResearchSession:
    def test_create(self):
        session = ResearchSession(id="s1", topic="AI safety", depth=3)
        assert session.id == "s1"
        assert session.topic == "AI safety"
        assert session.status == "pending"


class TestResearchPhase:
    def test_create(self):
        phase = ResearchPhase(id="p1", name="Planning", description="Create plan")
        assert phase.id == "p1"
        assert phase.status == "pending"
        assert phase.progress == 0.0


class TestDeepResearchFrontend:
    def test_create(self):
        frontend = DeepResearchFrontend()
        assert frontend._components == {}

    def test_create_topic_input(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_topic_input()
        assert component.component_type == "text_input"
        assert component.props["label"] == "Research Topic"

    def test_create_depth_selector(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_depth_selector()
        assert component.component_type == "select"
        assert len(component.props["options"]) == 5

    def test_create_progress_bar(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_progress_bar(progress=0.5)
        assert component.component_type == "progress_bar"
        assert component.props["progress"] == 0.5

    def test_create_phase_list(self):
        frontend = DeepResearchFrontend()
        phases = [{"id": "p1", "name": "Planning", "status": "completed"}]
        component = frontend.create_phase_list(phases)
        assert component.component_type == "list"
        assert len(component.children) == 1

    def test_create_results_view(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_results_view({"key": "value"})
        assert component.component_type == "results"
        assert component.props["data"] == {"key": "value"}

    def test_create_session_card(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_session_card({"id": "s1", "topic": "AI"})
        assert component.component_type == "card"
        assert component.props["topic"] == "AI"

    def test_get_component(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_topic_input()
        result = frontend.get_component(component.id)
        assert result is not None
        assert result.component_type == "text_input"

    def test_list_components(self):
        frontend = DeepResearchFrontend()
        frontend.create_topic_input()
        frontend.create_depth_selector()
        components = frontend.list_components()
        assert len(components) == 2

    def test_remove_component(self):
        frontend = DeepResearchFrontend()
        component = frontend.create_topic_input()
        assert frontend.remove_component(component.id) is True
        assert frontend.get_component(component.id) is None

    def test_render_dashboard(self):
        frontend = DeepResearchFrontend()
        dashboard = frontend.render_dashboard([{"id": "s1", "topic": "AI"}])
        assert dashboard["title"] == "Deep Research Dashboard"
        assert dashboard["total_sessions"] == 1

    def test_render_session_detail(self):
        frontend = DeepResearchFrontend()
        session = {"id": "s1", "topic": "AI safety", "phases": [], "result": {}}
        detail = frontend.render_session_detail(session)
        assert detail["title"] == "Session: AI safety"
        assert detail["session"] == session


class TestUIComponent:
    def test_create(self):
        component = UIComponent(id="c1", component_type="text_input")
        assert component.id == "c1"
        assert component.component_type == "text_input"
        assert component.children == []
