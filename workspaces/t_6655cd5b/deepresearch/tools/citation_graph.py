"""
Citation graph analyzer for gap detection.

Builds a directed graph of paper citation relationships and
identifies under-researched areas (gaps) using network analysis.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from deepresearch.state import PaperMetadata


class CitationGraphAnalyzer:
    """Analyzes citation relationships to identify research gaps."""

    def __init__(self):
        self.graph: dict[str, list[str]] = defaultdict(list)  # paper_id -> cited_paper_ids
        self.reverse_graph: dict[str, list[str]] = defaultdict(list)  # paper_id -> citing_paper_ids
        self.papers: dict[str, PaperMetadata] = {}
        self.in_degree: dict[str, int] = defaultdict(int)
        self.out_degree: dict[str, int] = defaultdict(int)

    def add_paper(self, paper_id: str, metadata: PaperMetadata) -> None:
        """Add a paper and its reference list to the graph."""
        self.papers[paper_id] = metadata
        refs = metadata.get("references", []) or []
        self.graph[paper_id] = list(refs)
        self.out_degree[paper_id] = len(refs)
        for ref_id in refs:
            self.reverse_graph[ref_id].append(paper_id)
            self.in_degree[ref_id] += 1

    def build_from_papers(self, papers: list[PaperMetadata]) -> None:
        """Build the citation graph from a list of papers."""
        for p in papers:
            pid = p.get("arxiv_id") or p.get("pubmed_id") or p.get("doi", "")
            if pid:
                self.add_paper(pid, p)

    def identify_gaps(self, min_citations: int = 1) -> list[str]:
        """Identify papers with low betweenness centrality (potential gaps).

        Papers that are rarely cited by others (low in-degree) but
        cite many papers (high out-degree) may be foundational works
        that haven't been built upon — indicating a gap.
        """
        gaps = []
        for pid, meta in self.papers.items():
            in_deg = self.in_degree.get(pid, 0)
            if in_deg <= min_citations:
                gaps.append(pid)
        return gaps

    def find_foundation_papers(self) -> list[str]:
        """Find papers with high out-degree but potentially low in-degree.

        These are papers that synthesize many sources but aren't
        themselves widely cited.
        """
        foundation = []
        for pid in self.papers:
            out_deg = self.out_degree.get(pid, 0)
            in_deg = self.in_degree.get(pid, 0)
            if out_deg >= 3 and in_deg < out_deg * 0.5:
                foundation.append(pid)
        return foundation

    def get_citation_chain(self, paper_id: str, depth: int = 3) -> list[str]:
        """Get the citation chain for a paper up to a given depth."""
        visited = set()
        chain = []

        def _dfs(pid: str, d: int):
            if d <= 0 or pid in visited:
                return
            visited.add(pid)
            chain.append(pid)
            for ref in self.graph.get(pid, []):
                _dfs(ref, d - 1)

        _dfs(paper_id, depth)
        return chain

    def gap_score(self, paper_id: str) -> float:
        """Compute a gap score for a paper (0.0 = well-researched, 1.0 = gap).

        Higher scores indicate the paper may be in an under-researched area.
        """
        in_deg = self.in_degree.get(paper_id, 0)
        out_deg = self.out_degree.get(paper_id, 0)

        if in_deg == 0 and out_deg == 0:
            return 1.0

        # Normalize: a paper with high out-degree but low in-degree
        # suggests it cites many things but nothing cites it back
        ratio = in_deg / (in_deg + out_deg)
        # Invert: lower ratio = higher gap score
        return max(0.0, min(1.0, 1.0 - ratio))

    def summary(self) -> dict[str, Any]:
        """Return a summary of the citation graph."""
        return {
            "total_papers": len(self.papers),
            "total_edges": sum(len(v) for v in self.graph.values()),
            "avg_in_degree": (
                sum(self.in_degree.values()) / len(self.papers) if self.papers else 0
            ),
            "avg_out_degree": (
                sum(self.out_degree.values()) / len(self.papers) if self.papers else 0
            ),
            "foundation_papers": self.find_foundation_papers(),
            "gap_papers": self.identify_gaps(),
        }
