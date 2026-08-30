#!/usr/bin/env python3
"""
HERMES DEEP RESEARCH ENGINE — WEB RESEARCH AGENT
================================================
Web search, crawling, and content extraction.

Extracted from:
- GPT Researcher: Web search + page crawling + source extraction
- DeerFlow: Web search + fetching + sub-agent research
- Perplexica: SearXNG integration + multi-source search
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
import urllib.parse
import urllib.request
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_web_research")


@dataclass
class SearchResult:
    """A search result."""
    result_id: str
    url: str
    title: str
    snippet: str
    source: str
    relevance_score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawledPage:
    """A crawled web page."""
    page_id: str
    url: str
    title: str
    content: str
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExtractedEvidence:
    """Extracted evidence from a page."""
    evidence_id: str
    page_id: str
    url: str
    claim: str
    evidence: str
    confidence: float = 0.5
    source_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class WebResearchAgent:
    """
    Web Research Agent — searches, crawls, and extracts information.
    
    Features:
    - Multi-source web search (DuckDuckGo, SearXNG, etc.)
    - Web page crawling and content extraction
    - Source extraction and evidence collection
    - Recursive link following
    - Content deduplication
    """
    
    def __init__(self, max_pages: int = 50, max_depth: int = 3):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self._search_cache: dict[str, list[SearchResult]] = {}
        self._crawled_pages: dict[str, CrawledPage] = {}
        self._evidence: list[ExtractedEvidence] = []
    
    async def search(self, query: str, num_results: int = 10, source: str = "duckduckgo") -> list[SearchResult]:
        """Search the web."""
        cache_key = f"{source}:{query}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        results = []
        
        if source == "duckduckgo":
            results = await self._search_duckduckgo(query, num_results)
        elif source == "searxng":
            results = await self._search_searxng(query, num_results)
        else:
            results = await self._search_fallback(query, num_results)
        
        self._search_cache[cache_key] = results
        logger.info("Search '%s': %d results from %s", query[:50], len(results), source)
        return results
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> list[SearchResult]:
        """Search using DuckDuckGo."""
        results = []
        
        try:
            # Use DuckDuckGo's lite HTML interface (more reliable)
            encoded_query = urllib.parse.quote(query)
            url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
            
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode("utf-8", errors="ignore")
                
                # Parse results from lite interface
                result_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>'
                snippet_pattern = r'<td class="result-snippet"[^>]*>(.*?)</td>'
                
                titles_urls = re.findall(result_pattern, html)
                snippets = re.findall(snippet_pattern, html, re.DOTALL)
                
                for i, (url, title) in enumerate(titles_urls[:num_results]):
                    # Clean up URL
                    if url.startswith("//"):
                        url = "https:" + url
                    elif url.startswith("/"):
                        url = "https://duckduckgo.com" + url
                    
                    # Clean up title
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    
                    snippet = ""
                    if i < len(snippets):
                        snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                    
                    if title and url:
                        results.append(SearchResult(
                            result_id=str(uuid.uuid4()),
                            url=url,
                            title=title[:200],
                            snippet=snippet[:500],
                            source="duckduckgo"
                        ))
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
        
        return results
    
    async def _search_searxng(self, query: str, num_results: int) -> list[SearchResult]:
        """Search using SearXNG."""
        results = []
        
        try:
            # Try local SearXNG instance
            encoded_query = urllib.parse.quote(query)
            url = f"http://localhost:8080/search?q={encoded_query}&format=json"
            
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                for result in data.get("results", [])[:num_results]:
                    results.append(SearchResult(
                        result_id=str(uuid.uuid4()),
                        url=result.get("url", ""),
                        title=result.get("title", ""),
                        snippet=result.get("content", ""),
                        source="searxng"
                    ))
        except Exception as e:
            logger.warning("SearXNG search failed: %s", e)
        
        return results
    
    async def _search_fallback(self, query: str, num_results: int) -> list[SearchResult]:
        """Fallback search using multiple sources."""
        results = []
        
        # Try DuckDuckGo first
        results = await self._search_duckduckgo(query, num_results)
        
        if not results:
            # Try SearXNG
            results = await self._search_searxng(query, num_results)
        
        return results
    
    async def crawl(self, url: str, depth: int = 0) -> CrawledPage | None:
        """Crawl a web page."""
        if url in self._crawled_pages:
            return self._crawled_pages[url]
        
        if depth >= self.max_depth:
            return None
        
        if len(self._crawled_pages) >= self.max_pages:
            return None
        
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode("utf-8", errors="ignore")
                
                # Extract title
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
                title = title_match.group(1) if title_match else url
                
                # Extract text content
                text = self._extract_text(content)
                
                # Extract links
                links = self._extract_links(content, url)
                
                page = CrawledPage(
                    page_id=str(uuid.uuid4()),
                    url=url,
                    title=title,
                    content=text,
                    links=links[:20]  # Limit links
                )
                
                self._crawled_pages[url] = page
                logger.info("Crawled: %s (%d chars)", url[:50], len(text))
                return page
                
        except Exception as e:
            logger.warning("Crawl failed for %s: %s", url[:50], e)
            return None
    
    def _extract_text(self, html: str) -> str:
        """Extract text from HTML."""
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract links from HTML."""
        links = []
        
        href_pattern = r'href=["\']([^"\']+)["\']'
        for match in re.finditer(href_pattern, html, re.IGNORECASE):
            href = match.group(1)
            
            # Skip anchors, javascript, mailto
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Make absolute URL
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                parsed = urllib.parse.urlparse(base_url)
                links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
        
        return links
    
    async def extract_evidence(self, page: CrawledPage, question: str) -> list[ExtractedEvidence]:
        """Extract evidence from a crawled page."""
        evidence = []
        
        # Split content into paragraphs
        paragraphs = page.content.split('\n')
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) < 50:  # Skip short paragraphs
                continue
            
            # Check relevance to question
            relevance = self._calculate_relevance(paragraph, question)
            
            if relevance > 0.3:
                evidence.append(ExtractedEvidence(
                    evidence_id=str(uuid.uuid4()),
                    page_id=page.page_id,
                    url=page.url,
                    claim=f"Evidence from {page.title}",
                    evidence=paragraph[:500],
                    confidence=relevance,
                    source_text=paragraph
                ))
        
        self._evidence.extend(evidence)
        return evidence
    
    def _calculate_relevance(self, text: str, question: str) -> float:
        """Calculate relevance of text to a question."""
        # Simple keyword overlap
        question_words = set(question.lower().split())
        text_words = set(text.lower().split())
        
        if not question_words:
            return 0.0
        
        overlap = len(question_words & text_words)
        return min(1.0, overlap / len(question_words))
    
    async def research_topic(self, topic: str, max_results: int = 10) -> dict[str, Any]:
        """Research a topic comprehensively."""
        # Search
        search_results = await self.search(topic, max_results)
        
        # Crawl top results
        pages = []
        for result in search_results[:5]:
            page = await self.crawl(result.url)
            if page:
                pages.append(page)
        
        # Extract evidence
        all_evidence = []
        for page in pages:
            evidence = await self.extract_evidence(page, topic)
            all_evidence.extend(evidence)
        
        return {
            "topic": topic,
            "search_results": len(search_results),
            "pages_crawled": len(pages),
            "evidence_found": len(all_evidence),
            "evidence": all_evidence
        }
    
    async def health(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "crawled_pages": len(self._crawled_pages),
            "evidence_count": len(self._evidence),
            "search_cache_size": len(self._search_cache)
        }
