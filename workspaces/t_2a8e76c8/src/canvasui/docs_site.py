"""Documentation site generator for CanvasUI Dashboard.

Generates a complete, self-contained HTML documentation site with:
- Component reference with live examples
- Design token reference
- Interactive search
- Dark/light mode toggle
- Responsive layout
"""
from __future__ import annotations

import html
import json
from typing import Any

from .components import (
    Button, Card, Container, Flex, Grid, Navbar, Sidebar, Table, Column,
    BarChart, LineChart, PieChart, AreaChart,
    TextInput, Form, Select, Checkbox, RadioGroup, TextArea,
    Modal, Alert, Badge, Avatar, Progress, Spinner, Tooltip, Tabs,
    Breadcrumb, Divider, Stack,
)
from .design_tokens import (
    Theme, LightTheme, DarkTheme, TokenRegistry,
    ColorTokens, TypographyTokens, SpacingTokens,
    ElevationTokens, RadiusTokens, BreakpointTokens, MotionTokens,
)


class DocsSite:
    """Documentation site generator."""

    def __init__(self, title: str = "CanvasUI Dashboard", theme: Theme | None = None):
        self.title = title
        self.theme = theme or LightTheme()
        self._sections: list[dict[str, Any]] = []

    def add_section(self, id: str, title: str, description: str = "") -> dict[str, Any]:
        """Add a documentation section."""
        section = {
            "id": id,
            "title": title,
            "description": description,
            "items": [],
        }
        self._sections.append(section)
        return section

    def _escape(self, text: str) -> str:
        """Escape HTML entities."""
        return html.escape(str(text))

    def _render_token_table(self, tokens: dict[str, Any]) -> str:
        """Render a token reference table."""
        rows = []
        for key, value in tokens.items():
            rows.append(f"""
                <tr>
                    <td><code>{self._escape(key)}</code></td>
                    <td><code>{self._escape(str(value))}</code></td>
                </tr>""")
        return f"""
            <table class="token-table">
                <thead>
                    <tr><th>Token</th><th>Value</th></tr>
                </thead>
                <tbody>{"".join(rows)}</tbody>
            </table>"""

    def _render_button_examples(self) -> str:
        """Render button component examples."""
        variants = ["primary", "secondary", "outline", "ghost", "danger"]
        sizes = ["sm", "md", "lg"]

        sections = []

        # Variants
        variant_buttons = " ".join(
            f'<button class="btn btn-{v}">{v.title()}</button>'
            for v in variants
        )
        sections.append(f"""
            <div class="example-block">
                <h4>Variants</h4>
                <div class="example-row">{variant_buttons}</div>
                <pre><code>&lt;Button variant="primary"&gt;Primary&lt;/Button&gt;
&lt;Button variant="secondary"&gt;Secondary&lt;/Button&gt;
&lt;Button variant="outline"&gt;Outline&lt;/Button&gt;
&lt;Button variant="ghost"&gt;Ghost&lt;/Button&gt;
&lt;Button variant="danger"&gt;Danger&lt;/Button&gt;</code></pre>
            </div>""")

        # Sizes
        size_buttons = " ".join(
            f'<button class="btn btn-primary btn-{s}">{s.upper()}</button>'
            for s in sizes
        )
        sections.append(f"""
            <div class="example-block">
                <h4>Sizes</h4>
                <div class="example-row">{size_buttons}</div>
                <pre><code>&lt;Button size="sm"&gt;Small&lt;/Button&gt;
&lt;Button size="md"&gt;Medium&lt;/Button&gt;
&lt;Button size="lg"&gt;Large&lt;/Button&gt;</code></pre>
            </div>""")

        # States
        sections.append(f"""
            <div class="example-block">
                <h4>States</h4>
                <div class="example-row">
                    <button class="btn btn-primary" disabled>Disabled</button>
                    <button class="btn btn-primary btn-loading">Loading...</button>
                </div>
                <pre><code>&lt;Button disabled&gt;Disabled&lt;/Button&gt;
&lt;Button loading&gt;Loading...&lt;/Button&gt;</code></pre>
            </div>""")

        return "".join(sections)

    def _render_form_examples(self) -> str:
        """Render form component examples."""
        return """
            <div class="example-block">
                <h4>Text Input</h4>
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" class="form-input" placeholder="Enter your name">
                </div>
                <pre><code>&lt;TextInput label="Name" placeholder="Enter your name" /&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Select</h4>
                <div class="form-group">
                    <label>Role</label>
                    <select class="form-input">
                        <option>Admin</option>
                        <option>Editor</option>
                        <option>Viewer</option>
                    </select>
                </div>
                <pre><code>&lt;Select label="Role" options={[
  {{label: 'Admin', value: 'admin'}},
  {{label: 'Editor', value: 'editor'}},
  {{label: 'Viewer', value: 'viewer'}}
]} /&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Checkbox &amp; Radio</h4>
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" checked> Accept terms
                    </label>
                </div>
                <pre><code>&lt;Checkbox label="Accept terms" checked /&gt;</code></pre>
            </div>"""

    def _render_table_example(self) -> str:
        """Render table component example."""
        return """
            <div class="example-block">
                <h4>Data Table</h4>
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr><th>Name</th><th>Role</th><th>Status</th><th>Last Active</th></tr>
                        </thead>
                        <tbody>
                            <tr><td>Alice Chen</td><td>Admin</td><td><span class="badge badge-success">Active</span></td><td>2 min ago</td></tr>
                            <tr><td>Bob Kumar</td><td>Editor</td><td><span class="badge badge-success">Active</span></td><td>15 min ago</td></tr>
                            <tr><td>Carol Smith</td><td>Viewer</td><td><span class="badge badge-warning">Away</span></td><td>1 hour ago</td></tr>
                            <tr><td>Dan Lee</td><td>Editor</td><td><span class="badge badge-default">Offline</span></td><td>3 days ago</td></tr>
                        </tbody>
                    </table>
                </div>
                <pre><code>&lt;Table columns={[{{key: 'name', label: 'Name', sortable: true}}]} data={data} /&gt;</code></pre>
            </div>"""

    def _render_chart_examples(self) -> str:
        """Render chart component examples."""
        return """
            <div class="example-block">
                <h4>Bar Chart</h4>
                <div class="chart-placeholder">
                    <div class="bar-chart-demo">
                        <div class="bar" style="height: 60%"></div>
                        <div class="bar" style="height: 80%"></div>
                        <div class="bar" style="height: 45%"></div>
                        <div class="bar" style="height: 90%"></div>
                        <div class="bar" style="height: 70%"></div>
                    </div>
                </div>
                <pre><code>&lt;BarChart data={[
  {{label: 'Jan', value: 60}},
  {{label: 'Feb', value: 80}},
  {{label: 'Mar', value: 45}},
  {{label: 'Apr', value: 90}},
  {{label: 'May', value: 70}}
]} /&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Line Chart</h4>
                <div class="chart-placeholder">
                    <svg viewBox="0 0 400 200" class="line-chart-demo">
                        <polyline fill="none" stroke="#3b82f6" stroke-width="2" points="0,150 80,100 160,120 240,60 320,80 400,30"/>
                        <polyline fill="none" stroke="#10b981" stroke-width="2" points="0,170 80,140 160,150 240,100 320,110 400,70"/>
                    </svg>
                </div>
                <pre><code>&lt;LineChart series={[
  {{name: 'Revenue', data: [{{x: 'Jan', y: 60}}, {{x: 'Feb', y: 80}}]}},
  {{name: 'Profit', data: [{{x: 'Jan', y: 30}}, {{x: 'Feb', y: 45}}]}}
]} /&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Pie Chart</h4>
                <div class="chart-placeholder">
                    <div class="pie-chart-demo"></div>
                </div>
                <pre><code>&lt;PieChart data={[
  {{label: 'Direct', value: 40}},
  {{label: 'Organic', value: 30}},
  {{label: 'Referral', value: 20}},
  {{label: 'Social', value: 10}}
]} /&gt;</code></pre>
            </div>"""

    def _render_card_example(self) -> str:
        """Render card component example."""
        return """
            <div class="example-block">
                <h4>Card</h4>
                <div class="card-demo">
                    <div class="card">
                        <div class="card-header">
                            <h3>Project Alpha</h3>
                            <span class="badge badge-success">Active</span>
                        </div>
                        <div class="card-body">
                            <p>Build the next-generation dashboard with real-time analytics and team collaboration.</p>
                        </div>
                        <div class="card-footer">
                            <button class="btn btn-sm btn-outline">View</button>
                            <button class="btn btn-sm btn-primary">Edit</button>
                        </div>
                    </div>
                </div>
                <pre><code>&lt;Card title="Project Alpha" subtitle="Active"&gt;
  &lt;p&gt;Card content goes here&lt;/p&gt;
&lt;/Card&gt;</code></pre>
            </div>"""

    def _render_modal_example(self) -> str:
        """Render modal component example."""
        return """
            <div class="example-block">
                <h4>Modal</h4>
                <button class="btn btn-primary" onclick="document.getElementById('demo-modal').classList.add('open')">Open Modal</button>
                <div id="demo-modal" class="modal-overlay" onclick="this.classList.remove('open')">
                    <div class="modal" onclick="event.stopPropagation()">
                        <div class="modal-header">
                            <h3>Confirm Action</h3>
                            <button class="btn btn-ghost btn-sm" onclick="this.closest('.modal-overlay').classList.remove('open')">&times;</button>
                        </div>
                        <div class="modal-body">
                            <p>Are you sure you want to proceed with this action?</p>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-outline btn-sm" onclick="this.closest('.modal-overlay').classList.remove('open')">Cancel</button>
                            <button class="btn btn-primary btn-sm">Confirm</button>
                        </div>
                    </div>
                </div>
                <pre><code>&lt;Modal title="Confirm Action" open={isOpen}&gt;
  &lt;p&gt;Modal content&lt;/p&gt;
&lt;/Modal&gt;</code></pre>
            </div>"""

    def _render_alert_examples(self) -> str:
        """Render alert component examples."""
        variants = [
            ("info", "Information", "This is an informational message."),
            ("success", "Success", "Your changes have been saved."),
            ("warning", "Warning", "Please review before proceeding."),
            ("error", "Error", "Something went wrong. Please try again."),
        ]
        alerts = "".join(
            f'<div class="alert alert-{v[0]}"><strong>{v[1]}</strong><p>{v[2]}</p></div>'
            for v in variants
        )
        return f"""
            <div class="example-block">
                <h4>Alerts</h4>
                {alerts}
                <pre><code>&lt;Alert variant="success" title="Success" message="Changes saved" /&gt;</code></pre>
            </div>"""

    def _render_badge_examples(self) -> str:
        """Render badge component examples."""
        variants = ["default", "success", "warning", "error", "info"]
        badges = " ".join(
            f'<span class="badge badge-{v}">{v.title()}</span>'
            for v in variants
        )
        return f"""
            <div class="example-block">
                <h4>Badges</h4>
                <div class="example-row">{badges}</div>
                <pre><code>&lt;Badge text="Active" variant="success" /&gt;</code></pre>
            </div>"""

    def _render_progress_examples(self) -> str:
        """Render progress bar examples."""
        bars = "".join(
            f"""
                <div class="progress-demo">
                    <span class="progress-label">{label}</span>
                    <div class="progress-bar"><div class="progress-fill" style="width: {value}%"></div></div>
                    <span class="progress-value">{value}%</span>
                </div>"""
            for label, value in [("Upload", 65), ("Storage", 82), ("Tasks", 45)]
        )
        return f"""
            <div class="example-block">
                <h4>Progress</h4>
                {bars}
                <pre><code>&lt;Progress value={65} max={100} showLabel /&gt;</code></pre>
            </div>"""

    def _render_typography_tokens(self) -> str:
        """Render typography token reference."""
        typo = self.theme.typography
        tokens = {
            "Font Family (Sans)": typo.font_family_sans,
            "Font Family (Mono)": typo.font_family_mono,
            "Font Size XS": typo.font_size_xs,
            "Font Size SM": typo.font_size_sm,
            "Font Size Base": typo.font_size_base,
            "Font Size LG": typo.font_size_lg,
            "Font Size XL": typo.font_size_xl,
            "Font Size 2XL": typo.font_size_2xl,
            "Font Size 3XL": typo.font_size_3xl,
            "Font Size 4XL": typo.font_size_4xl,
            "Font Weight Normal": str(typo.font_weight_normal),
            "Font Weight Medium": str(typo.font_weight_medium),
            "Font Weight Semibold": str(typo.font_weight_semibold),
            "Font Weight Bold": str(typo.font_weight_bold),
            "Line Height Tight": str(typo.line_height_tight),
            "Line Height Normal": str(typo.line_height_normal),
            "Line Height Relaxed": str(typo.line_height_relaxed),
        }
        return self._render_token_table(tokens)

    def _render_color_tokens(self) -> str:
        """Render color token reference."""
        colors = self.theme.colors
        tokens = {}
        for key, value in colors.__dict__.items():
            tokens[f"colors.{key}"] = value
        return self._render_token_table(tokens)

    def _render_spacing_tokens(self) -> str:
        """Render spacing token reference."""
        spacing = self.theme.spacing
        tokens = {}
        for key, value in spacing.__dict__.items():
            tokens[f"spacing.{key}"] = value
        return self._render_token_table(tokens)

    def _render_elevation_tokens(self) -> str:
        """Render elevation token reference."""
        elevation = self.theme.elevation
        tokens = {}
        for key, value in elevation.__dict__.items():
            tokens[f"elevation.{key}"] = value
        return self._render_token_table(tokens)

    def _render_radius_tokens(self) -> str:
        """Render radius token reference."""
        radius = self.theme.radius
        tokens = {}
        for key, value in radius.__dict__.items():
            tokens[f"radius.{key}"] = value
        return self._render_token_table(tokens)

    def _render_breakpoint_tokens(self) -> str:
        """Render breakpoint token reference."""
        bp = self.theme.breakpoints
        tokens = {}
        for key, value in bp.__dict__.items():
            tokens[f"breakpoints.{key}"] = value
        return self._render_token_table(tokens)

    def _render_motion_tokens(self) -> str:
        """Render motion token reference."""
        motion = self.theme.motion
        tokens = {}
        for key, value in motion.__dict__.items():
            tokens[f"motion.{key}"] = value
        return self._render_token_table(tokens)

    def generate_html(self) -> str:
        """Generate the complete HTML documentation site."""
        # Build navigation
        nav_items = "".join(
            f'<a href="#{s["id"]}" class="nav-link">{self._escape(s["title"])}</a>'
            for s in self._sections
        )

        # Build content sections
        content_parts = []
        for section in self._sections:
            content_parts.append(self._render_section(section))

        sections_html = "".join(content_parts)

        return f"""<!DOCTYPE html>
<html lang="en" data-theme="{self.theme.name}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape(self.title)}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="header-inner">
            <div class="brand">
                <span class="brand-icon">◆</span>
                <span class="brand-text">{self._escape(self.title)}</span>
            </div>
            <div class="header-search">
                <input type="search" id="search" placeholder="Search components... (⌘K)" />
            </div>
            <div class="header-actions">
                <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
                    <span class="theme-icon-light">☀</span>
                    <span class="theme-icon-dark">☾</span>
                </button>
            </div>
        </div>
    </header>

    <div class="site-layout">
        <aside class="sidebar">
            <nav class="sidebar-nav">
                {nav_items}
            </nav>
        </aside>

        <main class="main-content">
            <div class="content-header">
                <h1>{self._escape(self.title)}</h1>
                <p class="lead">A comprehensive dashboard component system with design tokens, interactive components, and responsive layouts.</p>
            </div>
            {sections_html}
        </main>
    </div>

    <script>
        {self._get_js()}
    </script>
</body>
</html>"""

    def _render_section(self, section: dict[str, Any]) -> str:
        """Render a documentation section."""
        section_id = self._escape(section["id"])
        title = self._escape(section["title"])
        description = self._escape(section.get("description", ""))

        # Get content based on section id
        body = ""
        if section_id == "tokens":
            body = self._render_tokens_section()
        elif section_id == "buttons":
            body = self._render_button_examples()
        elif section_id == "forms":
            body = self._render_form_examples()
        elif section_id == "tables":
            body = self._render_table_example()
        elif section_id == "charts":
            body = self._render_chart_examples()
        elif section_id == "cards":
            body = self._render_card_example()
        elif section_id == "modals":
            body = self._render_modal_example()
        elif section_id == "feedback":
            body = self._render_alert_examples() + self._render_badge_examples() + self._render_progress_examples()
        elif section_id == "layout":
            body = self._render_layout_section()

        return f"""
            <section id="{section_id}" class="doc-section">
                <h2>{title}</h2>
                <p class="section-desc">{description}</p>
                {body}
            </section>"""

    def _render_tokens_section(self) -> str:
        """Render the tokens section."""
        return f"""
            <div class="token-group">
                <h3>Colors</h3>
                {self._render_color_tokens()}
            </div>
            <div class="token-group">
                <h3>Typography</h3>
                {self._render_typography_tokens()}
            </div>
            <div class="token-group">
                <h3>Spacing</h3>
                {self._render_spacing_tokens()}
            </div>
            <div class="token-group">
                <h3>Elevation</h3>
                {self._render_elevation_tokens()}
            </div>
            <div class="token-group">
                <h3>Radius</h3>
                {self._render_radius_tokens()}
            </div>
            <div class="token-group">
                <h3>Breakpoints</h3>
                {self._render_breakpoint_tokens()}
            </div>
            <div class="token-group">
                <h3>Motion</h3>
                {self._render_motion_tokens()}
            </div>"""

    def _render_layout_section(self) -> str:
        """Render layout component examples."""
        return """
            <div class="example-block">
                <h4>Container</h4>
                <pre><code>&lt;Container max_width="xl"&gt;
  &lt;!-- Page content --&gt;
&lt;/Container&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Grid</h4>
                <div class="grid-demo">
                    <div class="grid-item">1</div>
                    <div class="grid-item">2</div>
                    <div class="grid-item">3</div>
                    <div class="grid-item">4</div>
                    <div class="grid-item">5</div>
                    <div class="grid-item">6</div>
                </div>
                <pre><code>&lt;Grid columns={3} gap="md"&gt;
  &lt;Card&gt;Item 1&lt;/Card&gt;
  &lt;Card&gt;Item 2&lt;/Card&gt;
  &lt;Card&gt;Item 3&lt;/Card&gt;
&lt;/Grid&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Flex</h4>
                <pre><code>&lt;Flex direction="row" justify="space-between" align="center"&gt;
  &lt;div&gt;Left&lt;/div&gt;
  &lt;div&gt;Right&lt;/div&gt;
&lt;/Flex&gt;</code></pre>
            </div>
            <div class="example-block">
                <h4>Stack</h4>
                <pre><code>&lt;Stack gap="md"&gt;
  &lt;div&gt;Item 1&lt;/div&gt;
  &lt;div&gt;Item 2&lt;/div&gt;
  &lt;div&gt;Item 3&lt;/div&gt;
&lt;/Stack&gt;</code></pre>
            </div>"""

    def _get_css(self) -> str:
        """Get the CSS styles for the documentation site."""
        t = self.theme
        return f"""
        :root {{
            --bg: {t.background};
            --surface: {t.surface};
            --surface-hover: {t.surface_hover};
            --text: {t.text_primary};
            --text-secondary: {t.text_secondary};
            --text-disabled: {t.text_disabled};
            --border: {t.border};
            --border-focus: {t.border_focus};
            --primary: {t.colors.primary_500};
            --primary-hover: {t.colors.primary_600};
            --success: {t.colors.success_500};
            --warning: {t.colors.warning_500};
            --error: {t.colors.error_500};
            --info: {t.colors.info_500};
            --radius: {t.radius.radius_md};
            --radius-sm: {t.radius.radius_sm};
            --radius-lg: {t.radius.radius_lg};
            --shadow: {t.elevation.shadow_md};
            --font: {t.typography.font_family_sans};
            --font-mono: {t.typography.font_family_mono};
            --transition: {t.motion.duration_fast} {t.motion.easing_ease_in_out};
        }}

        [data-theme="dark"] {{
            --bg: {DarkTheme().background};
            --surface: {DarkTheme().surface};
            --surface-hover: {DarkTheme().surface_hover};
            --text: {DarkTheme().text_primary};
            --text-secondary: {DarkTheme().text_secondary};
            --text-disabled: {DarkTheme().text_disabled};
            --border: {DarkTheme().border};
            --border-focus: {DarkTheme().border_focus};
            --primary: {DarkTheme().colors.primary_500};
            --primary-hover: {DarkTheme().colors.primary_600};
            --success: {DarkTheme().colors.success_500};
            --warning: {DarkTheme().colors.warning_500};
            --error: {DarkTheme().colors.error_500};
            --info: {DarkTheme().colors.info_500};
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: var(--font);
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            transition: background var(--transition), color var(--transition);
        }}

        /* Header */
        .site-header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 0 24px;
            height: 60px;
        }}

        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            height: 100%;
            gap: 24px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 1.125rem;
        }}

        .brand-icon {{ color: var(--primary); font-size: 1.5rem; }}

        .header-search {{
            flex: 1;
            max-width: 400px;
        }}

        .header-search input {{
            width: 100%;
            padding: 8px 16px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--bg);
            color: var(--text);
            font-size: 0.875rem;
            transition: border-color var(--transition);
        }}

        .header-search input:focus {{
            outline: none;
            border-color: var(--border-focus);
        }}

        .theme-toggle {{
            background: none;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 6px 10px;
            cursor: pointer;
            font-size: 1rem;
            color: var(--text);
        }}

        .theme-icon-dark {{ display: none; }}
        [data-theme="dark"] .theme-icon-light {{ display: none; }}
        [data-theme="dark"] .theme-icon-dark {{ display: inline; }}

        /* Layout */
        .site-layout {{
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
        }}

        .sidebar {{
            width: 240px;
            flex-shrink: 0;
            position: sticky;
            top: 60px;
            height: calc(100vh - 60px);
            overflow-y: auto;
            padding: 24px 16px;
            border-right: 1px solid var(--border);
        }}

        .sidebar-nav {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .nav-link {{
            display: block;
            padding: 8px 12px;
            color: var(--text-secondary);
            text-decoration: none;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
            transition: all var(--transition);
        }}

        .nav-link:hover {{
            background: var(--surface-hover);
            color: var(--text);
        }}

        .main-content {{
            flex: 1;
            padding: 32px 40px;
            max-width: 900px;
        }}

        .content-header {{
            margin-bottom: 40px;
        }}

        .content-header h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .lead {{
            color: var(--text-secondary);
            font-size: 1.125rem;
        }}

        /* Sections */
        .doc-section {{
            margin-bottom: 48px;
            scroll-margin-top: 80px;
        }}

        .doc-section h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}

        .section-desc {{
            color: var(--text-secondary);
            margin-bottom: 24px;
        }}

        /* Examples */
        .example-block {{
            margin-bottom: 32px;
            padding: 24px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }}

        .example-block h4 {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 16px;
        }}

        .example-row {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 16px;
        }}

        pre {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 16px;
            overflow-x: auto;
            font-family: var(--font-mono);
            font-size: 0.8125rem;
            line-height: 1.5;
        }}

        code {{
            font-family: var(--font-mono);
            font-size: 0.875em;
        }}

        /* Buttons */
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border-radius: var(--radius);
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all var(--transition);
            text-decoration: none;
        }}

        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}

        .btn-primary {{ background: var(--primary); color: white; }}
        .btn-primary:hover:not(:disabled) {{ background: var(--primary-hover); }}

        .btn-secondary {{ background: var(--surface); color: var(--text); border-color: var(--border); }}
        .btn-secondary:hover:not(:disabled) {{ background: var(--surface-hover); }}

        .btn-outline {{ background: transparent; color: var(--primary); border-color: var(--primary); }}
        .btn-outline:hover:not(:disabled) {{ background: var(--primary); color: white; }}

        .btn-ghost {{ background: transparent; color: var(--text); }}
        .btn-ghost:hover:not(:disabled) {{ background: var(--surface-hover); }}

        .btn-danger {{ background: var(--error); color: white; }}
        .btn-danger:hover:not(:disabled) {{ opacity: 0.9; }}

        .btn-sm {{ padding: 4px 10px; font-size: 0.8125rem; }}
        .btn-lg {{ padding: 12px 24px; font-size: 1rem; }}

        /* Forms */
        .form-group {{
            margin-bottom: 16px;
        }}

        .form-group label {{
            display: block;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 4px;
        }}

        .form-input {{
            width: 100%;
            max-width: 300px;
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--bg);
            color: var(--text);
            font-size: 0.875rem;
        }}

        .form-input:focus {{
            outline: none;
            border-color: var(--border-focus);
        }}

        .checkbox-label {{
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }}

        /* Table */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}

        .data-table th {{
            text-align: left;
            padding: 10px 16px;
            border-bottom: 2px solid var(--border);
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .data-table td {{
            padding: 10px 16px;
            border-bottom: 1px solid var(--border);
        }}

        .data-table tr:hover td {{
            background: var(--surface-hover);
        }}

        /* Badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }}

        .badge-default {{ background: var(--surface); color: var(--text); border: 1px solid var(--border); }}
        .badge-success {{ background: color-mix(in srgb, var(--success) 15%, transparent); color: var(--success); }}
        .badge-warning {{ background: color-mix(in srgb, var(--warning) 15%, transparent); color: var(--warning); }}
        .badge-error {{ background: color-mix(in srgb, var(--error) 15%, transparent); color: var(--error); }}
        .badge-info {{ background: color-mix(in srgb, var(--info) 15%, transparent); color: var(--info); }}

        /* Progress */
        .progress-demo {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }}

        .progress-label {{ width: 80px; font-size: 0.875rem; }}
        .progress-bar {{ flex: 1; height: 8px; background: var(--surface); border-radius: 9999px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: var(--primary); border-radius: 9999px; transition: width var(--transition); }}
        .progress-value {{ width: 40px; font-size: 0.8125rem; color: var(--text-secondary); text-align: right; }}

        /* Alerts */
        .alert {{
            padding: 12px 16px;
            border-radius: var(--radius);
            margin-bottom: 12px;
            border: 1px solid;
        }}

        .alert strong {{ display: block; font-weight: 600; margin-bottom: 4px; }}
        .alert p {{ font-size: 0.875rem; margin: 0; }}

        .alert-info {{ background: color-mix(in srgb, var(--info) 10%, transparent); border-color: var(--info); }}
        .alert-success {{ background: color-mix(in srgb, var(--success) 10%, transparent); border-color: var(--success); }}
        .alert-warning {{ background: color-mix(in srgb, var(--warning) 10%, transparent); border-color: var(--warning); }}
        .alert-error {{ background: color-mix(in srgb, var(--error) 10%, transparent); border-color: var(--error); }}

        /* Card */
        .card-demo {{ max-width: 360px; }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }}

        .card-header {{
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }}

        .card-header h3 {{ font-size: 1rem; font-weight: 600; }}
        .card-body {{ padding: 16px; }}
        .card-body p {{ color: var(--text-secondary); font-size: 0.875rem; }}
        .card-footer {{ padding: 12px 16px; display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid var(--border); }}

        /* Modal */
        .modal-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 200;
        }}

        .modal-overlay.open {{ display: flex; }}
        .modal {{ background: var(--surface); border-radius: var(--radius-lg); width: 90%; max-width: 440px; box-shadow: var(--shadow); }}
        .modal-header {{ padding: 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }}
        .modal-header h3 {{ font-size: 1rem; font-weight: 600; }}
        .modal-body {{ padding: 16px; }}
        .modal-footer {{ padding: 12px 16px; display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid var(--border); }}

        /* Charts */
        .chart-placeholder {{
            height: 200px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 16px;
        }}

        .bar-chart-demo {{
            display: flex;
            align-items: flex-end;
            gap: 12px;
            height: 160px;
            padding: 16px;
        }}

        .bar {{
            width: 32px;
            background: var(--primary);
            border-radius: 4px 4px 0 0;
            transition: height var(--transition);
        }}

        .line-chart-demo {{ width: 100%; height: 100%; }}
        .pie-chart-demo {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: conic-gradient(
                var(--primary) 0deg 144deg,
                var(--success) 144deg 252deg,
                var(--warning) 252deg 324deg,
                var(--info) 324deg 360deg
            );
        }}

        /* Token Table */
        .token-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8125rem;
            margin-bottom: 16px;
        }}

        .token-table th {{
            text-align: left;
            padding: 8px 12px;
            background: var(--surface);
            border-bottom: 2px solid var(--border);
            font-weight: 600;
        }}

        .token-table td {{
            padding: 6px 12px;
            border-bottom: 1px solid var(--border);
            font-family: var(--font-mono);
        }}

        .token-group {{ margin-bottom: 32px; }}
        .token-group h3 {{ font-size: 1.125rem; font-weight: 600; margin-bottom: 12px; }}

        /* Grid Demo */
        .grid-demo {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}

        .grid-item {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            text-align: center;
            font-weight: 500;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .sidebar {{ display: none; }}
            .main-content {{ padding: 20px; }}
            .header-search {{ display: none; }}
        }}
        """

    def _get_js(self) -> str:
        """Get the JavaScript for the documentation site."""
        return """
        // Theme toggle
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }

        // Restore theme preference
        (function() {
            const saved = localStorage.getItem('theme');
            if (saved) document.documentElement.setAttribute('data-theme', saved);
        })();

        // Search with keyboard shortcut
        document.addEventListener('keydown', function(e) {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('search').focus();
            }
        });

        // Simple search filter
        document.getElementById('search').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            const sections = document.querySelectorAll('.doc-section');
            sections.forEach(function(section) {
                const text = section.textContent.toLowerCase();
                section.style.display = text.includes(query) ? '' : 'none';
            });
        });
        """

    def generate(self, output_path: str) -> str:
        """Generate and write the documentation site to a file."""
        html_content = self.generate_html()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path


def create_default_site() -> DocsSite:
    """Create a documentation site with all default sections."""
    site = DocsSite()

    site.add_section("tokens", "Design Tokens",
        "Complete reference for all design tokens: colors, typography, spacing, elevation, radius, breakpoints, and motion.")
    site.add_section("buttons", "Buttons",
        "Button components with variants, sizes, and states.")
    site.add_section("forms", "Forms",
        "Form components including inputs, selects, checkboxes, and validation.")
    site.add_section("tables", "Tables",
        "Data table component with sorting and pagination.")
    site.add_section("charts", "Charts",
        "Chart components: bar, line, pie, and area charts.")
    site.add_section("cards", "Cards",
        "Card containers for content grouping.")
    site.add_section("modals", "Modals",
        "Modal dialog components.")
    site.add_section("feedback", "Feedback",
        "Alert, badge, and progress components for user feedback.")
    site.add_section("layout", "Layout",
        "Layout primitives: container, grid, flex, and stack.")

    return site
