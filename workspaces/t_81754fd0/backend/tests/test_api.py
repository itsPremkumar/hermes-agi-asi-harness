"""Tests for UIGenerator backend."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import (
    ComponentCategory,
    ExportRequest,
    Framework,
    GenerationRequest,
)
from backend.app.services.component_library import ComponentLibrary, library
from backend.app.services.generation import GenerationService
from backend.app.utils.templates import TemplateEngine


# --- Fixtures ---

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def gen_service() -> GenerationService:
    return GenerationService()


# --- Health ---

def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "UIGenerator"


# --- Component Library ---

class TestComponentLibrary:
    def test_total_components(self) -> None:
        assert library.total >= 500

    def test_list_all(self) -> None:
        comps = library.list_all()
        assert len(comps) >= 500

    def test_get_by_id(self) -> None:
        comp = library.get("comp_0001")
        assert comp is not None
        assert comp.id == "comp_0001"

    def test_get_by_id_missing(self) -> None:
        assert library.get("nonexistent") is None

    def test_get_by_name(self) -> None:
        comp = library.get_by_name("Button")
        assert comp is not None
        assert comp.name == "Button"

    def test_get_by_name_missing(self) -> None:
        assert library.get_by_name("Nonexistent") is None

    def test_by_category(self) -> None:
        layout = library.by_category("layout")
        assert len(layout) > 0
        assert all(c.category == ComponentCategory.layout for c in layout)

    def test_by_category_missing(self) -> None:
        assert library.by_category("nonexistent") == []

    def test_search(self) -> None:
        results = library.search("button")
        assert len(results) > 0

    def test_search_limit(self) -> None:
        results = library.search("a", limit=10)
        assert len(results) <= 10

    def test_categories(self) -> None:
        cats = library.categories()
        assert "layout" in cats
        assert "navigation" in cats
        assert "form" in cats

    def test_component_has_templates(self) -> None:
        comp = library.get_by_name("Button")
        assert comp is not None
        assert comp.html_template
        assert comp.react_template
        assert comp.vue_template
        assert comp.angular_template

    def test_component_responsive_accessible(self) -> None:
        comp = library.get_by_name("Card")
        assert comp is not None
        assert comp.responsive is True
        assert comp.accessible is True


# --- Generation Service ---

class TestGenerationService:
    def test_generate_basic(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A login form with button and input")
        resp = gen_service.generate(req)
        assert resp.id
        assert resp.html_code
        assert resp.css_code
        assert resp.framework == Framework.react

    def test_generate_detects_vue(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A vue dashboard")
        resp = gen_service.generate(req)
        assert resp.framework == Framework.vue

    def test_generate_detects_angular(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="An angular component")
        resp = gen_service.generate(req)
        assert resp.framework == Framework.angular

    def test_generate_detects_html(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="Simple html and css page")
        resp = gen_service.generate(req)
        assert resp.framework == Framework.html_css

    def test_generate_detects_dark_theme(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A dark themed navbar")
        resp = gen_service.generate(req)
        assert "#0f172a" in resp.css_code

    def test_generate_detects_components(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A page with button, input, and card")
        resp = gen_service.generate(req)
        assert len(resp.components_used) > 0

    def test_generate_caches(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A header")
        resp = gen_service.generate(req)
        cached = gen_service.get_generation(resp.id)
        assert cached is not None
        assert cached.id == resp.id

    def test_get_generation_missing(self, gen_service: GenerationService) -> None:
        assert gen_service.get_generation("nonexistent") is None

    def test_export_react(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A button")
        gen = gen_service.generate(req)
        export_req = ExportRequest(generation_id=gen.id, framework=Framework.react)
        export = gen_service.export(export_req)
        assert export.framework == Framework.react
        assert ".tsx" in export.filename

    def test_export_vue(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A button")
        gen = gen_service.generate(req)
        export_req = ExportRequest(generation_id=gen.id, framework=Framework.vue)
        export = gen_service.export(export_req)
        assert export.framework == Framework.vue
        assert ".vue" in export.filename

    def test_export_angular(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A button")
        gen = gen_service.generate(req)
        export_req = ExportRequest(generation_id=gen.id, framework=Framework.angular)
        export = gen_service.export(export_req)
        assert export.framework == Framework.angular

    def test_export_html(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A button")
        gen = gen_service.generate(req)
        export_req = ExportRequest(generation_id=gen.id, framework=Framework.html_css)
        export = gen_service.export(export_req)
        assert export.framework == Framework.html_css
        assert ".html" in export.filename

    def test_export_minify(self, gen_service: GenerationService) -> None:
        req = GenerationRequest(description="A button")
        gen = gen_service.generate(req)
        export_req = ExportRequest(generation_id=gen.id, framework=Framework.react, minify=True)
        export = gen_service.export(export_req)
        assert export.code

    def test_export_missing_generation(self, gen_service: GenerationService) -> None:
        export_req = ExportRequest(generation_id="nonexistent", framework=Framework.react)
        with pytest.raises(ValueError, match="not found"):
            gen_service.export(export_req)


# --- Template Engine ---

class TestTemplateEngine:
    def setup_method(self) -> None:
        self.engine = TemplateEngine()

    def test_render_html_default(self) -> None:
        html = self.engine.render_html("<p>Hello</p>", "default", True, True)
        assert "<!DOCTYPE html>" in html
        assert "viewport" in html
        assert 'lang="en"' in html

    def test_render_html_dark(self) -> None:
        html = self.engine.render_html("<p>Hello</p>", "dark", False, False)
        assert "#0f172a" in html
        assert "viewport" not in html

    def test_render_css_responsive(self) -> None:
        css = self.engine.render_css("default", True)
        assert "@media" in css

    def test_render_css_no_responsive(self) -> None:
        css = self.engine.render_css("default", False)
        assert "@media" not in css

    def test_render_react(self) -> None:
        code = self.engine.render_react("", ["Button", "Input"], ["Button", "Input"])
        assert "import React" in code
        assert "GeneratedUI" in code

    def test_render_vue(self) -> None:
        code = self.engine.render_vue("", ["Button"], ["Button"])
        assert "<template>" in code
        assert "<script setup" in code

    def test_render_angular(self) -> None:
        code = self.engine.render_angular("", ["Button"], ["Button"])
        assert "@Component" in code
        assert "GeneratedUIComponent" in code

    def test_themes_exist(self) -> None:
        assert "default" in TemplateEngine.THEMES
        assert "dark" in TemplateEngine.THEMES
        assert "modern" in TemplateEngine.THEMES
        assert "minimal" in TemplateEngine.THEMES


# --- API Routes ---

class TestAPIRoutes:
    def test_list_components(self, client: TestClient) -> None:
        resp = client.get("/api/v1/components")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 500
        assert len(data["components"]) > 0
        assert "categories" in data

    def test_list_components_with_category(self, client: TestClient) -> None:
        resp = client.get("/api/v1/components?category=form")
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["category"] == "form" for c in data["components"])

    def test_list_components_with_search(self, client: TestClient) -> None:
        resp = client.get("/api/v1/components?search=button")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["components"]) > 0

    def test_list_components_with_limit(self, client: TestClient) -> None:
        resp = client.get("/api/v1/components?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["components"]) <= 10

    def test_get_component(self, client: TestClient) -> None:
        resp = client.get("/api/v1/components/comp_0001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "comp_0001"

    def test_get_component_missing(self, client: TestClient) -> None:
        resp = client.get("/api/v1/components/nonexistent")
        assert resp.status_code == 404

    def test_list_categories(self, client: TestClient) -> None:
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "layout" in data
        assert "form" in data

    def test_list_frameworks(self, client: TestClient) -> None:
        resp = client.get("/api/v1/frameworks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        ids = [f["id"] for f in data]
        assert "react" in ids
        assert "vue" in ids
        assert "angular" in ids
        assert "html_css" in ids

    def test_generate_endpoint(self, client: TestClient) -> None:
        resp = client.post("/api/v1/generate", json={
            "description": "A login form with button and input",
            "framework": "react",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["html_code"]
        assert data["css_code"]
        assert data["framework"] == "react"

    def test_generate_endpoint_default_framework(self, client: TestClient) -> None:
        resp = client.post("/api/v1/generate", json={
            "description": "A simple page",
        })
        assert resp.status_code == 200

    def test_get_generation_endpoint(self, client: TestClient) -> None:
        # First create
        resp = client.post("/api/v1/generate", json={"description": "A header"})
        gen_id = resp.json()["id"]
        # Then fetch
        resp = client.get(f"/api/v1/generate/{gen_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == gen_id

    def test_get_generation_missing(self, client: TestClient) -> None:
        resp = client.get("/api/v1/generate/nonexistent")
        assert resp.status_code == 404

    def test_export_endpoint(self, client: TestClient) -> None:
        # First create
        resp = client.post("/api/v1/generate", json={"description": "A button"})
        gen_id = resp.json()["id"]
        # Then export
        resp = client.post("/api/v1/export", json={
            "generation_id": gen_id,
            "framework": "react",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"]
        assert data["filename"]

    def test_export_missing_generation(self, client: TestClient) -> None:
        resp = client.post("/api/v1/export", json={
            "generation_id": "nonexistent",
            "framework": "react",
        })
        assert resp.status_code == 404


# --- Models ---

class TestModels:
    def test_generation_request_valid(self) -> None:
        req = GenerationRequest(description="Test")
        assert req.description == "Test"
        assert req.framework is None

    def test_generation_request_empty_desc(self) -> None:
        with pytest.raises(Exception):
            GenerationRequest(description="")

    def test_component_model(self) -> None:
        from backend.app.models.schemas import Component
        comp = Component(
            id="test_001",
            name="TestComp",
            category=ComponentCategory.layout,
            description="A test component",
        )
        assert comp.id == "test_001"
        assert comp.responsive is True
