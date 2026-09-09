"""Tests for CanvasUI Dashboard Component System.

Comprehensive test suite covering design tokens, components, and docs site.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure src/ is on path
src = Path(__file__).resolve().parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from canvasui import (
    # Design tokens
    Theme, LightTheme, DarkTheme,
    ColorTokens, TypographyTokens, SpacingTokens,
    ElevationTokens, RadiusTokens, BreakpointTokens, MotionTokens,
    TokenRegistry, create_default_registry, default_registry,
    # Components
    Component, Button,
    FormField, TextInput, TextArea, Select, Checkbox, RadioGroup, Form,
    Column, Table,
    Chart, BarChart, LineChart, PieChart, AreaChart,
    Card, Modal,
    NavItem, Navbar, Sidebar, Breadcrumb,
    Badge, Avatar, Progress, Spinner, Tooltip, Tabs,
    Alert, Divider,
    Container, Grid, Flex, Stack,
    # Docs site
    DocsSite, create_default_site,
)


# ══════════════════════════════════════════════════════════════════════════
# Design Tokens Tests
# ══════════════════════════════════════════════════════════════════════════

class TestColorTokens:
    """Test color token system."""

    def test_default_colors(self):
        c = ColorTokens()
        assert c.primary_500 == "#3b82f6"
        assert c.neutral_0 == "#ffffff"
        assert c.success_500 == "#10b981"
        assert c.error_500 == "#ef4444"

    def test_custom_colors(self):
        c = ColorTokens(primary_500="#ff0000")
        assert c.primary_500 == "#ff0000"

    def test_frozen(self):
        c = ColorTokens()
        with pytest.raises(AttributeError):
            c.primary_500 = "#000000"


class TestTypographyTokens:
    """Test typography token system."""

    def test_default_typography(self):
        t = TypographyTokens()
        assert t.font_size_base == "1rem"
        assert t.font_weight_bold == 700
        assert t.line_height_normal == 1.5

    def test_font_families(self):
        t = TypographyTokens()
        assert "Inter" in t.font_family_sans
        assert "JetBrains" in t.font_family_mono


class TestSpacingTokens:
    """Test spacing token system."""

    def test_default_spacing(self):
        s = SpacingTokens()
        assert s.space_0 == "0px"
        assert s.space_4 == "16px"
        assert s.space_16 == "64px"

    def test_spacing_progression(self):
        s = SpacingTokens()
        assert s.space_1 == "4px"
        assert s.space_2 == "8px"
        assert s.space_3 == "12px"


class TestElevationTokens:
    """Test elevation token system."""

    def test_default_elevation(self):
        e = ElevationTokens()
        assert "0 1px 2px" in e.shadow_sm
        assert "0 4px 6px" in e.shadow_md
        assert "0 10px 15px" in e.shadow_lg


class TestRadiusTokens:
    """Test radius token system."""

    def test_default_radius(self):
        r = RadiusTokens()
        assert r.radius_none == "0px"
        assert r.radius_md == "6px"
        assert r.radius_full == "9999px"


class TestBreakpointTokens:
    """Test breakpoint token system."""

    def test_default_breakpoints(self):
        b = BreakpointTokens()
        assert b.breakpoint_sm == "640px"
        assert b.breakpoint_md == "768px"
        assert b.breakpoint_lg == "1024px"


class TestMotionTokens:
    """Test motion token system."""

    def test_default_motion(self):
        m = MotionTokens()
        assert m.duration_fast == "150ms"
        assert m.duration_normal == "250ms"
        assert m.easing_linear == "linear"


class TestTheme:
    """Test theme system."""

    def test_light_theme(self):
        t = LightTheme()
        assert t.name == "light"
        assert t.background == "#ffffff"
        assert t.text_primary == "#111827"

    def test_dark_theme(self):
        t = DarkTheme()
        assert t.name == "dark"
        assert t.background == "#0f0f23"
        assert t.text_primary == "#f9fafb"

    def test_resolve_tokens(self):
        t = LightTheme()
        assert t.resolve("colors.primary_500") == "#3b82f6"
        assert t.resolve("spacing.space_4") == "16px"
        assert t.resolve("background") == "#ffffff"

    def test_resolve_invalid_token(self):
        t = LightTheme()
        with pytest.raises(KeyError):
            t.resolve("invalid.token.path")

    def test_to_dict(self):
        t = LightTheme()
        d = t.to_dict()
        assert "background" in d
        assert "colors.primary_500" in d
        assert "typography.font_size_base" in d

    def test_theme_inheritance(self):
        t = Theme(name="custom")
        assert isinstance(t.colors, ColorTokens)
        assert isinstance(t.typography, TypographyTokens)


class TestTokenRegistry:
    """Test token registry."""

    def test_register_and_get(self):
        reg = TokenRegistry()
        theme = LightTheme()
        reg.register(theme)
        assert reg.get("light") is theme

    def test_set_active(self):
        reg = create_default_registry()
        reg.set_active("dark")
        assert reg.active == "dark"

    def test_list_themes(self):
        reg = create_default_registry()
        themes = reg.list_themes()
        assert "light" in themes
        assert "dark" in themes

    def test_get_invalid_theme(self):
        reg = TokenRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_default_registry(self):
        reg = default_registry
        assert "light" in reg.list_themes()
        assert "dark" in reg.list_themes()


# ══════════════════════════════════════════════════════════════════════════
# Component Tests
# ══════════════════════════════════════════════════════════════════════════

class TestComponent:
    """Test base component."""

    def test_create(self):
        c = Component(name="test")
        assert c.name == "test"
        assert c.visible is True
        assert c.enabled is True

    def test_add_child(self):
        parent = Component(name="parent")
        child = Component(name="child")
        parent.add_child(child)
        assert child in parent.children
        assert child.parent is parent

    def test_remove_child(self):
        parent = Component(name="parent")
        child = Component(name="child")
        parent.add_child(child)
        parent.remove_child(child)
        assert child not in parent.children

    def test_find(self):
        root = Component(name="root")
        child = Component(name="child")
        grandchild = Component(name="grandchild")
        child.add_child(grandchild)
        root.add_child(child)
        assert root.find("grandchild") is grandchild

    def test_find_not_found(self):
        root = Component(name="root")
        assert root.find("nonexistent") is None

    def test_event_handlers(self):
        c = Component(name="test")
        results = []
        c.on("click", lambda self, **kw: results.append("clicked"))
        c.trigger("click")
        assert results == ["clicked"]

    def test_event_bubbling(self):
        parent = Component(name="parent")
        child = Component(name="child")
        parent.add_child(child)
        results = []
        parent.on("click", lambda self, **kw: results.append("parent"))
        child.trigger("click")
        assert "parent" in results

    def test_to_dict(self):
        c = Component(name="test")
        d = c.to_dict()
        assert d["name"] == "test"
        assert d["visible"] is True
        assert "id" in d


class TestButton:
    """Test button component."""

    def test_create(self):
        b = Button(text="Click me")
        assert b.text == "Click me"
        assert b.variant == "primary"
        assert b.size == "md"

    def test_variants(self):
        for v in ["primary", "secondary", "outline", "ghost", "danger"]:
            b = Button(text="Test", variant=v)
            assert b.variant == v

    def test_sizes(self):
        for s in ["sm", "md", "lg"]:
            b = Button(text="Test", size=s)
            assert b.size == s

    def test_to_dict(self):
        b = Button(text="Submit", variant="primary", size="lg")
        d = b.to_dict()
        assert d["text"] == "Submit"
        assert d["variant"] == "primary"
        assert d["size"] == "lg"


class TestFormComponents:
    """Test form components."""

    def test_text_input(self):
        t = TextInput(label="Name", placeholder="Enter name")
        assert t.label == "Name"
        assert t.placeholder == "Enter name"

    def test_text_input_validation(self):
        t = TextInput(label="Name", required=True)
        assert t.validate() is False
        assert "required" in t.error.lower()

    def test_text_input_min_length(self):
        t = TextInput(label="Name", min_length=3)
        t.value = "ab"
        assert t.validate() is False
        assert "minimum" in t.error.lower()

    def test_text_input_max_length(self):
        t = TextInput(label="Name", max_length=5)
        t.value = "toolong"
        assert t.validate() is False
        assert "maximum" in t.error.lower()

    def test_text_input_valid(self):
        t = TextInput(label="Name", required=True, min_length=2, max_length=20)
        t.value = "Alice"
        assert t.validate() is True
        assert t.error == ""

    def test_text_area(self):
        ta = TextArea(label="Bio", rows=6)
        assert ta.rows == 6

    def test_select(self):
        s = Select(label="Role", options=[
            {"label": "Admin", "value": "admin"},
            {"label": "User", "value": "user"},
        ])
        assert len(s.options) == 2

    def test_select_validation(self):
        s = Select(label="Role", required=True)
        assert s.validate() is False
        s.value = "admin"
        assert s.validate() is True

    def test_checkbox(self):
        c = Checkbox(label="Accept", checked=True)
        assert c.checked is True

    def test_checkbox_validation(self):
        c = Checkbox(label="Accept", required=True)
        assert c.validate() is False
        c.checked = True
        assert c.validate() is True

    def test_radio_group(self):
        r = RadioGroup(label="Choice", options=[
            {"label": "A", "value": "a"},
            {"label": "B", "value": "b"},
        ])
        assert len(r.options) == 2

    def test_form(self):
        f = Form(title="Signup")
        f.add_field(TextInput(label="Name", name="name"))
        f.add_field(TextInput(label="Email", name="email"))
        assert len(f.fields) == 2

    def test_form_validation(self):
        f = Form(title="Test")
        f.add_field(TextInput(label="Name", name="name", required=True))
        assert f.validate() is False
        f.fields[0].value = "Alice"
        assert f.validate() is True

    def test_form_get_values(self):
        f = Form(title="Test")
        f.add_field(TextInput(label="Name", name="name"))
        f.add_field(TextInput(label="Email", name="email"))
        f.fields[0].value = "Alice"
        f.fields[1].value = "alice@example.com"
        values = f.get_values()
        assert values["name"] == "Alice"
        assert values["email"] == "alice@example.com"


class TestTable:
    """Test table component."""

    def test_add_column(self):
        t = Table()
        t.add_column("name", "Name")
        assert len(t.columns) == 1
        assert t.columns[0].key == "name"

    def test_set_data(self):
        t = Table()
        t.set_data([{"name": "Alice"}, {"name": "Bob"}])
        assert len(t.data) == 2

    def test_sort_by(self):
        t = Table()
        t.add_column("name", "Name")
        t.set_data([{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}])
        t.sort_by("name")
        assert t.data[0]["name"] == "Alice"
        assert t.sort_direction == "asc"

    def test_sort_direction_toggle(self):
        t = Table()
        t.add_column("name", "Name")
        t.set_data([{"name": "Alice"}, {"name": "Bob"}])
        t.sort_by("name")
        t.sort_by("name")
        assert t.sort_direction == "desc"

    def test_pagination(self):
        t = Table()
        t.set_data([{"id": i} for i in range(25)])
        t.paginated = True
        t.page_size = 10
        assert t.page_count == 3
        assert len(t.visible_data) == 10

    def test_pagination_page_2(self):
        t = Table()
        t.set_data([{"id": i} for i in range(25)])
        t.paginated = True
        t.page_size = 10
        t.current_page = 1
        assert len(t.visible_data) == 10

    def test_to_dict(self):
        t = Table()
        t.add_column("name", "Name")
        t.set_data([{"name": "Alice"}])
        d = t.to_dict()
        assert d["row_count"] == 1
        assert len(d["columns"]) == 1


class TestCharts:
    """Test chart components."""

    def test_bar_chart(self):
        c = BarChart(title="Sales")
        c.data = [{"label": "Jan", "value": 100}]
        d = c.to_dict()
        assert d["chart_type"] == "bar"
        assert d["title"] == "Sales"

    def test_line_chart(self):
        c = LineChart(title="Trend")
        c.series = [{"name": "A", "data": [{"x": 1, "y": 2}]}]
        d = c.to_dict()
        assert d["chart_type"] == "line"

    def test_pie_chart(self):
        c = PieChart(title="Distribution")
        c.data = [{"label": "A", "value": 50}]
        d = c.to_dict()
        assert d["chart_type"] == "pie"

    def test_area_chart(self):
        c = AreaChart(title="Growth")
        c.series = [{"name": "A", "data": [{"x": 1, "y": 10}]}]
        d = c.to_dict()
        assert d["chart_type"] == "area"

    def test_chart_dimensions(self):
        c = BarChart(width=800, height=400)
        assert c.width == 800
        assert c.height == 400


class TestCard:
    """Test card component."""

    def test_create(self):
        c = Card(title="Test Card", subtitle="Subtitle")
        assert c.title == "Test Card"
        assert c.subtitle == "Subtitle"

    def test_to_dict(self):
        c = Card(title="Test", elevation="lg")
        d = c.to_dict()
        assert d["title"] == "Test"
        assert d["elevation"] == "lg"


class TestModal:
    """Test modal component."""

    def test_create(self):
        m = Modal(title="Confirm")
        assert m.title == "Confirm"
        assert m.open is False

    def test_show_hide(self):
        m = Modal()
        m.show()
        assert m.open is True
        m.hide()
        assert m.open is False

    def test_toggle(self):
        m = Modal()
        m.toggle()
        assert m.open is True
        m.toggle()
        assert m.open is False

    def test_event_on_show(self):
        m = Modal()
        results = []
        m.on("show", lambda self, **kw: results.append("shown"))
        m.show()
        assert results == ["shown"]


class TestNavigation:
    """Test navigation components."""

    def test_navbar(self):
        n = Navbar(brand="App")
        n.add_item("Home", "/")
        n.add_item("About", "/about")
        assert len(n.items) == 2
        assert n.brand == "App"

    def test_sidebar(self):
        s = Sidebar()
        s.add_item("Dashboard", "/dash")
        assert len(s.items) == 1

    def test_breadcrumb(self):
        b = Breadcrumb()
        b.add_item("Home", "/")
        b.add_item("Page", "/page")
        assert len(b.items) == 2

    def test_nav_item(self):
        item = NavItem(label="Home", href="/", active=True)
        assert item.active is True


class TestUtilityComponents:
    """Test utility components."""

    def test_badge(self):
        b = Badge(text="Active", variant="success")
        assert b.text == "Active"
        assert b.variant == "success"

    def test_avatar(self):
        a = Avatar(initials="AC", size="lg")
        assert a.initials == "AC"
        assert a.size == "lg"

    def test_progress(self):
        p = Progress(value=50, max=100)
        assert p.percentage == 50.0

    def test_progress_over_max(self):
        p = Progress(value=150, max=100)
        assert p.percentage == 100.0

    def test_progress_zero_max(self):
        p = Progress(value=50, max=0)
        assert p.percentage == 0.0

    def test_spinner(self):
        s = Spinner(size="lg")
        assert s.size == "lg"

    def test_tooltip(self):
        t = Tooltip(text="Info", position="bottom")
        assert t.text == "Info"
        assert t.position == "bottom"

    def test_tabs(self):
        t = Tabs()
        t.add_tab("tab1", "Tab 1")
        t.add_tab("tab2", "Tab 2")
        assert len(t.tabs) == 2
        assert t.active_tab == "tab1"

    def test_alert(self):
        a = Alert(title="Error", message="Something failed", variant="error")
        assert a.variant == "error"
        assert a.visible is True

    def test_alert_dismiss(self):
        a = Alert()
        a.dismiss()
        assert a.visible is False

    def test_divider(self):
        d = Divider(orientation="vertical")
        assert d.orientation == "vertical"


class TestLayoutComponents:
    """Test layout components."""

    def test_container(self):
        c = Container(max_width="xl")
        assert c.max_width == "xl"

    def test_grid(self):
        g = Grid(columns=4, gap="lg")
        assert g.columns == 4
        assert g.gap == "lg"

    def test_flex(self):
        f = Flex(direction="column", justify="center")
        assert f.direction == "column"
        assert f.justify == "center"

    def test_stack(self):
        s = Stack(gap="lg")
        assert s.gap == "lg"


# ══════════════════════════════════════════════════════════════════════════
# Integration Tests
# ══════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for the full system."""

    def test_full_dashboard_build(self):
        """Build a complete dashboard with all component types."""
        # Create root container
        root = Container(max_width="xl")

        # Navbar
        navbar = Navbar(brand="CanvasUI")
        navbar.add_item("Dashboard", "/", active=True)
        navbar.add_item("Analytics", "/analytics")
        navbar.add_item("Settings", "/settings")
        root.add_child(navbar)

        # Main content stack
        stack = Stack(gap="lg")

        # Cards row
        cards_row = Flex(gap="md")
        for i in range(3):
            card = Card(title=f"Metric {i+1}", subtitle=f"Value: {(i+1)*100}")
            cards_row.add_child(card)
        stack.add_child(cards_row)

        # Table
        table = Table()
        table.add_column("name", "Name", sortable=True)
        table.add_column("status", "Status")
        table.set_data([
            {"name": "Alice", "status": "Active"},
            {"name": "Bob", "status": "Away"},
        ])
        stack.add_child(table)

        # Chart
        chart = BarChart(title="Weekly Sales", width=600, height=300)
        chart.data = [
            {"label": "Mon", "value": 120},
            {"label": "Tue", "value": 200},
            {"label": "Wed", "value": 150},
        ]
        stack.add_child(chart)

        root.add_child(stack)

        # Verify structure
        d = root.to_dict()
        assert d["name"] == ""
        assert len(d["children"]) == 2  # navbar + stack

    def test_form_with_all_fields(self):
        """Create a form with every field type."""
        form = Form(title="Registration")

        form.add_field(TextInput(label="Full Name", name="name", required=True))
        form.add_field(TextInput(label="Email", name="email", input_type="email", required=True))
        form.add_field(TextArea(label="Bio", name="bio"))
        form.add_field(Select(label="Role", name="role", options=[
            {"label": "Admin", "value": "admin"},
            {"label": "User", "value": "user"},
        ]))
        form.add_field(Checkbox(label="Accept Terms", name="terms", required=True))
        form.add_field(RadioGroup(label="Plan", name="plan", options=[
            {"label": "Free", "value": "free"},
            {"label": "Pro", "value": "pro"},
        ]))

        # Fill values
        form.fields[0].value = "Alice"
        form.fields[1].value = "alice@example.com"
        form.fields[2].value = "Hello world"
        form.fields[3].value = "admin"
        form.fields[4].checked = True
        form.fields[5].value = "pro"

        assert form.validate() is True
        values = form.get_values()
        assert values["name"] == "Alice"
        assert values["email"] == "alice@example.com"

    def test_theme_switching(self):
        """Test switching between light and dark themes."""
        registry = create_default_registry()

        light = registry.get("light")
        assert light.name == "light"

        registry.set_active("dark")
        dark = registry.get()
        assert dark.name == "dark"
        assert dark.background != light.background

    def test_component_tree_serialization(self):
        """Test serializing a complex component tree."""
        root = Component(name="root")
        child1 = Component(name="child1")
        child2 = Component(name="child2")
        grandchild = Component(name="grandchild")

        child1.add_child(grandchild)
        root.add_child(child1)
        root.add_child(child2)

        d = root.to_dict()
        assert d["name"] == "root"
        assert len(d["children"]) == 2
        assert d["children"][0]["children"][0]["name"] == "grandchild"

    def test_event_system(self):
        """Test event propagation through component tree."""
        root = Component(name="root")
        child = Component(name="child")
        grandchild = Component(name="grandchild")
        child.add_child(grandchild)
        root.add_child(child)

        events = []
        root.on("action", lambda self, **kw: events.append(f"root:{self.name}"))
        child.on("action", lambda self, **kw: events.append(f"child:{self.name}"))
        grandchild.on("action", lambda self, **kw: events.append(f"grandchild:{self.name}"))

        grandchild.trigger("action")

        assert "grandchild:grandchild" in events
        assert "child:child" in events
        assert "root:root" in events


