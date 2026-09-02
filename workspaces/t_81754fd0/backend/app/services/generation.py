"""AI-powered UI generation service."""
from __future__ import annotations

import time
import uuid
from typing import Any

from backend.app.models.schemas import (
    ExportRequest,
    ExportResponse,
    Framework,
    GenerationRequest,
    GenerationResponse,
)
from backend.app.services.component_library import library
from backend.app.utils.templates import TemplateEngine


class GenerationService:
    """Service that generates UI code from natural-language descriptions."""

    def __init__(self) -> None:
        self._engine = TemplateEngine()
        self._cache: dict[str, GenerationResponse] = {}

    # --- description parsing helpers ---

    @staticmethod
    def _detect_framework(description: str) -> Framework:
        """Detect the target framework from the description text."""
        lowered = description.lower()
        if "vue" in lowered:
            return Framework.vue
        if "angular" in lowered:
            return Framework.angular
        if "html" in lowered or "css" in lowered:
            return Framework.html_css
        return Framework.react

    @staticmethod
    def _detect_components(description: str) -> list[str]:
        """Detect relevant components from description keywords."""
        desc_lower = description.lower()
        matches: list[str] = []
        for comp in library.list_all():
            if (comp.name.lower().replace("_", " ") in desc_lower or
                    any(tag in desc_lower for tag in comp.tags)):
                if comp.name not in matches:
                    matches.append(comp.name)
            if len(matches) >= 8:
                break
        return matches if matches else ["Container", "Text"]

    @staticmethod
    def _detect_theme(description: str) -> str:
        desc_lower = description.lower()
        if "dark" in desc_lower:
            return "dark"
        if "light" in desc_lower:
            return "light"
        if "modern" in desc_lower:
            return "modern"
        if "minimal" in desc_lower:
            return "minimal"
        return "default"

    # --- generation ---

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate UI code based on request."""
        gen_id = str(uuid.uuid4())

        framework = request.framework or self._detect_framework(request.description)
        components = request.components or self._detect_components(request.description)
        theme = request.theme or self._detect_theme(request.description)

        # Collect templates from library
        html_parts: list[str] = []
        react_parts: list[str] = []
        vue_parts: list[str] = []
        angular_parts: list[str] = []

        for comp_name in components:
            comp = library.get_by_name(comp_name)
            if comp is None:
                continue
            html_parts.append(comp.html_template)
            react_parts.append(comp.react_template)
            vue_parts.append(comp.vue_template)
            angular_parts.append(comp.angular_template)

        # Wrap in container
        body_html = "\n  ".join(html_parts) if html_parts else "<div>No components</div>"

        html_code = self._engine.render_html(body_html, theme, request.responsive, request.accessible)
        jsx_code = self._engine.render_react(body_html, react_parts, components)
        vue_code = self._engine.render_vue(body_html, vue_parts, components)
        angular_code = self._engine.render_angular(body_html, angular_parts, components)
        css_code = self._engine.render_css(theme, request.responsive)

        response = GenerationResponse(
            id=gen_id,
            framework=framework,
            html_code=html_code,
            css_code=css_code,
            jsx_code=jsx_code,
            vue_code=vue_code,
            angular_code=angular_code,
            components_used=components,
            responsive=request.responsive,
            accessible=request.accessible,
        )
        self._cache[gen_id] = response
        return response

    def get_generation(self, gen_id: str) -> GenerationResponse | None:
        return self._cache.get(gen_id)

    def export(self, request: ExportRequest) -> ExportResponse:
        """Export a generation in a specific framework."""
        gen = self._cache.get(request.generation_id)
        if gen is None:
            raise ValueError(f"Generation {request.generation_id} not found")

        code_map = {
            Framework.react: gen.jsx_code,
            Framework.vue: gen.vue_code,
            Framework.angular: gen.angular_code,
            Framework.html_css: f"{gen.html_code}\n<style>{gen.css_code}</style>",
        }
        code = code_map.get(request.framework, gen.html_code)

        if request.minify:
            code = " ".join(code.split())

        ext_map = {
            Framework.react: (".tsx", "text/typescript"),
            Framework.vue: (".vue", "text/plain"),
            Framework.angular: (".ts", "text/typescript"),
            Framework.html_css: (".html", "text/html"),
        }
        ext, content_type = ext_map.get(request.framework, (".txt", "text/plain"))

        return ExportResponse(
            generation_id=request.generation_id,
            framework=request.framework,
            code=code,
            filename=f"ui-export{ext}",
            content_type=content_type,
        )


# Singleton
generation_service = GenerationService()
