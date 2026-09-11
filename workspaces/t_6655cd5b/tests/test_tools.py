"""Tests for deepresearch.tools."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from deepresearch.tools.arxiv_api import ArxivAPI
from deepresearch.tools.pubmed_api import PubMedAPI
from deepresearch.tools.citation_graph import CitationGraphAnalyzer
from deepresearch.config import ResearchConfig


class TestArxivAPI:
    """Tests for ArxivAPI tool."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        api = ArxivAPI(email=config.arxiv_email, max_results=config.arxiv_max_results)
        assert api.email == config.arxiv_email
        assert api.max_results == config.arxiv_max_results

    def test_search_returns_results(self):
        """Test search returns paper metadata."""
        api = ArxivAPI()
        with patch.object(api, "_parse_feed", return_value=[
            {"arxiv_id": "test.123", "title": "Test Paper", "authors": ["Alice"], "abstract": "Test abstract", "published": "2025-01-01", "year": 2025, "links": []},
        ]):
            with patch("deepresearch.providers.llm.httpx.get") as mock_get:
                mock_response = MagicMock()
                mock_response.text = "<feed></feed>"
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response
                results = api.search("test query", max_results=5)
                assert len(results) > 0

    def test_search_fallback_to_mock(self):
        """Test search falls back to mock on network error."""
        api = ArxivAPI()
        with patch("deepresearch.providers.llm.httpx.get", side_effect=Exception("Network error")):
            results = api.search("test query", max_results=5)
            assert len(results) == 5
            assert results[0]["title"] != ""

    def test_parse_feed(self):
        """Test parsing arXiv Atom feed XML."""
        api = ArxivAPI()
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/cs/0501021</id>
                <title>Attention Is All You Need</title>
                <summary>This paper introduces the Transformer architecture.</summary>
                <author><name>Ashish Vaswani</name></author>
                <author><name>Noam Shazeer</name></author>
                <published>2017-06-12</published>
                <category term="cs.CL" />
                <category term="cs.AI" />
            </entry>
        </feed>"""
        papers = api._parse_feed(feed_xml)
        assert len(papers) == 1
        assert papers[0]["title"] == "Attention Is All You Need"
        assert "Ashish Vaswani" in papers[0]["authors"]
        assert papers[0]["year"] == 2017

    def test_parse_feed_empty(self):
        """Test parsing empty feed."""
        api = ArxivAPI()
        empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        </feed>"""
        papers = api._parse_feed(empty_xml)
        assert len(papers) == 0

    def test_fetch_paper(self):
        """Test fetching a specific paper."""
        api = ArxivAPI()
        with patch.object(api, "_parse_feed", return_value=[
            {"arxiv_id": "test.123", "title": "Test Paper", "authors": ["Alice"], "abstract": "Test abstract", "published": "2025-01-01", "year": 2025, "links": []},
        ]):
            with patch("deepresearch.providers.llm.httpx.get") as mock_get:
                mock_response = MagicMock()
                mock_response.text = "<feed></feed>"
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response
                paper = api.fetch_paper("test.123")
                assert paper["title"] == "Test Paper"

    def test_fetch_paper_fallback(self):
        """Test fetch falls back to mock on error."""
        api = ArxivAPI()
        with patch("deepresearch.providers.llm.httpx.get", side_effect=Exception("Network error")):
            paper = api.fetch_paper("test.123")
            assert paper["title"] == "Paper test.123"


