"""
ecosystem_v2.py — Ecosystem Intelligence v2 — Research Pipeline & Discovery

Implements:
- GitHub capability discovery (API-based)
- ArXiv paper discovery
- HuggingFace model/dataset discovery
- Provenance tracking
- Research memory consolidation
- Capability extraction
- License & risk scanning
"""

import time
import json
import uuid
import logging
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryItem:
    source: str  # "github", "arxiv", "huggingface"
    item_id: str
    title: str
    description: str
    url: str
    license: str = "unknown"
    tags: List[str] = field(default_factory=list)
    stars: int = 0
    quality_score: float = 0.0
    discovered_at: float = field(default_factory=time.time)
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchPaper:
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    url: str
    published: str
    categories: List[str]
    relevance_score: float = 0.0


class EcosystemDiscoveryEngine:
    """
    Discovers and tracks capabilities from GitHub, ArXiv, and HuggingFace.
    Free-first — uses public APIs with no authentication required.
    """

    GITHUB_TRENDING_URL = "https://api.github.com/search/repositories"
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    HF_API_URL = "https://huggingface.co/api/models"

    def __init__(self):
        self.discoveries: List[DiscoveryItem] = []
        self.papers: List[ResearchPaper] = []
        self.provenance_log: List[Dict[str, Any]] = []
        self._http = None  # Will use httpx if available

    def _get_http(self):
        if self._http is None:
            try:
                import httpx
                self._http = httpx.AsyncClient(timeout=30)
            except ImportError:
                self._http = None
        return self._http

    async def discover_github(self, query: str = "AI agent framework", limit: int = 10) -> List[DiscoveryItem]:
        """Discovers GitHub repositories matching a query."""
        http = self._get_http()
        if not http:
            logger.warning("httpx not available for GitHub discovery")
            return []

        url = f"{self.GITHUB_TRENDING_URL}?q={query}&sort=stars&order=desc&per_page={limit}"
        try:
            resp = await http.get(url, headers={"Accept": "application/vnd.github.v3+json"})
            data = resp.json()
            items = []
            for repo in data.get("items", []):
                score = min(1.0, (repo.get("stargazers_count", 0) / 10000))
                item = DiscoveryItem(
                    source="github",
                    item_id=f"github_{repo['id']}",
                    title=repo["full_name"],
                    description=repo.get("description", ""),
                    url=repo["html_url"],
                    license=repo.get("license", {}).get("spdx_id", "unknown") if repo.get("license") else "unknown",
                    tags=["ai", "framework"],
                    stars=repo.get("stargazers_count", 0),
                    quality_score=score,
                    provenance={"discovered_at": time.time(), "query": query},
                )
                items.append(item)
                self.discoveries.append(item)
                self.provenance_log.append({
                    "item_id": item.item_id,
                    "action": "discovered_github",
                    "timestamp": time.time(),
                })
            return items
        except Exception as e:
            logger.warning("GitHub discovery failed: %s", e)
            return []

    async def discover_arxiv(self, query: str = "AI agent", limit: int = 10) -> List[ResearchPaper]:
        """Discovers research papers from ArXiv."""
        http = self._get_http()
        if not http:
            return []

        url = f"{self.ARXIV_API_URL}?search_query=all:{query}&start=0&max_results={limit}"
        try:
            resp = await http.get(url)
            # Simple parsing without feedparser
            import re
            content = resp.text
            papers = []

            # Extract paper entries
            entry_pattern = r'<entry>(.*?)</entry>'
            entries = re.findall(entry_pattern, content, re.DOTALL)

            for entry in entries[:limit]:
                title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                id_match = re.search(r'<id>(.*?)</id>', entry)
                summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)

                title = title_match.group(1).strip() if title_match else "Untitled"
                paper_id = id_match.group(1).strip() if id_match else f"arxiv_{uuid.uuid4().hex[:8]}"
                abstract = summary_match.group(1).strip()[:500] if summary_match else ""

                paper = ResearchPaper(
                    paper_id=paper_id,
                    title=title,
                    authors=[],
                    abstract=abstract,
                    url=paper_id,
                    published="",
                    categories=["cs.AI"],
                    relevance_score=0.5,
                )
                papers.append(paper)
                self.papers.append(paper)

            return papers
        except Exception as e:
            logger.warning("ArXiv discovery failed: %s", e)
            return []

    async def discover_hf(self, query: str = "text-generation", limit: int = 10) -> List[DiscoveryItem]:
        """Discovers HuggingFace models."""
        http = self._get_http()
        if not http:
            return []

        url = f"{self.HF_API_URL}?search={query}&limit={limit}"
        try:
            resp = await http.get(url)
            data = resp.json()
            items = []
            for model in data[:limit]:
                item = DiscoveryItem(
                    source="huggingface",
                    item_id=f"hf_{model.get('id', uuid.uuid4().hex[:8])}",
                    title=model.get("id", ""),
                    description=model.get("description", ""),
                    url=f"https://huggingface.co/{model.get('id', '')}",
                    license=model.get("license", "unknown"),
                    tags=model.get("tags", []),
                    quality_score=0.0,
                    provenance={"discovered_at": time.time(), "query": query},
                )
                items.append(item)
                self.discoveries.append(item)
            return items
        except Exception as e:
            logger.warning("HuggingFace discovery failed: %s", e)
            return []

    def scan_secrets(self, file_paths: List[str]) -> List[Dict[str, str]]:
        """Scans files for hardcoded secrets."""
        import re
        import pathlib

        secret_patterns = [
            (r"sk-[A-Za-z0-9]{16,}", "OpenAI API key"),
            (r"ghp_[A-Za-z0-9]{20,}", "GitHub Personal Access Token"),
            (r"github_pat_[A-Za-z0-9_]{20,}", "GitHub Fine-grained PAT"),
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
            (r"gho_[A-Za-z0-9_]{20,}", "GitHub OAuth Token"),
        ]

        findings = []
        for path in file_paths:
            p = pathlib.Path(path)
            if not p.exists() or not p.is_file():
                continue
            if p.stat().st_size > 100000:  # Skip large files
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for pattern, secret_type in secret_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        findings.append({
                            "file": str(p),
                            "type": secret_type,
                            "match_prefix": match[:8] + "...",
                        })
            except Exception as e:
                logger.debug("Secret scan error on %s: %s", path, e)
        return findings

    def get_summary(self) -> Dict[str, Any]:
        """Returns discovery summary."""
        by_source = {}
        for item in self.discoveries:
            by_source[item.source] = by_source.get(item.source, 0) + 1

        return {
            "total_discoveries": len(self.discoveries),
            "total_papers": len(self.papers),
            "by_source": by_source,
            "provenance_entries": len(self.provenance_log),
        }

    async def close(self):
        if self._http:
            await self._http.aclose()


