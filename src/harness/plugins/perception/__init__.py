"""Perception Plugins — Vision, Audio, Text, Sensor, Multimodal, Attention."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginMetadata:
    provides: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)


class BasePlugin:
    def __init__(self, plugin_id: str, provides: list[str]):
        self.id = plugin_id
        self.metadata = PluginMetadata(provides=provides)
        self._loaded = False

    def on_load(self) -> None:
        self._loaded = True

    def on_unload(self) -> None:
        self._loaded = False

    def health_check(self) -> dict[str, Any]:
        return {"healthy": self._loaded}


class VisionPlugin(BasePlugin):
    def __init__(self):
        super().__init__("perception.vision", ["vision", "image", "object_detection"])

    def process(self, data: str) -> dict[str, Any]:
        return {"objects": ["object1", "object2"], "confidence": 0.95}


class AudioPlugin(BasePlugin):
    def __init__(self):
        super().__init__("perception.audio", ["audio", "speech", "sound"])

    def transcribe(self, data: str) -> dict[str, Any]:
        return {"text": "transcribed text", "confidence": 0.9}


class TextPlugin(BasePlugin):
    def __init__(self):
        super().__init__("perception.text", ["text", "nlp", "language"])

    def process(self, data: str) -> dict[str, Any]:
        return {"tokens": data.split(), "sentiment": "positive"}


class SensorPlugin(BasePlugin):
    def __init__(self):
        super().__init__("perception.sensor", ["sensor", "iot", "telemetry"])

    def read(self) -> dict[str, Any]:
        return {"temperature": 22.5, "humidity": 45.0}


class MultimodalPlugin(BasePlugin):
    def __init__(self):
        super().__init__("perception.multimodal", ["multimodal", "fusion", "cross_modal"])

    def fuse(self, modalities: list[str]) -> dict[str, Any]:
        return {"fused": True, "modalities": modalities}


class AttentionPlugin(BasePlugin):
    def __init__(self):
        super().__init__("perception.attention", ["attention", "focus", "salience"])

    def attend(self, data: str) -> dict[str, Any]:
        return {"salience": [0.1, 0.5, 0.9], "focus": "region_2"}
