"""RuleHypothesizer — generate hypotheses about transformation rules from examples.

Given a list of training example pairs, produces ranked hypotheses describing
the input -> output transformation. Each hypothesis has a name, confidence
score, and a human-readable description.

Uses a rule-based approach with pluggable detectors for common ARC-AGI
transformations (color shifts, rotations, reflections, scaling, flood fill,
object extraction, etc.).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .puzzle_parser import Grid, Puzzle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------

@dataclass
class Hypothesis:
    """A single transformation rule hypothesis."""
    name: str
    description: str
    confidence: float = 0.0  # 0.0 to 1.0
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class HypothesisSet:
    """A ranked collection of hypotheses."""
    hypotheses: list[Hypothesis] = field(default_factory=list)
    puzzle_id: str = ""

    def top(self) -> Optional[Hypothesis]:
        if not self.hypotheses:
            return None
        return self.hypotheses[0]

    def sorted_by_confidence(self) -> list[Hypothesis]:
        return sorted(self.hypotheses, key=lambda h: h.confidence, reverse=True)


# ---------------------------------------------------------------------------
# detectors
# ---------------------------------------------------------------------------

DetectionFn = Callable[[Grid, Grid], tuple[bool, float, dict[str, object]]]


def _detect_identity(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is identical to input."""
    if inp.width == out.width and inp.height == out.height and inp.cells == out.cells:
        return True, 0.95, {}
    return False, 0.0, {}


