"""Visual regression testing — pixel-perfect image diff."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testpilot.models import (
    GateStatus,
    PixelDiffResult,
    QualityGateResult,
    VisualTestResult,
)


class PixelDiffer:
    """Performs pixel-by-pixel image comparison."""

    def __init__(self, threshold: float = 0.1) -> None:
        """Args:
            threshold: Maximum allowed percentage of differing pixels (0-100).
        """
        self.threshold = threshold

    def compare(
        self,
        baseline_path: str | Path,
        current_path: str | Path,
        diff_path: str | Path | None = None,
    ) -> PixelDiffResult:
        """Compare two images pixel by pixel."""
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError(
                "Pillow is not installed. Install with: pip install Pillow"
            )

        baseline = Image.open(baseline_path).convert("RGBA")
        current = Image.open(current_path).convert("RGBA")

        if baseline.size != current.size:
            # Resize current to match baseline for comparison
            current = current.resize(baseline.size, Image.LANCZOS)

        pixels_baseline = baseline.load()
        pixels_current = current.load()
        width, height = baseline.size
        total_pixels = width * height
        diff_pixels = 0

        # Create diff image
        diff_image = Image.new("RGBA", (width, height))
        pixels_diff = diff_image.load()

        for y in range(height):
            for x in range(width):
                pb = pixels_baseline[x, y]
                pc = pixels_current[x, y]
                if pb != pc:
                    diff_pixels += 1
                    # Highlight difference in red
                    pixels_diff[x, y] = (255, 0, 0, 255)
                else:
                    pixels_diff[x, y] = (0, 0, 0, 0)

        diff_percentage = (diff_pixels / total_pixels * 100) if total_pixels else 0.0
        is_match = diff_percentage <= self.threshold

        actual_diff_path = ""
        if diff_path:
            diff_path_obj = Path(diff_path)
            diff_path_obj.parent.mkdir(parents=True, exist_ok=True)
            diff_image.save(str(diff_path_obj))
            actual_diff_path = str(diff_path_obj)

        return PixelDiffResult(
            baseline_path=str(baseline_path),
            current_path=str(current_path),
            diff_path=actual_diff_path,
            total_pixels=total_pixels,
            diff_pixels=diff_pixels,
            diff_percentage=round(diff_percentage, 4),
            is_match=is_match,
            threshold=self.threshold,
        )

    def compare_regions(
        self,
        baseline_path: str | Path,
        current_path: str | Path,
        regions: list[tuple[int, int, int, int]],
    ) -> list[PixelDiffResult]:
        """Compare specific regions of two images."""
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow is not installed.")

        baseline = Image.open(baseline_path).convert("RGBA")
        current = Image.open(current_path).convert("RGBA")

        results = []
        for i, (x1, y1, x2, y2) in enumerate(regions):
            region_baseline = baseline.crop((x1, y1, x2, y2))
            region_current = current.crop((x1, y1, x2, y2))

            # Compare regions using same logic as main compare
            region_diff = self._compare_images(region_baseline, region_current)
            results.append(region_diff)

        return results

    def _compare_images(self: PixelDiffer, baseline: Any, current: Any) -> PixelDiffResult:
        """Compare two already-loaded PIL images."""
        from PIL import Image

        if baseline.size != current.size:
            current = current.resize(baseline.size, Image.LANCZOS)

        pb = baseline.load()
        pc = current.load()
        w, h = baseline.size
        total = w * h
        diff = 0

        for y in range(h):
            for x in range(w):
                if pb[x, y] != pc[x, y]:
                    diff += 1

        pct = (diff / total * 100) if total else 0.0
        return PixelDiffResult(
            baseline_path="",
            current_path="",
            total_pixels=total,
            diff_pixels=diff,
            diff_percentage=round(pct, 4),
            is_match=pct <= self.threshold,
            threshold=self.threshold,
        )


class VisualRegressionRunner:
    """Orchestrates visual regression testing across multiple images."""

    def __init__(
        self,
        baseline_dir: str,
        current_dir: str,
        output_dir: str = "./testpilot-output/visual",
        threshold: float = 0.1,
    ) -> None:
        self.baseline_dir = Path(baseline_dir)
        self.current_dir = Path(current_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.differ = PixelDiffer(threshold=threshold)

    def run_all(self) -> list[VisualTestResult]:
        """Run visual regression on all images in the directories."""
        results = []
        baseline_images = list(self.baseline_dir.glob("*.png")) + list(
            self.baseline_dir.glob("*.jpg")
        )

        for baseline_path in baseline_images:
            current_path = self.current_dir / baseline_path.name
            result = self.run_single(baseline_path, current_path)
            results.append(result)

        return results

    def run_single(
        self,
        baseline_path: str | Path,
        current_path: str | Path,
    ) -> VisualTestResult:
        """Run visual regression on a single image pair."""
        name = Path(baseline_path).stem

        if not Path(baseline_path).exists():
            return VisualTestResult(
                name=name,
                passed=False,
                error_message=f"Baseline not found: {baseline_path}",
            )

        if not Path(current_path).exists():
            return VisualTestResult(
                name=name,
                passed=False,
                error_message=f"Current screenshot not found: {current_path}",
            )

        diff_path = self.output_dir / "diffs" / f"{name}_diff.png"

        try:
            diff_result = self.differ.compare(baseline_path, current_path, diff_path)
            return VisualTestResult(
                name=name,
                passed=diff_result.is_match,
                diff_result=diff_result,
            )
        except Exception as e:
            return VisualTestResult(
                name=name,
                passed=False,
                error_message=str(e),
            )

    def to_quality_gate(self, results: list[VisualTestResult]) -> QualityGateResult:
        """Convert visual regression results to a quality gate result."""
        failed = [r for r in results if not r.passed]
        passed = len(results) - len(failed)

        details: dict[str, Any] = {
            "total_images": len(results),
            "passed": passed,
            "failed": len(failed),
            "failures": [
                {
                    "name": r.name,
                    "diff_percentage": r.diff_result.diff_percentage if r.diff_result else None,
                    "error": r.error_message,
                }
                for r in failed
            ],
        }

        status = GateStatus.PASS if not failed else GateStatus.FAIL
        return QualityGateResult(
            name="visual_regression",
            status=status,
            message=f"{passed}/{len(results)} visual tests passed",
            details=details,
        )

    def save_report(self, results: list[VisualTestResult]) -> Path:
        """Save visual regression report as JSON."""
        report = {
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "diff_percentage": r.diff_result.diff_percentage if r.diff_result else None,
                    "error": r.error_message,
                }
                for r in results
            ],
        }

        report_path = self.output_dir / "visual-report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report_path