class TestPubMedAPI:
    """Tests for PubMedAPI tool."""

    def test_init(self):
        """Test initialization."""
        config = ResearchConfig()
        api = PubMedAPI(email=config.arxiv_email, max_results=config.pubmed_max_results)
        assert api.email == config.arxiv_email
        assert api.max_results == config.pubmed_max_results

    def test_search_returns_results(self):
        """Test search returns article metadata."""
        api = PubMedAPI()
        with patch("deepresearch.providers.llm.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            with patch.object(api, "_parse_xml", return_value=[
                {"pubmed_id": "12345678", "title": "Test Article", "authors": ["Jane Doe"], "abstract": "Test abstract", "year": 2025, "links": []},
            ]):
                results = api.search("test query", max_results=5)
                assert len(results) > 0

    def test_search_fallback_to_mock(self):
        """Test search falls back to mock on network error."""
        api = PubMedAPI()
        with patch("deepresearch.providers.llm.httpx.get", side_effect=Exception("Network error")):
            results = api.search("test query", max_results=5)
            assert len(results) == 5
            assert results[0]["title"] != ""

    def test_parse_xml(self):
        """Test parsing PubMed XML."""
        api = PubMedAPI()
        xml_text = """<?xml version="1.0" encoding="utf-8"?>
        <MedlineCitationSet>
            <MedlineCitation Status="Publisher">
                <PMID>12345678</PMID>
                <Article>
                    <ArticleTitle>Machine Learning in Healthcare</ArticleTitle>
                    <AuthorList>
                        <Author>
                            <LastName>Doe</LastName>
                            <ForeName>Jane</ForeName>
                        </Author>
                    </AuthorList>
                    <ArticleDate>
                        <Date Year="2020" />
                    </ArticleDate>
                    <MeshHeadingList>
                        <MeshHeading>
                            <DescriptorName>Machine Learning</DescriptorName>
                        </MeshHeading>
                    </MeshHeadingList>
                    <OtherAbstract>
                        <AbstractText>This paper discusses ML applications in healthcare.</AbstractText>
                    </OtherAbstract>
                </Article>
            </MedlineCitation>
        </MedlineCitationSet>"""
        papers = api._parse_xml(xml_text, ["12345678"])
        assert len(papers) == 1
        assert papers[0]["title"] == "Machine Learning in Healthcare"
        assert "Doe" in papers[0]["authors"][0]
        assert papers[0]["year"] == 2020

    def test_parse_xml_empty(self):
        """Test parsing empty PubMed XML."""
        api = PubMedAPI()
        empty_xml = """<?xml version="1.0" encoding="utf-8"?>
        <MedlineCitationSet>
        </MedlineCitationSet>"""
        papers = api._parse_xml(empty_xml, [])
        assert len(papers) == 0

    def test_fetch_article(self):
        """Test fetching a specific article."""
        api = PubMedAPI()
        with patch("deepresearch.providers.llm.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<MedlineCitationSet></MedlineCitationSet>"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            article = api.fetch_article("12345678")
            assert article["pubmed_id"] == "12345678"


class TestCitationGraphAnalyzer:
    """Tests for CitationGraphAnalyzer tool."""

    def test_init(self):
        """Test initialization."""
        analyzer = CitationGraphAnalyzer()
        assert analyzer.graph is not None
        assert len(analyzer.graph) == 0

    def test_add_paper(self):
        """Test adding a paper to the graph."""
        analyzer = CitationGraphAnalyzer()
        paper = {"arxiv_id": "p1", "title": "Paper 1", "references": ["p2", "p3"]}
        analyzer.add_paper("p1", paper)
        assert "p1" in analyzer.graph
        assert "p2" in analyzer.graph["p1"]
        assert "p3" in analyzer.graph["p1"]

    def test_build_from_papers(self):
        """Test building graph from papers."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "p1", "title": "Paper 1", "references": ["p2", "p3"]},
            {"arxiv_id": "p2", "title": "Paper 2", "references": ["p3"]},
        ]
        analyzer.build_from_papers(papers)
        assert "p1" in analyzer.graph
        assert "p2" in analyzer.graph
        assert "p2" in analyzer.graph["p1"]
        assert "p3" in analyzer.graph["p1"]
        assert "p3" in analyzer.graph["p2"]

    def test_identify_gaps(self):
        """Test gap identification."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "p1", "title": "Paper 1", "references": []},
            {"arxiv_id": "p2", "title": "Paper 2", "references": []},
        ]
        analyzer.build_from_papers(papers)
        gaps = analyzer.identify_gaps()
        assert len(gaps) >= 1  # Both papers have 0 citations

    def test_identify_gaps_no_gaps(self):
        """Test when no gaps exist."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "p1", "title": "P1", "references": ["p2", "p3"]},
            {"arxiv_id": "p2", "title": "P2", "references": ["p1", "p3"]},
            {"arxiv_id": "p3", "title": "P3", "references": ["p1", "p2"]},
        ]
        analyzer.build_from_papers(papers)
        gaps = analyzer.identify_gaps()
        # All papers have 2+ citations
        assert len(gaps) == 0

    def test_find_foundation_papers(self):
        """Test finding foundation papers."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "p1", "title": "P1", "references": ["p2", "p3", "p4"]},
            {"arxiv_id": "p2", "title": "P2", "references": []},
            {"arxiv_id": "p3", "title": "P3", "references": []},
            {"arxiv_id": "p4", "title": "P4", "references": []},
        ]
        analyzer.build_from_papers(papers)
        foundation = analyzer.find_foundation_papers()
        assert "p1" in foundation

    def test_get_citation_chain(self):
        """Test citation chain extraction."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "a", "title": "A", "references": ["b"]},
            {"arxiv_id": "b", "title": "B", "references": ["c"]},
            {"arxiv_id": "c", "title": "C", "references": ["d"]},
            {"arxiv_id": "d", "title": "D", "references": []},
        ]
        analyzer.build_from_papers(papers)
        chain = analyzer.get_citation_chain("a", depth=3)
        assert "a" in chain
        assert "b" in chain

    def test_gap_score(self):
        """Test gap score computation."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "p1", "title": "P1", "references": ["p2", "p3"]},
            {"arxiv_id": "p2", "title": "P2", "references": []},
            {"arxiv_id": "p3", "title": "P3", "references": []},
        ]
        analyzer.build_from_papers(papers)
        score = analyzer.gap_score("p1")
        assert 0.0 <= score <= 1.0

    def test_gap_score_isolated(self):
        """Test gap score for isolated paper."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "p1", "title": "P1", "references": []},
        ]
        analyzer.build_from_papers(papers)
        score = analyzer.gap_score("p1")
        assert score == 1.0

    def test_summary(self):
        """Test graph summary statistics."""
        analyzer = CitationGraphAnalyzer()
        papers = [
            {"arxiv_id": "a", "title": "A", "references": ["b", "c"]},
            {"arxiv_id": "b", "title": "B", "references": ["c"]},
            {"arxiv_id": "c", "title": "C", "references": []},
        ]
        analyzer.build_from_papers(papers)
        summary = analyzer.summary()
        assert summary["total_papers"] == 3
        assert summary["total_edges"] == 3
        assert "avg_in_degree" in summary
        assert "avg_out_degree" in summary
        assert "foundation_papers" in summary
        assert "gap_papers" in summary

    def test_summary_empty(self):
        """Test summary with empty graph."""
        analyzer = CitationGraphAnalyzer()
        summary = analyzer.summary()
        assert summary["total_papers"] == 0
        assert summary["total_edges"] == 0