# ══════════════════════════════════════════════════════════════════════════
# Docs Site Tests
# ══════════════════════════════════════════════════════════════════════════

class TestDocsSite:
    """Test documentation site generator."""

    def test_create_site(self):
        site = DocsSite(title="Test Docs")
        assert site.title == "Test Docs"

    def test_add_section(self):
        site = DocsSite()
        section = site.add_section("intro", "Introduction", "Getting started")
        assert section["id"] == "intro"
        assert section["title"] == "Introduction"

    def test_generate_html(self):
        site = create_default_site()
        html_output = site.generate_html()
        assert "<!DOCTYPE html>" in html_output
        assert "CanvasUI" in html_output
        assert "Design Tokens" in html_output
        assert "Buttons" in html_output

    def test_generate_to_file(self, tmp_path):
        site = create_default_site()
        output = tmp_path / "docs.html"
        site.generate(str(output))
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_html_escaping(self):
        site = DocsSite(title="<script>alert('xss')</script>")
        html_output = site.generate_html()
        assert "<script>alert" not in html_output
        assert "&lt;script&gt;" in html_output

    def test_dark_theme_in_html(self):
        site = DocsSite(theme=DarkTheme())
        html_output = site.generate_html()
        assert 'data-theme="dark"' in html_output

    def test_all_sections_present(self):
        site = create_default_site()
        html_output = site.generate_html()
        expected_sections = [
            "tokens", "buttons", "forms", "tables", "charts",
            "cards", "modals", "feedback", "layout"
        ]
        for section_id in expected_sections:
            assert f'id="{section_id}"' in html_output

    def test_search_input_present(self):
        site = create_default_site()
        html_output = site.generate_html()
        assert 'id="search"' in html_output

    def test_theme_toggle_present(self):
        site = create_default_site()
        html_output = site.generate_html()
        assert "toggleTheme" in html_output


