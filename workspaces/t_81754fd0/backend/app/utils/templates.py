"""Template rendering engine for multi-framework code generation."""
from __future__ import annotations

from typing import Any


class TemplateEngine:
    """Renders code templates for different frameworks."""

    THEMES: dict[str, dict[str, str]] = {
        "default": {
            "primary": "#3b82f6",
            "secondary": "#64748b",
            "bg": "#ffffff",
            "text": "#1e293b",
            "border": "#e2e8f0",
            "radius": "6px",
        },
        "dark": {
            "primary": "#60a5fa",
            "secondary": "#94a3b8",
            "bg": "#0f172a",
            "text": "#f1f5f9",
            "border": "#334155",
            "radius": "6px",
        },
        "modern": {
            "primary": "#8b5cf6",
            "secondary": "#a78bfa",
            "bg": "#fafafa",
            "text": "#18181b",
            "border": "#e4e4e7",
            "radius": "12px",
        },
        "minimal": {
            "primary": "#000000",
            "secondary": "#666666",
            "bg": "#ffffff",
            "text": "#000000",
            "border": "#eeeeee",
            "radius": "0px",
        },
    }

    def _theme_vars(self, theme: str) -> dict[str, str]:
        return self.THEMES.get(theme, self.THEMES["default"])

    def render_html(self, body: str, theme: str, responsive: bool, accessible: bool) -> str:
        """Render a complete HTML document."""
        t = self._theme_vars(theme)
        viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">' if responsive else ''
        lang = 'lang="en"' if accessible else ''
        a11y_role = 'role="main"' if accessible else ''

        return f"""<!DOCTYPE html>
<html {lang}>
<head>
  <meta charset="UTF-8">
  {viewport}
  <title>Generated UI</title>
  <style>
    :root {{
      --color-primary: {t['primary']};
      --color-secondary: {t['secondary']};
      --color-bg: {t['bg']};
      --color-text: {t['text']};
      --color-border: {t['border']};
      --radius: {t['radius']};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--color-bg); color: var(--color-text); }}
    .ui-container {{ max-width: 1200px; margin: 0 auto; padding: 1rem; }}
  </style>
</head>
<body>
  <div class="ui-container" {a11y_role}>
    {body}
  </div>
</body>
</html>"""

    def render_css(self, theme: str, responsive: bool) -> str:
        """Render framework-agnostic CSS."""
        t = self._theme_vars(theme)
        responsive_css = """
@media (max-width: 768px) {
  .ui-container { padding: 0.5rem; }
  .ui-grid { grid-template-columns: 1fr !important; }
}
@media (max-width: 480px) {
  .ui-container { padding: 0.25rem; }
}
""" if responsive else ""

        return f""":root {{
  --color-primary: {t['primary']};
  --color-secondary: {t['secondary']};
  --color-bg: {t['bg']};
  --color-text: {t['text']};
  --color-border: {t['border']};
  --radius: {t['radius']};
}}

/* Base */
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--color-bg); color: var(--color-text); line-height: 1.6; }}
.ui-container {{ max-width: 1200px; margin: 0 auto; padding: 1rem; }}

/* Components */
.ui-button {{ background: var(--color-primary); color: white; border: none; padding: 0.5rem 1rem; border-radius: var(--radius); cursor: pointer; }}
.ui-input {{ border: 1px solid var(--color-border); padding: 0.5rem; border-radius: var(--radius); width: 100%; }}
.ui-card {{ background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius); padding: 1rem; }}
.ui-badge {{ display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; background: var(--color-secondary); color: white; }}
.ui-heading {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }}
.ui-text {{ font-size: 1rem; line-height: 1.6; }}
.ui-grid {{ display: grid; gap: 1rem; }}
.ui-flex {{ display: flex; gap: 1rem; }}
.ui-navbar {{ display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; background: var(--color-bg); border-bottom: 1px solid var(--color-border); }}
{responsive_css}"""

    def render_react(self, body_html: str, components: list[str], names: list[str]) -> str:
        """Render React/JSX code."""
        imports = "\n".join([f"import {{ {name} }} from './{name}';" for name in names if name])
        return f"""import React from 'react';

{imports}

export default function GeneratedUI() {{
  return (
    <div className="ui-container">
{chr(10).join(f'      <{name} />' for name in names if name)}
    </div>
  );
}}
"""

    def render_vue(self, body_html: str, components: list[str], names: list[str]) -> str:
        """Render Vue SFC code."""
        imports = "\n".join([f"import {name} from './{name}.vue';" for name in names if name])
        return f"""<template>
  <div class="ui-container">
{chr(10).join(f'    <{name} />' for name in names if name)}
  </div>
</template>

<script setup lang="ts">
{imports}
</script>

<style scoped>
.ui-container {{ max-width: 1200px; margin: 0 auto; padding: 1rem; }}
</style>
"""

    def render_angular(self, body_html: str, components: list[str], names: list[str]) -> str:
        """Render Angular component code."""
        selector = "app-generated-ui"
        template = "\n".join([f"    <app-{name.lower()}></app-{name.lower()}>" for name in names if name])
        return f"""import {{ Component }} from '@angular/core';

@Component({{
  selector: '{selector}',
  template: `
    <div class="ui-container">
{template}
    </div>
  `,
  styles: [`
    .ui-container {{ max-width: 1200px; margin: 0 auto; padding: 1rem; }}
  `]
}})
export class GeneratedUIComponent {{}}
"""
