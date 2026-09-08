"""Tests for ArXiv API client."""

import pytest
from deepresearch.tools.arxiv_api import ArxivAPI


class TestArxivAPI:
    def test_init(self):
        api = ArxivAPI(email="test@test.com", max_results=10)
        assert api.email == "test@test.com"
        assert api.max_results == 10

    def test_search_returns_list(self):
        api = ArxivAPI()
        results = api.search("quantum computing", max_results=5)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_search_result_fields(self):
        api = ArxivAPI()
        results = api.search("machine learning", max_results=3)
        for r in results:
            assert "arxiv_id" in r
            assert "title" in r
            assert "authors" in r
            assert "abstract" in r
            assert "year" in r
            assert "links" in r

    def test_search_caching(self):
        api = ArxivAPI()
        r1 = api.search("caching test", max_results=3)
        r2 = api.search("caching test", max_results=3)
        assert r1 == r2

    def test_fetch_paper_mock(self):
        api = ArxivAPI()
        paper = api.fetch_paper("2106.12345")
        assert paper["arxiv_id"] == "2106.12345"

    def test_mock_results_structure(self):
        api = ArxivAPI()
        results = api._mock_results("test query", 2)
        assert len(results) == 2
        assert all("title" in r for r in results)
        assert all("arxiv_id" in r for r in results)
