"""Tests for all 31 plugin capabilities."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.plugins.action import (
    APIPlugin,
    CodeGenPlugin,
    FileSystemPlugin,
    ShellPlugin,
    ToolUsePlugin,
    WebPlugin,
)
from harness.plugins.learning import (
    CurriculumPlugin,
    MetaLearningPlugin,
    RLPlugin,
    SupervisedPlugin,
    TransferLearningPlugin,
    UnsupervisedPlugin,
)
from harness.plugins.perception import (
    AttentionPlugin,
    AudioPlugin,
    MultimodalPlugin,
    SensorPlugin,
    TextPlugin,
    VisionPlugin,
)
from harness.plugins.reasoning import (
    AbductivePlugin,
    AnalogicalPlugin,
    CausalPlugin,
    DecisionPlugin,
    DeductivePlugin,
    InductivePlugin,
    PlanningPlugin,
)
from harness.plugins.safety import (
    AdversarialDefensePlugin,
    AlignmentPlugin,
    BiasDetectionPlugin,
    ExplainabilityPlugin,
    GuardrailsPlugin,
    PrivacyPlugin,
)

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
        assert result["healthy"] is False


class TestTextPlugin:
    def test_create(self):
        p = TextPlugin()
        assert p.id == "perception.text"

    def test_process(self):
        p = TextPlugin()
        result = p.process("hello world")
        assert "tokens" in result

    def test_health_check(self):
        p = TextPlugin()
        result = p.health_check()
        assert result["healthy"] is False


class TestSensorPlugin:
    def test_create(self):
        p = SensorPlugin()
        assert p.id == "perception.sensor"

    def test_read(self):
        p = SensorPlugin()
        result = p.read()
        assert "temperature" in result


class TestMultimodalPlugin:
    def test_create(self):
        p = MultimodalPlugin()
        assert p.id == "perception.multimodal"

    def test_fuse(self):
        p = MultimodalPlugin()
        result = p.fuse(["vision", "audio"])
        assert result["fused"] is True


class TestAttentionPlugin:
    def test_create(self):
        p = AttentionPlugin()
        assert p.id == "perception.attention"

    def test_attend(self):
        p = AttentionPlugin()
        result = p.attend("data")
        assert "salience" in result


# ============== Reasoning Tests ==============

class TestDeductivePlugin:
    def test_create(self):
        p = DeductivePlugin()
        assert p.id == "reasoning.deductive"

    def test_deduce(self):
        p = DeductivePlugin()
        result = p.deduce(["A", "B"])
        assert "conclusion" in result


class TestInductivePlugin:
    def test_create(self):
        p = InductivePlugin()
        assert p.id == "reasoning.inductive"

    def test_generalize(self):
        p = InductivePlugin()
        result = p.generalize(["ex1", "ex2"])
        assert "rule" in result


class TestAbductivePlugin:
    def test_create(self):
        p = AbductivePlugin()
        assert p.id == "reasoning.abductive"

    def test_explain(self):
        p = AbductivePlugin()
        result = p.explain("observation")
        assert "hypothesis" in result


class TestCausalPlugin:
    def test_create(self):
        p = CausalPlugin()
        assert p.id == "reasoning.causal"

    def test_intervene(self):
        p = CausalPlugin()
        result = p.intervene("X", 1.0)
        assert "effect" in result


class TestAnalogicalPlugin:
    def test_create(self):
        p = AnalogicalPlugin()
        assert p.id == "reasoning.analogical"

    def test_map(self):
        p = AnalogicalPlugin()
        result = p.map("source", "target")
        assert "mapping" in result


class TestPlanningPlugin:
    def test_create(self):
        p = PlanningPlugin()
        assert p.id == "reasoning.planning"

    def test_plan(self):
        p = PlanningPlugin()
        result = p.plan("goal1")
        assert "steps" in result


class TestDecisionPlugin:
    def test_create(self):
        p = DecisionPlugin()
        assert p.id == "reasoning.decision"

    def test_decide(self):
        p = DecisionPlugin()
        result = p.decide(["opt1", "opt2"])
        assert "choice" in result


# ============== Action Tests ==============

class TestToolUsePlugin:
    def test_create(self):
        p = ToolUsePlugin()
        assert p.id == "action.tool_use"

    def test_execute(self):
        p = ToolUsePlugin()
        result = p.execute("tool1", {"arg": "val"})
        assert "result" in result


class TestCodeGenPlugin:
    def test_create(self):
        p = CodeGenPlugin()
        assert p.id == "action.code_gen"

    def test_generate(self):
        p = CodeGenPlugin()
        result = p.generate("sort a list")
        assert "code" in result


class TestWebPlugin:
    def test_create(self):
        p = WebPlugin()
        assert p.id == "action.web"

    def test_fetch(self):
        p = WebPlugin()
        result = p.fetch("http://example.com")
        assert "status" in result


class TestFileSystemPlugin:
    def test_create(self):
        p = FileSystemPlugin()
        assert p.id == "action.filesystem"

    def test_read(self):
        p = FileSystemPlugin()
        result = p.read("/tmp/test.txt")
        assert "content" in result

    def test_write(self):
        p = FileSystemPlugin()
        result = p.write("/tmp/test.txt", "data")
        assert result["written"] is True


class TestShellPlugin:
    def test_create(self):
        p = ShellPlugin()
        assert p.id == "action.shell"

    def test_run(self):
        p = ShellPlugin()
        result = p.run("ls -la")
        assert "stdout" in result


class TestAPIPlugin:
    def test_create(self):
        p = APIPlugin()
        assert p.id == "action.api"

    def test_call(self):
        p = APIPlugin()
        result = p.call("/endpoint", "POST")
        assert "status" in result


# ============== Learning Tests ==============

class TestRLPlugin:
    def test_create(self):
        p = RLPlugin()
        assert p.id == "learning.rl"

    def test_train(self):
        p = RLPlugin()
        result = p.train("env1", 100)
        assert "reward" in result


class TestSupervisedPlugin:
    def test_create(self):
        p = SupervisedPlugin()
        assert p.id == "learning.supervised"

    def test_fit(self):
        p = SupervisedPlugin()
        result = p.fit([1, 2], [3, 4])
        assert "accuracy" in result


class TestUnsupervisedPlugin:
    def test_create(self):
        p = UnsupervisedPlugin()
        assert p.id == "learning.unsupervised"

    def test_cluster(self):
        p = UnsupervisedPlugin()
        result = p.cluster([1, 2, 3, 4])
        assert "clusters" in result


class TestMetaLearningPlugin:
    def test_create(self):
        p = MetaLearningPlugin()
        assert p.id == "learning.meta"

    def test_adapt(self):
        p = MetaLearningPlugin()
        result = p.adapt("task1", ["ex1", "ex2"])
        assert result["adapted"] is True


class TestTransferLearningPlugin:
    def test_create(self):
        p = TransferLearningPlugin()
        assert p.id == "learning.transfer"

    def test_transfer(self):
        p = TransferLearningPlugin()
        result = p.transfer("src", "tgt")
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
        result = p.report_result(0.8)
        assert result["progressed"] is True


# ============== Safety Tests ==============

class TestGuardrailsPlugin:
    def test_create(self):
        p = GuardrailsPlugin()
        assert p.id == "safety.guardrails"

    def test_add_rule(self):
        p = GuardrailsPlugin()
        p.add_rule("bad_pattern", "block")
        assert len(p._rules) == 1

    def test_check(self):
        p = GuardrailsPlugin()
        p.add_rule("badword", "block")
        result = p.check("this has badword")
        assert result["violation"] is True

    def test_check_clean(self):
        p = GuardrailsPlugin()
        p.add_rule("badword", "block")
        result = p.check("clean text")
        assert result["violation"] is False


class TestBiasDetectionPlugin:
    def test_create(self):
        p = BiasDetectionPlugin()
        assert p.id == "safety.bias"

    def test_analyze(self):
        p = BiasDetectionPlugin()
        result = p.analyze(["sample1", "sample2"])
        assert "bias_score" in result


class TestAdversarialDefensePlugin:
    def test_create(self):
        p = AdversarialDefensePlugin()
        assert p.id == "safety.adversarial"

    def test_detect(self):
        p = AdversarialDefensePlugin()
        result = p.detect("normal input")
        assert result["is_adversarial"] is False


class TestPrivacyPlugin:
    def test_create(self):
        p = PrivacyPlugin()
        assert p.id == "safety.privacy"

    def test_redact(self):
        p = PrivacyPlugin()
        result = p.redact("My SSN is 123-45-6789")
        assert "[REDACTED]" in result["redacted"]

    def test_pii_types(self):
        p = PrivacyPlugin()
        types = p.pii_types()
        assert "ssn" in types


class TestExplainabilityPlugin:
    def test_create(self):
        p = ExplainabilityPlugin()
        assert p.id == "safety.explainability"

    def test_explain(self):
        p = ExplainabilityPlugin()
        result = p.explain("decision1")
        assert "explanation" in result


class TestAlignmentPlugin:
    def test_create(self):
        p = AlignmentPlugin()
        assert p.id == "safety.alignment"

    def test_check_alignment(self):
        p = AlignmentPlugin()
        result = p.check_alignment("action1", "intent1")
        assert result["aligned"] is True