def _detect_color_shift(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is input with a consistent color mapping."""
    if inp.width != out.width or inp.height != out.height:
        return False, 0.0, {}
    if not inp.cells:
        return False, 0.0, {}
    mapping: dict[int, int] = {}
    reverse_mapping: dict[int, int] = {}
    consistent = True
    for ic, oc in zip(inp.cells, out.cells):
        if ic in mapping:
            if mapping[ic] != oc:
                consistent = False
                break
        else:
            if oc in reverse_mapping and reverse_mapping[oc] != ic:
                # two different inputs map to same output - allowed for many-to-one
                pass
            mapping[ic] = oc
            reverse_mapping[oc] = ic
    if consistent and mapping:
        # if all mappings are identity, this is the identity rule, not color shift
        non_identity = {k: v for k, v in mapping.items() if k != v}
        # require that a meaningful fraction of distinct colors are shifted
        # (avoids false positives where only one cell differs)
        if non_identity and len(non_identity) / len(mapping) >= 0.5:
            confidence = 0.8 + 0.1 * (1.0 - len(non_identity) / max(len(mapping), 1))
            return True, min(confidence, 0.95), {"mapping": mapping}
    return False, 0.0, {}


def _detect_rotation(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is a 90/180/270 degree rotation of input."""
    if not inp.cells:
        return False, 0.0, {}

    def rotate_90(g: Grid) -> list[int]:
        new_cells = []
        for c in range(g.width):
            for r in range(g.height - 1, -1, -1):
                new_cells.append(g.cells[r * g.width + c])
        return new_cells

    def rotate_180(g: Grid) -> list[int]:
        return list(reversed(g.cells))

    def rotate_270(g: Grid) -> list[int]:
        new_cells = []
        for c in range(g.width - 1, -1, -1):
            for r in range(g.height):
                new_cells.append(g.cells[r * g.width + c])
        return new_cells

    # 90 degree: width <-> height
    rot90 = rotate_90(inp)
    if rot90 == out.cells and inp.width == out.height and inp.height == out.width:
        return True, 0.9, {"angle": 90}

    # 180 degree
    rot180 = rotate_180(inp)
    if rot180 == out.cells and inp.width == out.width and inp.height == out.height:
        return True, 0.9, {"angle": 180}

    # 270 degree
    rot270 = rotate_270(inp)
    if rot270 == out.cells and inp.width == out.height and inp.height == out.width:
        return True, 0.9, {"angle": 270}

    return False, 0.0, {}


def _detect_reflection(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is a horizontal or vertical reflection of input."""
    if inp.width != out.width or inp.height != out.height:
        return False, 0.0, {}
    if not inp.cells:
        return False, 0.0, {}

    # horizontal flip (flip rows)
    h_flip = []
    for r in range(inp.height):
        row = inp.cells[r * inp.width:(r + 1) * inp.width]
        h_flip.extend(reversed(row))
    if h_flip == out.cells:
        return True, 0.85, {"axis": "horizontal"}

    # vertical flip (flip columns)
    v_flip = []
    for r in range(inp.height - 1, -1, -1):
        v_flip.extend(inp.cells[r * inp.width:(r + 1) * inp.width])
    if v_flip == out.cells:
        return True, 0.85, {"axis": "vertical"}

    return False, 0.0, {}


def _detect_scaling(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is a scaled version of input (uniform factor)."""
    if not inp.cells or not out.cells:
        return False, 0.0, {}

    # check if out is a scaled-up version
    if out.width % inp.width == 0 and out.height % inp.height == 0:
        sx = out.width // inp.width
        sy = out.height // inp.height
        if sx == sy and sx > 1:
            # verify each cell is replicated sx times in both dimensions
            consistent = True
            for oy in range(out.height):
                for ox in range(out.width):
                    src_x = ox // sx
                    src_y = oy // sx
                    if out.cells[oy * out.width + ox] != inp.cells[src_y * inp.width + src_x]:
                        consistent = False
                        break
                if not consistent:
                    break
            if consistent:
                return True, 0.85, {"scale_factor": sx}

    # check if out is a scaled-down version
    if inp.width % out.width == 0 and inp.height % out.height == 0:
        sx = inp.width // out.width
        sy = inp.height // out.height
        if sx == sy and sx > 1:
            consistent = True
            for oy in range(out.height):
                for ox in range(out.width):
                    src_x = ox * sx
                    src_y = oy * sx
                    if out.cells[oy * out.width + ox] != inp.cells[src_y * inp.width + src_x]:
                        consistent = False
                        break
                if not consistent:
                    break
            if consistent:
                return True, 0.85, {"scale_factor": -sx}  # negative = downscale

    return False, 0.0, {}


def _detect_flood_fill(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is a flood fill from a seed point."""
    if inp.width != out.width or inp.height != out.height:
        return False, 0.0, {}
    if not inp.cells:
        return False, 0.0, {}

    # find cells that changed
    changed = [(i, inp.cells[i], out.cells[i]) for i in range(len(inp.cells)) if inp.cells[i] != out.cells[i]]
    if not changed:
        return False, 0.0, {}

    # all changed cells should have the same output color
    target_color = changed[0][2]
    if any(c[2] != target_color for c in changed):
        return False, 0.0, {}

    # the changed cells should form a connected region
    # simple check: all changed cells are connected (4-connectivity)
    changed_positions = {i for i, _, _ in changed}
    if not changed_positions:
        return False, 0.0, {}

    # BFS from first changed cell
    start = next(iter(changed_positions))
    visited = set()
    queue = [start]
    while queue:
        pos = queue.pop()
        if pos in visited:
            continue
        visited.add(pos)
        r, c = divmod(pos, inp.width)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < inp.height and 0 <= nc < inp.width:
                npos = nr * inp.width + nc
                if npos in changed_positions and npos not in visited:
                    queue.append(npos)

    if visited == changed_positions:
        return True, 0.7, {"target_color": target_color, "filled_count": len(changed)}
    return False, 0.0, {}


def _detect_crop_to_content(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is the bounding box of non-zero content in input."""
    if not inp.cells or not out.cells:
        return False, 0.0, {}

    # find bounding box of non-zero cells in input
    non_zero_rows = []
    non_zero_cols = []
    for r in range(inp.height):
        for c in range(inp.width):
            if inp.cells[r * inp.width + c] != 0:
                non_zero_rows.append(r)
                non_zero_cols.append(c)

    if not non_zero_rows:
        return False, 0.0, {}

    min_r, max_r = min(non_zero_rows), max(non_zero_rows)
    min_c, max_c = min(non_zero_cols), max(non_zero_cols)

    expected_h = max_r - min_r + 1
    expected_w = max_c - min_c + 1

    if out.height != expected_h or out.width != expected_w:
        return False, 0.0, {}

    # verify the crop matches
    for oy in range(out.height):
        for ox in range(out.width):
            src_r = min_r + oy
            src_c = min_c + ox
            if out.cells[oy * out.width + ox] != inp.cells[src_r * inp.width + src_c]:
                return False, 0.0, {}

    return True, 0.8, {"bbox": (min_r, min_c, max_r, max_c)}


def _detect_padding(inp: Grid, out: Grid) -> tuple[bool, float, dict[str, object]]:
    """Check if output is input with added border/padding."""
    if not inp.cells or not out.cells:
        return False, 0.0, {}
    if out.width < inp.width or out.height < inp.height:
        return False, 0.0, {}

    # check if input is centered in output with a uniform border
    border_color = out.cells[0]
    # verify border is uniform
    for i in range(out.width):
        if out.cells[i] != border_color or out.cells[(out.height - 1) * out.width + i] != border_color:
            return False, 0.0, {}
    for i in range(out.height):
        if out.cells[i * out.width] != border_color or out.cells[i * out.width + out.width - 1] != border_color:
            return False, 0.0, {}

    # check inner content matches input
    offset_r = (out.height - inp.height) // 2
    offset_c = (out.width - inp.width) // 2
    for r in range(inp.height):
        for c in range(inp.width):
            if out.cells[(r + offset_r) * out.width + (c + offset_c)] != inp.cells[r * inp.width + c]:
                return False, 0.0, {}

    return True, 0.8, {"border_color": border_color, "offset": (offset_r, offset_c)}


# ---------------------------------------------------------------------------
# hypothesizer
# ---------------------------------------------------------------------------

class RuleHypothesizer:
    """Generate ranked hypotheses about transformation rules.

    Uses a set of pluggable detectors to identify common ARC-AGI-3
    transformations. Each detector returns (matched, confidence, metadata).
    The hypothesizer aggregates results across all training examples and
    ranks hypotheses by average confidence.
    """

    DEFAULT_DETECTORS: list[DetectionFn] = [
        _detect_identity,
        _detect_color_shift,
        _detect_rotation,
        _detect_reflection,
        _detect_scaling,
        _detect_flood_fill,
        _detect_crop_to_content,
        _detect_padding,
    ]

    def __init__(
        self,
        detectors: Optional[list[DetectionFn]] = None,
        min_confidence: float = 0.3,
    ) -> None:
        self.detectors = detectors if detectors is not None else self.DEFAULT_DETECTORS
        self.min_confidence = min_confidence
        self._hypothesis_count = 0

    def hypothesize(self, puzzle: Puzzle) -> HypothesisSet:
        """Generate hypotheses for a puzzle.

        Args:
            puzzle: a parsed Puzzle object.

        Returns:
            A ranked HypothesisSet.
        """
        self._hypothesis_count += 1
        logger.info("hypothesize_start puzzle_id=%s", puzzle.puzzle_id)

        if not puzzle.train:
            logger.warning("hypothesize_empty puzzle_id=%s", puzzle.puzzle_id)
            return HypothesisSet(puzzle_id=puzzle.puzzle_id)

        # aggregate detector results across all training pairs
        detector_scores: dict[str, list[float]] = {}
        detector_metadata: dict[str, list[dict[str, object]]] = {}

        for pair in puzzle.train:
            for detector in self.detectors:
                name = detector.__name__
                matched, confidence, meta = detector(pair.input_grid, pair.output_grid)
                if matched:
                    if name not in detector_scores:
                        detector_scores[name] = []
                        detector_metadata[name] = []
                    detector_scores[name].append(confidence)
                    detector_metadata[name].append(meta)

        # build hypotheses from aggregated scores
        hypotheses: list[Hypothesis] = []
        for name, scores in detector_scores.items():
            avg_confidence = sum(scores) / len(scores)
            if avg_confidence >= self.min_confidence:
                # clean up name
                clean_name = name.replace("_detect_", "").replace("_", " ").title()
                meta_list = detector_metadata[name]
                # merge metadata from all matches
                merged_meta: dict[str, object] = {}
                for m in meta_list:
                    for k, v in m.items():
                        if k not in merged_meta:
                            merged_meta[k] = v
                        else:
                            if merged_meta[k] != v:
                                merged_meta[k] = [merged_meta[k], v]

                hyp = Hypothesis(
                    name=clean_name,
                    description=f"Detected {clean_name.lower()} transformation "
                               f"(matched {len(scores)}/{len(puzzle.train)} examples, "
                               f"confidence={avg_confidence:.2f})",
                    confidence=avg_confidence,
                    metadata=merged_meta,
                )
                hypotheses.append(hyp)

        # sort by confidence descending
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)

        result = HypothesisSet(hypotheses=hypotheses, puzzle_id=puzzle.puzzle_id)
        logger.info(
            "hypothesize_done puzzle_id=%s hypotheses=%d",
            puzzle.puzzle_id, len(hypotheses),
        )
        return result

    @property
    def hypothesis_count(self) -> int:
        return self._hypothesis_count