# ══════════════════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_theme_to_dict(self):
        t = Theme()
        d = t.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_component_with_no_name(self):
        c = Component()
        assert c.name == ""

    def test_deeply_nested_find(self):
        root = Component(name="root")
        current = root
        for i in range(10):
            child = Component(name=f"level_{i}")
            current.add_child(child)
            current = child
        found = root.find("level_9")
        assert found is not None
        assert found.name == "level_9"

    def test_remove_nonexistent_child(self):
        parent = Component(name="parent")
        other = Component(name="other")
        parent.remove_child(other)  # Should not raise

    def test_table_empty_data(self):
        t = Table()
        t.add_column("name", "Name")
        assert t.visible_data == []

    def test_progress_negative_value(self):
        p = Progress(value=-10, max=100)
        assert p.percentage == -10.0

    def test_modal_show_when_already_open(self):
        m = Modal()
        m.show()
        m.show()  # Should not raise
        assert m.open is True

    def test_button_disabled_state(self):
        b = Button(text="Click", disabled=True)
        assert b.disabled is True

    def test_form_no_fields(self):
        f = Form(title="Empty")
        assert f.validate() is True
        assert f.get_values() == {}

    def test_table_sort_empty(self):
        t = Table()
        t.sort_by("name")  # Should not raise
        assert t.data == []
