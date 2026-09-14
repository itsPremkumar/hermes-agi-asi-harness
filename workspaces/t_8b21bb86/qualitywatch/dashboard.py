"""Rich-based terminal dashboard for quality scores."""
from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from qualitywatch.models import CheckResult, QualityProfile
from qualitywatch.scoring import compute_score


class Dashboard:
    """Terminal dashboard for quality monitoring."""

    def __init__(self) -> None:
        self.console = Console()

    def render_score(self, score_info: dict[str, Any], title: str = "Quality Score") -> None:
        score = score_info["score"]
        bar_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        bar = Text()
        blocks = int(score / 5)
        bar.append("█" * blocks, style=bar_color)
        bar.append("░" * (20 - blocks), style="dim")

        table = Table(title=title, expand=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Score", f"{score}/100")
        table.add_row("Bar", bar)
        table.add_row("Passed", str(score_info.get("passed", 0)))
        table.add_row("Failed", str(score_info.get("failed", 0)))
        table.add_row("Skipped", str(score_info.get("skipped", 0)))
        self.console.print(table)

    def render_results(self, results: list[CheckResult]) -> None:
        table = Table(title="Check Results", expand=False)
        table.add_column("Rule", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Status", style="green")
        table.add_column("Severity", style="yellow")
        table.add_column("Message", style="dim")

        for r in results:
            status_color = "green" if r.status.value == "pass" else "red" if r.status.value == "fail" else "yellow"
            table.add_row(
                r.rule_name,
                r.rule_type,
                f"[{status_color}]{r.status.value}[/{status_color}]",
                r.severity.value,
                r.message,
            )
        self.console.print(table)

    def render_profile(self, profile: QualityProfile) -> None:
        table = Table(title=f"Profile: {profile.dataset_name}", expand=False)
        table.add_column("Column", style="cyan")
        table.add_column("Nulls", style="red")
        table.add_column("Uniqueness", style="green")
        table.add_column("Stats", style="white")

        for col in profile.stats:
            s = profile.stats[col]
            stat_str = ", ".join(f"{k}={v}" for k, v in s.items() if k != "dtype")
            table.add_row(col, str(profile.null_counts.get(col, 0)), f"{profile.uniqueness.get(col, 0):.2%}", stat_str)
        self.console.print(table)

    def render(self, score_info: dict[str, Any], results: list[CheckResult], profile: QualityProfile | None = None) -> None:
        self.render_score(score_info)
        self.console.print()
        self.render_results(results)
        if profile:
            self.console.print()
            self.render_profile(profile)