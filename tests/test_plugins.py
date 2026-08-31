"""Tests for all 31 plugin capabilities."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from harness.plugins.perception import (
        VisionPlugin, AudioPlugin, TextPlugin, SensorPlugin, MultimodalPlugin, AttentionPlugin,
    )
    from harness.plugins.reasoning import (
        DeductivePlugin, InductivePlugin, AbductivePlugin, CausalPlugin,
        AnalogicalPlugin, PlanningPlugin, DecisionPlugin,
    )
    from harness.plugins.action import (
        ToolUsePlugin, CodeGenPlugin, WebPlugin, FileSystemPlugin, ShellPlugin, APIPlugin,
    )
    from harness.plugins.learning import (
        RLPlugin, SupervisedPlugin, UnsupervisedPlugin, MetaLearningPlugin,
        TransferLearningPlugin, CurriculumPlugin,
    )
    from harness.plugins.safety import (
        GuardrailsPlugin, BiasDetectionPlugin, AdversarialDefensePlugin,
        PrivacyPlugin, ExplainabilityPlugin, AlignmentPlugin,
    )
    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False

import pytest

pytestmark = pytest.mark.skipif(not PLUGINS_AVAILABLE, reason="harness.plugins not available in this build")


# ============== Perception Tests ==============

class TestVisionPlugin:
    def test_create(self):
        p = VisionPlugin()
        assert p.id == "perception.vision"
        assert "vision" in p.metadata.provides

    def test_process(self):
        p = VisionPlugin()
        result = p.process("image_data")
        assert "objects" in result

    def test_health_check(self):
        p = VisionPlugin()
        p.on_load()
        result = p.health_check()
        assert result["healthy"] is True


class TestAudioPlugin:
    def test_create(self):
        p = AudioPlugin()
        assert p.id == "perception.audio"

    def test_transcribe(self):
        p = AudioPlugin()
        result = p.transcribe("audio_data")
        assert "text" in result

    def test_health_check(self):
        p = AudioPlugin()
        result = p.health_check()
        assert result["healthy"] is True


class TestTextPlugin:
    def test_create(self):
        p = TextPlugin()
        assert p.id == "perception.text"

    def test_parse(self):
        p = TextPlugin()
        result = p.parse("hello world")
        assert "tokens" in result

    def test_health_check(self):
        p = TextPlugin()
        result = p.health_check()
        assert result["healthy"] is True


class TestSensorPlugin:
    def test_create(self):
        p = SensorPlugin()
        assert p.id == "perception.sensor"

    def test_register_sensor(self):
        p = SensorPlugin()
        p.register_sensor("s1", "temperature")
        assert len(p._sensors) == 1

    def test_read(self):
        p = SensorPlugin()
        p.register_sensor("s1", "temperature")
        result = p.read("s1")
        assert "value" in result

    def test_read_not_found(self):
        p = SensorPlugin()
        result = p.read("nonexistent")
        assert "error" in result


class TestMultimodalPlugin:
    def test_create(self):
        p = MultimodalPlugin()
        assert p.id == "perception.multimodal"
        assert "perception.vision" in p.metadata.dependencies

    def test_fuse(self):
        p = MultimodalPlugin()
        result = p.fuse({"vision": "img", "audio": "snd"})
        assert result["fused"] is True


class TestAttentionPlugin:
    def test_create(self):
        p = AttentionPlugin()
        assert p.id == "perception.attention"

    def test_attend(self):
        p = AttentionPlugin()
        result = p.attend(["a", "b", "c"])
        assert result["focused"] == "a"

    def test_attend_empty(self):
        p = AttentionPlugin()
        result = p.attend([])
        assert result["focused"] is None


# ============== Reasoning Tests ==============

class TestDeductivePlugin:
    def test_create(self):
        p = DeductivePlugin()
        assert p.id == "reasoning.deductive"

    def test_add_rule(self):
        p = DeductivePlugin()
        p.add_rule({"if": "A", "then": "B"})
        assert len(p._rules) == 1

    def test_deduce(self):
        p = DeductivePlugin()
        result = p.deduce(["A"])
        assert result["valid"] is True


class TestInductivePlugin:
    def test_create(self):
        p = InductivePlugin()
        assert p.id == "reasoning.inductive"

    def test_add_example(self):
        p = InductivePlugin()
        p.add_example("example1")
        assert len(p._examples) == 1

    def test_generalize(self):
        p = InductivePlugin()
        result = p.generalize()
        assert "pattern" in result


class TestAbductivePlugin:
    def test_create(self):
        p = AbductivePlugin()
        assert p.id == "reasoning.abductive"

    def test_explain(self):
        p = AbductivePlugin()
        result = p.explain("observation")
        assert "explanation" in result


class TestCausalPlugin:
    def test_create(self):
        p = CausalPlugin()
        assert p.id == "reasoning.causal"

    def test_add_cause(self):
        p = CausalPlugin()
        p.add_cause("rain", "wet_ground")
        assert "rain" in p._causal_graph

    def test_find_causes(self):
        p = CausalPlugin()
        p.add_cause("rain", "wet_ground")
        result = p.find_causes("wet_ground")
        assert "rain" in result["causes"]


class TestAnalogicalPlugin:
    def test_create(self):
        p = AnalogicalPlugin()
        assert p.id == "reasoning.analogical"

    def test_map(self):
        p = AnalogicalPlugin()
        result = p.map("source_domain", "target_domain")
        assert "mapping" in result


class TestPlanningPlugin:
    def test_create(self):
        p = PlanningPlugin()
        assert p.id == "reasoning.planning"

    def test_create_plan(self):
        p = PlanningPlugin()
        result = p.create_plan("build X")
        assert "steps" in result


class TestDecisionPlugin:
    def test_create(self):
        p = DecisionPlugin()
        assert p.id == "reasoning.decision"

    def test_decide(self):
        p = DecisionPlugin()
        result = p.decide([{"value": 10}, {"value": 20}])
        assert result["chosen"]["value"] == 20

    def test_decide_empty(self):
        p = DecisionPlugin()
        result = p.decide([])
        assert "error" in result


# ============== Action Tests ==============

class TestToolUsePlugin:
    def test_create(self):
        p = ToolUsePlugin()
        assert p.id == "action.tool_use"

    def test_register_tool(self):
        p = ToolUsePlugin()
        p.register_tool("calculator", object())
        assert "calculator" in p._tools

    def test_invoke(self):
        p = ToolUsePlugin()
        p.register_tool("calc", object())
        result = p.invoke("calc", x=1, y=2)
        assert result["result"] == "success"

    def test_invoke_not_found(self):
        p = ToolUsePlugin()
        result = p.invoke("nonexistent")
        assert "error" in result


class TestCodeGenPlugin:
    def test_create(self):
        p = CodeGenPlugin()
        assert p.id == "action.code_gen"

    def test_generate(self):
        p = CodeGenPlugin()
        result = p.generate("sort a list")
        assert "code" in result

    def test_languages(self):
        p = CodeGenPlugin()
        p.set_config({"languages": ["python", "javascript"]})
        p.on_init()
        assert "javascript" in p._languages


class TestWebPlugin:
    def test_create(self):
        p = WebPlugin()
        assert p.id == "action.web"

    def test_browse(self):
        p = WebPlugin()
        result = p.browse("https://example.com")
        assert result["status"] == 200

    def test_search(self):
        p = WebPlugin()
        result = p.search("query")
        assert "results" in result


class TestFileSystemPlugin:
    def test_create(self):
        p = FileSystemPlugin()
        assert p.id == "action.filesystem"

    def test_read(self):
        p = FileSystemPlugin()
        result = p.read("/path/to/file")
        assert "content" in result

    def test_write(self):
        p = FileSystemPlugin()
        result = p.write("/path", "content")
        assert result["written"] is True


class TestShellPlugin:
    def test_create(self):
        p = ShellPlugin()
        assert p.id == "action.shell"

    def test_execute(self):
        p = ShellPlugin()
        result = p.execute("ls -la")
        assert "output" in result


class TestAPIPlugin:
    def test_create(self):
        p = APIPlugin()
        assert p.id == "action.api"

    def test_register_endpoint(self):
        p = APIPlugin()
        p.register_endpoint("users", "https://api.example.com/users")
        assert "users" in p._endpoints

    def test_call(self):
        p = APIPlugin()
        p.register_endpoint("users", "https://api.example.com/users")
        result = p.call("users", method="GET")
        assert result["status"] == 200


# ============== Learning Tests ==============

class TestRLPlugin:
    def test_create(self):
        p = RLPlugin()
        assert p.id == "learning.rl"

    def test_act(self):
        p = RLPlugin()
        result = p.act("state1")
        assert "action" in result

    def test_learn(self):
        p = RLPlugin()
        result = p.learn("state", "action", 1.0, "next_state")
        assert result["learned"] is True
        assert p._episodes == 1


class TestSupervisedPlugin:
    def test_create(self):
        p = SupervisedPlugin()
        assert p.id == "learning.supervised"

    def test_train(self):
        p = SupervisedPlugin()
        result = p.train([1, 2, 3])
        assert result["trained"] is True

    def test_predict(self):
        p = SupervisedPlugin()
        result = p.predict("input")
        assert "prediction" in result


class TestUnsupervisedPlugin:
    def test_create(self):
        p = UnsupervisedPlugin()
        assert p.id == "learning.unsupervised"

    def test_cluster(self):
        p = UnsupervisedPlugin()
        result = p.cluster([1, 2, 3, 4], n_clusters=2)
        assert len(result["clusters"]) == 2


class TestMetaLearningPlugin:
    def test_create(self):
        p = MetaLearningPlugin()
        assert p.id == "learning.meta"

    def test_adapt(self):
        p = MetaLearningPlugin()
        result = p.adapt("task1")
        assert result["adapted"] is True


class TestTransferLearningPlugin:
    def test_create(self):
        p = TransferLearningPlugin()
        assert p.id == "learning.transfer"

    def test_transfer(self):
        p = TransferLearningPlugin()
        result = p.transfer("source", "target")
        assert result["transferred"] is True


class TestCurriculumPlugin:
    def test_create(self):
        p = CurriculumPlugin()
        assert p.id == "learning.curriculum"

    def test_next_lesson(self):
        p = CurriculumPlugin()
        result = p.next_lesson()
        assert "lesson" in result

    def test_report_result(self):
        p = CurriculumPlugin()
        result = p.report_result("lesson1", True)
        assert result["progressed"] is True


# ============== Safety Tests ==============

class TestGuardrailsPlugin:
    def test_create(self):
        p = GuardrailsPlugin()
        assert p.id == "safety.guardrails"

    def test_add_rule(self):
        p = GuardrailsPlugin()
        p.add_rule({"action": "block", "condition": "x > 10"})
        assert len(p._rules) == 1

    def test_check(self):
        p = GuardrailsPlugin()
        result = p.check("some_action")
        assert result["allowed"] is True


class TestBiasDetectionPlugin:
    def test_create(self):
        p = BiasDetectionPlugin()
        assert p.id == "safety.bias_detection"

    def test_analyze(self):
        p = BiasDetectionPlugin()
        result = p.analyze("data")
        assert "bias_detected" in result


class TestAdversarialDefensePlugin:
    def test_create(self):
        p = AdversarialDefensePlugin()
        assert p.id == "safety.adversarial"

    def test_detect(self):
        p = AdversarialDefensePlugin()
        result = p.detect("input")
        assert "threat_detected" in result


class TestPrivacyPlugin:
    def test_create(self):
        p = PrivacyPlugin()
        assert p.id == "safety.privacy"

    def test_redact(self):
        p = PrivacyPlugin()
        result = p.redact("Contact: test@example.com")
        assert "redacted" in result

    def test_pii_types(self):
        p = PrivacyPlugin()
        p.set_config({"pii_types": ["email", "phone"]})
        p.on_init()
        assert "phone" in p._pii_types


class TestExplainabilityPlugin:
    def test_create(self):
        p = ExplainabilityPlugin()
        assert p.id == "safety.explainability"

    def test_explain(self):
        p = ExplainabilityPlugin()
        result = p.explain("decision")
        assert "explanation" in result


class TestAlignmentPlugin:
    def test_create(self):
        p = AlignmentPlugin()
        assert p.id == "safety.alignment"

    def test_check_alignment(self):
        p = AlignmentPlugin()
        result = p.check_alignment("action")
        assert result["aligned"] is True
