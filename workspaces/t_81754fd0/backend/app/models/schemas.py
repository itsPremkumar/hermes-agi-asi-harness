"""Pydantic models for UIGenerator."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Framework(str, Enum):
    react = "react"
    vue = "vue"
    angular = "angular"
    html_css = "html_css"


class ComponentCategory(str, Enum):
    layout = "layout"
    navigation = "navigation"
    form = "form"
    display = "display"
    feedback = "feedback"
    data = "data"
    media = "media"
    overlay = "overlay"


class Component(BaseModel):
    id: str
    name: str
    category: ComponentCategory
    description: str
    html_template: str = ""
    react_template: str = ""
    vue_template: str = ""
    angular_template: str = ""
    props_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    responsive: bool = True
    accessible: bool = True


class GenerationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    framework: Framework | None = None
    responsive: bool = True
    accessible: bool = True
    theme: str | None = None
    components: list[str] = Field(default_factory=list)


class GenerationResponse(BaseModel):
    id: str
    framework: Framework
    html_code: str
    css_code: str
    jsx_code: str = ""
    vue_code: str = ""
    angular_code: str = ""
    components_used: list[str] = Field(default_factory=list)
    responsive: bool = True
    accessible: bool = True


class ExportRequest(BaseModel):
    generation_id: str
    framework: Framework
    include_tests: bool = False
    minify: bool = False


class ExportResponse(BaseModel):
    generation_id: str
    framework: Framework
    code: str
    filename: str
    content_type: str = "text/plain"


class ComponentListResponse(BaseModel):
    total: int
    components: list[Component]
    categories: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