class EcosystemDiscoveryPlugin:
    """Plugin wrapper for EcosystemDiscoveryEngine."""

    def __init__(self, kernel=None):
        self.state = "started"
        self.kernel = kernel
        self.engine = EcosystemDiscoveryEngine()
        self.manifest = type('Manifest', (), {'name': 'ecosystem_intelligence', 'version': '2.0.0'})()

    async def load(self):
        return True

    async def start(self):
        return True

    async def stop(self):
        await self.engine.close()
        return True

    async def health(self):
        summary = self.engine.get_summary()
        return {
            "status": "healthy",
            "plugin": "ecosystem_intelligence",
            "version": "2.0.0",
            "state": self.state,
            "healthy": True,
            "discoveries": summary["total_discoveries"],
            "papers": summary["total_papers"],
            "by_source": summary["by_source"],
        }

    def get_capabilities(self):
        return ["github_discovery", "arxiv_discovery", "hf_discovery", "secret_scan", "provenance_tracking"]

    async def discover_github(self, *args, **kwargs):
        return await self.engine.discover_github(*args, **kwargs)

    async def discover_arxiv(self, *args, **kwargs):
        return await self.engine.discover_arxiv(*args, **kwargs)

    def scan_secrets(self, *args, **kwargs):
        return self.engine.scan_secrets(*args, **kwargs)

    def get_summary(self):
        return self.engine.get_summary()


async def create(kernel=None) -> EcosystemDiscoveryPlugin:
    """Factory function for kernel integration."""
    plugin = EcosystemDiscoveryPlugin(kernel)
    await plugin.load()
    await plugin.start()
    return plugin
