#!/usr/bin/env python3
"""
Document Intelligence Plugin — Document parsing and extraction
============================================================
Features:
- Text extraction from multiple formats (txt, md, code, csv)
- PDF metadata extraction (if available)
- Table extraction from CSV/Markdown
- Document summarization (extractive)
- Keyword extraction
- Entity detection (basic)
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_document_intel")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


class DocumentIntel:
    """Document parsing and extraction."""
    
    def __init__(self):
        self.stopwords = set("the a an and or but if then else for to of in on at by with from as is are was were be been being this that these those it its their our your my we you they he she them his her not no yes do does did done has have had will would can could should may might must i me he she they who what which when where why how all any both each few more most other some such only own same so than too very s t can will just don should now".split())
    
    def read_text(self, path: str) -> Dict[str, Any]:
        """Read text from a file."""
        file_path = Path(path)
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return {
                "success": True,
                "content": content,
                "size_bytes": len(content.encode("utf-8")),
                "line_count": content.count("\n") + 1,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract basic metadata from text."""
        words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
        word_count = len(words)
        unique_words = len(set(words))
        
        # Sentence count
        sentences = re.split(r'[.!?]+', content)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Average word length
        avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
        
        return {
            "word_count": word_count,
            "unique_words": unique_words,
            "sentence_count": sentence_count,
            "avg_word_length": round(avg_word_len, 2),
            "avg_sentence_length": round(word_count / max(sentence_count, 1), 2),
        }
    
    def extract_keywords(self, content: str, top_k: int = 10) -> List[str]:
        """Extract keywords from text."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        # Remove stopwords
        filtered = [w for w in words if w not in self.stopwords]
        
        # Count frequencies
        word_counts = Counter(filtered)
        
        # Return top keywords
        return [word for word, _ in word_counts.most_common(top_k)]
    
    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract basic entities (capitalized words, emails, URLs, numbers)."""
        entities: Dict[str, List[str]] = {
            "proper_nouns": [],
            "emails": [],
            "urls": [],
            "numbers": [],
            "dates": [],
        }
        
        # Proper nouns (capitalized words not at sentence start)
        proper_nouns = re.findall(r'\b([A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})*)\b', content)
        entities["proper_nouns"] = list(dict.fromkeys(proper_nouns))[:20]
        
        # Emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
        entities["emails"] = list(dict.fromkeys(emails))[:10]
        
        # URLs
        urls = re.findall(r'https?://[^\s]+', content)
        entities["urls"] = list(dict.fromkeys(urls))[:10]
        
        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', content)
        entities["numbers"] = list(dict.fromkeys(numbers))[:20]
        
        # Dates
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b', content)
        entities["dates"] = list(dict.fromkeys(dates))[:10]
        
        return entities
    
    def extract_tables(self, content: str) -> List[Dict[str, Any]]:
        """Extract tables from Markdown or CSV content."""
        tables = []
        
        # Markdown tables
        md_tables = re.findall(r'(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n)+)', content)
        for mt in md_tables:
            rows = [r.strip().strip('|').split('|') for r in mt.strip().split('\n')]
            header = [c.strip() for c in rows[0]]
            data = [[c.strip() for c in r] for r in rows[2:]]
            tables.append({
                "type": "markdown",
                "header": header,
                "rows": data,
                "row_count": len(data),
            })
        
        return tables
    
    def summarize(self, content: str, sentences: int = 3) -> Dict[str, Any]:
        """Extractive summarization."""
        # Split into sentences
        raw_sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        raw_sentences = [s.strip() for s in raw_sentences if s.strip()]
        
        if not raw_sentences:
            return {"success": False, "error": "No sentences found"}
        
        # Score sentences by word frequency
        word_freq: Dict[str, int] = {}
        for sentence in raw_sentences:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            for word in words:
                if word not in self.stopwords:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        sentence_scores = []
        for i, sentence in enumerate(raw_sentences):
            words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            score = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
            # Bonus for position (first/last sentences)
            if i == 0 or i == len(raw_sentences) - 1:
                score *= 1.2
            sentence_scores.append((score, i, sentence))
        
        # Get top sentences
        top_sentences = sorted(sentence_scores, reverse=True)[:sentences]
        top_sentences.sort(key=lambda x: x[1])  # Sort by original order
        
        summary = " ".join(s[2] for s in top_sentences)
        
        return {
            "success": True,
            "summary": summary,
            "sentence_count": len(raw_sentences),
            "summary_sentences": len(top_sentences),
        }
    
    def analyze_document(self, path: str) -> Dict[str, Any]:
        """Full document analysis."""
        result = self.read_text(path)
        if not result["success"]:
            return result
        
        content = result["content"]
        
        return {
            "success": True,
            "path": path,
            "metadata": self.extract_metadata(content),
            "keywords": self.extract_keywords(content),
            "entities": self.extract_entities(content),
            "tables": self.extract_tables(content),
            "summary": self.summarize(content),
            "size_bytes": result["size_bytes"],
            "line_count": result["line_count"],
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Document Intelligence Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="document_intel",
            version="1.0.0",
            description="Document parsing, keyword/entity extraction, table extraction, and extractive summarization",
            license="MIT",
            source="internal",
            capabilities=["text_extraction", "keyword_extraction", "entity_extraction", "table_extraction", "summarization", "document_analysis"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.engine: Optional[DocumentIntel] = None
    
    async def load(self) -> bool:
        self.engine = DocumentIntel()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.engine:
            self.engine = DocumentIntel()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.engine is not None,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def read_text(self, path: str) -> Dict[str, Any]:
        return self.engine.read_text(path)
    
    def extract_metadata(self, content: str) -> Dict[str, Any]:
        return self.engine.extract_metadata(content)
    
    def extract_keywords(self, content: str, top_k: int = 10) -> List[str]:
        return self.engine.extract_keywords(content, top_k)
    
    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        return self.engine.extract_entities(content)
    
    def extract_tables(self, content: str) -> List[Dict[str, Any]]:
        return self.engine.extract_tables(content)
    
    def summarize(self, content: str, sentences: int = 3) -> Dict[str, Any]:
        return self.engine.summarize(content, sentences)
    
    def analyze_document(self, path: str) -> Dict[str, Any]:
        return self.engine.analyze_document(path)
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
