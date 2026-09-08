"""Tests for PubMed API client."""

import pytest
from unittest.mock import patch, MagicMock
from deepresearch.tools.pubmed_api import PubMedAPI


class TestPubMedAPI:
    def test_init(self):
        api = PubMedAPI(email="test@test.com", max_results=10)
        assert api.email == "test@test.com"
        assert api.max_results == 10

    def test_search_returns_list(self):
        api = PubMedAPI()
        with patch("deepresearch.providers.llm.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            with patch.object(api, "_parse_xml", return_value=[
                {"pubmed_id": "12345678", "title": "Test Article", "authors": ["Jane Doe"], "abstract": "Test abstract", "year": 2025, "links": []},
            ]):
                results = api.search("cancer research", max_results=5)
                assert isinstance(results, list)
                assert len(results) == 1

    def test_search_result_fields(self):
        api = PubMedAPI()
        with patch("deepresearch.providers.llm.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            with patch.object(api, "_parse_xml", return_value=[
                {"pubmed_id": "12345678", "title": "Test Article", "authors": ["Jane Doe"], "abstract": "Test abstract", "year": 2025, "links": []},
            ]):
                results = api.search("genetics", max_results=3)
                for r in results:
                    assert "pubmed_id" in r
                    assert "title" in r
                    assert "authors" in r
                    assert "abstract" in r
                    assert "year" in r
                    assert "links" in r

    def test_search_caching(self):
        api = PubMedAPI()
        with patch("deepresearch.providers.llm.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            with patch.object(api, "_parse_xml", return_value=[
                {"pubmed_id": "12345678", "title": "Test Article", "authors": ["Jane Doe"], "abstract": "Test abstract", "year": 2025, "links": []},
            ]):
                r1 = api.search("cache test", max_results=3)
                r2 = api.search("cache test", max_results=3)
                assert r1 == r2

    def test_fetch_article_mock(self):
        api = PubMedAPI()
        article = api.fetch_article("12345678")
        assert article["pubmed_id"] == "12345678"

    def test_mock_results_structure(self):
        api = PubMedAPI()
        results = api._mock_results("test query", 2)
        assert len(results) == 2
        assert all("pubmed_id" in r for r in results)
