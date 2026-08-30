"""
Operating Modes Plugin — Specialized Behavior Modes

Modes: coding, business, research, iot, scientific_discovery, demo.
Each mode configures tools, tone, expertise, and decision-making.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class OperatingMode(str, Enum):
    CODING = "coding"
    BUSINESS = "business"
    RESEARCH = "research"
    SCIENTIFIC_DISCOVERY = "scientific_discovery"
    IOT = "iot"
    DEMO = "demo"
    AUTOMATION = "automation"
    SAFETY_CRITICAL = "safety_critical"


@dataclass
class ModeConfig:
    name: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    expertise_areas: List[str] = field(default_factory=list)
    tone: str = "professional"
    risk_tolerance: float = 0.3  # 0-1
    require_approval_above: float = 0.5  # risk threshold
    verbosity: str = "medium"  # low/medium/high
    decision_style: str = "evidence-based"  # evidence-based / heuristic / cautious


class OperatingModes:
    """Specialized operating modes."""

    def __init__(self):
        self._modes: Dict[str, ModeConfig] = self._default_modes()
        self._current_mode: str = OperatingMode.CODING.value
        self._mode_history: List[Dict[str, Any]] = []

    def _default_modes(self) -> Dict[str, ModeConfig]:
        return {
            OperatingMode.CODING.value: ModeConfig(
                name="coding",
                description="Software engineering mode — focuses on code generation, "
                           "testing, refactoring, debugging",
                allowed_tools=["file_read", "file_write", "python_exec", "shell",
                              "git_tool", "http_get", "checkpoint"],
                expertise_areas=["software engineering", "algorithms", "data structures",
                                "testing", "CI/CD", "architecture"],
                tone="technical",
                risk_tolerance=0.4,
                require_approval_above=0.5,
                verbosity="medium",
                decision_style="evidence-based",
            ),
            OperatingMode.BUSINESS.value: ModeConfig(
                name="business",
                description="Business strategy mode — focuses on ROI, growth, "
                           "competitive analysis, market research",
                allowed_tools=["http_get", "memory_search", "python_exec", "file_read"],
                expertise_areas=["strategy", "marketing", "finance", "operations",
                                "competitive analysis"],
                tone="executive",
                risk_tolerance=0.3,
                require_approval_above=0.4,
                verbosity="concise",
                decision_style="cautious",
            ),
            OperatingMode.RESEARCH.value: ModeConfig(
                name="research",
                description="Research mode — focuses on literature review, "
                           "hypothesis generation, paper writing",
                allowed_tools=["http_get", "memory_search", "python_exec", "file_read", "file_write"],
                expertise_areas=["research methodology", "literature review",
                                "academic writing", "statistics", "domain knowledge"],
                tone="academic",
                risk_tolerance=0.2,
                require_approval_above=0.3,
                verbosity="high",
                decision_style="evidence-based",
            ),
            OperatingMode.SCIENTIFIC_DISCOVERY.value: ModeConfig(
                name="scientific_discovery",
                description="Scientific discovery — hypothesis testing, experiment design, "
                           "data analysis",
                allowed_tools=["python_exec", "http_get", "file_read", "file_write"],
                expertise_areas=["statistics", "experimental design", "data analysis",
                                "scientific method"],
                tone="rigorous",
                risk_tolerance=0.1,
                require_approval_above=0.2,
                verbosity="high",
                decision_style="evidence-based",
            ),
            OperatingMode.IOT.value: ModeConfig(
                name="iot",
                description="IoT mode — sensor data, device control, automation",
                allowed_tools=["http_get", "shell", "python_exec", "file_read", "file_write"],
                expertise_areas=["embedded systems", "sensors", "actuators",
                                "MQTT", "automation"],
                tone="technical",
                risk_tolerance=0.2,
                require_approval_above=0.3,
                verbosity="low",
                decision_style="cautious",
            ),
            OperatingMode.DEMO.value: ModeConfig(
                name="demo",
                description="Demo mode — user-friendly interactions, "
                           "high-visibility, marketing tone",
                allowed_tools=["http_get", "file_read", "python_exec", "file_write"],
                expertise_areas=["product", "UX", "storytelling"],
                tone="friendly",
                risk_tolerance=0.5,
                require_approval_above=0.7,
                verbosity="medium",
                decision_style="heuristic",
            ),
            OperatingMode.AUTOMATION.value: ModeConfig(
                name="automation",
                description="Automation — repetitive tasks, scheduled jobs, "
                           "batch processing",
                allowed_tools=["python_exec", "shell", "file_read", "file_write", "http_get"],
                expertise_areas=["scripting", "workflow automation", "scheduling"],
                tone="concise",
                risk_tolerance=0.3,
                require_approval_above=0.5,
                verbosity="low",
                decision_style="evidence-based",
            ),
            OperatingMode.SAFETY_CRITICAL.value: ModeConfig(
                name="safety_critical",
                description="Safety-critical — medical, aviation, infrastructure. "
                           "Maximum caution, multiple reviews, formal verification",
                allowed_tools=["python_exec", "file_read"],
                expertise_areas=["safety engineering", "formal methods", "redundancy"],
                tone="rigorous",
                risk_tolerance=0.0,
                require_approval_above=0.0,  # everything requires approval
                verbosity="high",
                decision_style="cautious",
            ),
        }

    def set_mode(self, mode_name: str) -> bool:
        """Switch to a different operating mode."""
        if mode_name not in self._modes:
            return False
        self._mode_history.append({
            "from": self._current_mode,
            "to": mode_name,
            "timestamp": time.time(),
        })
        self._current_mode = mode_name
        return True

    def get_current_mode(self) -> Optional[ModeConfig]:
        return self._modes.get(self._current_mode)

    def is_tool_allowed(self, tool_name: str) -> bool:
        mode = self.get_current_mode()
        if not mode:
            return False
        return tool_name in mode.allowed_tools

    def requires_approval(self, risk_score: float) -> bool:
        """Check if an action with given risk needs approval."""
        mode = self.get_current_mode()
        if not mode:
            return True
        return risk_score >= mode.require_approval_above

    def list_modes(self) -> List[str]:
        return list(self._modes.keys())

    def get_mode_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self._mode_history[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_mode": self._current_mode,
            "total_modes": len(self._modes),
            "mode_switches": len(self._mode_history),
        }


class OperatingModesPlugin:
    def __init__(self):
        self.engine = OperatingModes()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = OperatingModesPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
