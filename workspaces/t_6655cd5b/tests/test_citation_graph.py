"""Tests for CitationGraphAnalyzer."""

import pytest
from deepresearch.tools.citation_graph import CitationGraphAnalyzer
from deepresearch.state import PaperMetadata


@pytest.fixture
def sample_papers():
    return [
        PaperMetadata(
            arxiv_id="paper_A",
            title="Paper A",
            authors=["Alice"],
            abstract="Abstract A",
            year=2023,
            venue="ArXiv",
            doi="",
            citations=10,
            references=["paper_B", "paper_C"],
            url="",
        ),
        PaperMetadata(
            arxiv_id="paper_B",
            title="Paper B",
            authors=["Bob"],
            abstract="Abstract B",
            year=2022,
            venue="ArXiv",
            doi="",
            citations=5,
            references=["paper_C"],
            url="",
        ),
        PaperMetadata(
            arxiv_id="paper_C",
            title="Paper C",
            authors=["Carol"],
            abstract="Abstract C",
            year=2021,
            venue="ArXiv",
            doi="",
            citations=20,
            references=[],
            url="",
        ),
        PaperMetadata(
            arxiv_id="paper_D",
            title="Paper D",
            authors=["Dave"],
            abstract="Abstract D",
            year=2020,
            venue="ArXiv",
            doi="",
            citations=0,
            references=[],
            url="",
        ),
    ]


class TestCitationGraph:
    def test_build_from_papers(self, sample_papers):
        analyzer = CitationGraphAnalyzer()
        analyzer.build_from_papers(sample_papers)
        assert analyzer.papers["paper_A"]["title"] == "Paper A"
        assert analyzer.papers["paper_B"]["title"] == "Paper B"

    def test_add_paper(self):
        analyzer = CitationGraphAnalyzer()
        meta = PaperMetadata(
            arxiv_id="test",
            title="Test",
            authors=[],
            abstract="",
            year=2024,
            venue="",
            doi="",
            citations=0,
            references=["ref1", "ref2"],
            url="",
        )
        analyzer.add_paper("test", meta)
        assert "test" in analyzer.papers
        assert analyzer.graph["test"] == ["ref1", "ref2"]
        assert analyzer.out_degree["test"] == 2

    def test_reverse_graph(self, sample_papers):
        analyzer = CitationGraphAnalyzer()
        analyzer.build_from_papers(sample_papers)
        # paper_A cites paper_B and paper_C
        assert "paper_A" in analyzer.reverse_graph["paper_B"]
        assert "paper_A" in analyzer.reverse_graph["paper_C"]
        # paper_B cites paper_C
        assert "paper_B" in analyzer.reverse_graph["paper_C"]

    def test_identify_gaps(self, sample_papers):
        analyzer = CitationGraphAnalyzer()
        analyzer.build_from_papers(sample_papers)
        gaps = analyzer.identify_gaps(min_citations=5)
        # paper_D has 0 citations, paper_A has 0 in-citations (cites others but not cited by them)
        assert "paper_D" in gaps



    def test_get_citation_chain(self, sample_papers):
        analyzer = CitationGraphAnalyzer()
        analyzer.build_from_papers(sample_papers)
        chain = analyzer.get_citation_chain("paper_A", depth=3)
        assert "paper_A" in chain
        assert "paper_B" in chain
        assert "paper_C" in chain

    def test_gap_score(self, sample_papers):
        analyzer = CitationGraphAnalyzer()
        analyzer.build_from_papers(sample_papers)
        score_d = analyzer.gap_score("paper_D")
        assert score_d == 1.0  # No in or out edges

    def test_summary(self, sample_papers):
        analyzer = CitationGraphAnalyzer()
        analyzer.build_from_papers(sample_papers)
        s = analyzer.summary()
        assert s["total_papers"] == 4
        assert s["total_edges"] == 3  # A->B, A->C, B->C
        assert isinstance(s["foundation_papers"], list)
        assert isinstance(s["gap_papers"], list)
