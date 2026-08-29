"""Compliance badge generator for MCPTest."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx

from mcptest.config import Config
from mcptest.models import ComplianceReport


# SVG badge templates
BADGE_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="a">
    <rect width="{width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#a)">
    <path fill="#555" d="M0 0h{vleft}v20H0z"/>
    <path fill="{color}" d="M{vleft} 0h{vright}v20H{vleft}z"/>
    <path fill="url(#b)" d="M0 0h{vwidth}v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{xleft}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{xleft}" y="14">{label}</text>
    <text x="{xright}" y="15" fill="#010101" fill-opacity=".3">{message}</text>
    <text x="{xright}" y="14">{message}</text>
  </g>
</svg>"""


class BadgeGenerator:
    """Generates compliance badges as SVG files.

    Creates shields.io-compatible SVG badges showing the
    MCPTest compliance score and eligibility.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.output_dir = Path(config.output_dir)

    def generate(self, report: ComplianceReport) -> None:
        """Generate compliance badge SVG."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        score = report.overall_score
        if score >= 90:
            color = "#22c55e"  # green
            status = "excellent"
        elif score >= 80:
            color = "#84cc16"  # lime
            status = "great"
        elif score >= 60:
            color = "#f59e0b"  # amber
            status = "good"
        elif score >= 40:
            color = "#f97316"  # orange
            status = "fair"
        else:
            color = "#ef4444"  # red
            status = "poor"

        label = "mcptest"
        message = f"{score:.0f}%25"

        # Calculate text widths for layout
        label_width = len(label) * 6 + 10
        message_width = len(message) * 6 + 10
        total_width = label_width + message_width

        svg = BADGE_TEMPLATE.format(
            width=total_width,
            vleft=label_width,
            vright=message_width,
            vwidth=total_width,
            xleft=label_width // 2,
            xright=label_width + message_width // 2,
            color=color,
            label=label,
            message=message,
        )

        path = self.output_dir / "badge.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"Badge: {path}")

        # Also generate a badge.json for shields.io endpoint
        badge_json = {
            "schemaVersion": 1,
            "label": "mcptest",
            "message": f"{score:.0f}%",
            "color": color.replace("#", ""),
            "labelColor": "#555",
            "namedLogo": "",
            "style": "flat-square",
        }

        import json
        json_path = self.output_dir / "badge.json"
        json_path.write_text(json.dumps(badge_json, indent=2), encoding="utf-8")
        print(f"Badge JSON: {json_path}")
