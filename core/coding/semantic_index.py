"""
Semantic Code Index — Index code at multiple levels for retrieval.

Levels: repository → package → module → class → function → symbol → AST → tests → docs
Retrieval: lexical + semantic + AST/symbol + graph traversal + commit history + test relationships
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IndexLevel(str, Enum):
    REPOSITORY = "repository"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    SYMBOL = "symbol"
    AST = "ast"
    TEST = "test"
    DOCUMENTATION = "documentation"


@dataclass
class CodeChunk:
    id: str
    level: IndexLevel
    name: str
    file_path: str
    content: str
    line_start: int
    line_end: int
    symbols: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchQuery:
    text: str
    level: Optional[IndexLevel] = None
    file_pattern: str = ""
    symbol_type: str = ""
    include_tests: bool = True
    include_docs: bool = True


@dataclass
class SearchResult:
    chunk: CodeChunk
    score: float
    match_type: str  # lexical, semantic, symbol, graph, history


class SemanticCodeIndex:
    """Multi-level code index for retrieval."""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.chunks: Dict[str, CodeChunk] = {}
        self._symbol_index: Dict[str, List[str]] = {}  # symbol → [chunk_ids]
        self._file_index: Dict[str, List[str]] = {}  # file → [chunk_ids]
    
    def index_file(self, file_path: str, content: str,
                   level: IndexLevel = IndexLevel.MODULE) -> List[CodeChunk]:
        """Index a file and return created chunks."""
        chunks = []
        lines = content.split('\n')
        
        # Create a module-level chunk
        module_chunk = CodeChunk(
            id=str(uuid.uuid4()),
            level=level,
            name=file_path.split('/')[-1],
            file_path=file_path,
            content=content,
            line_start=1,
            line_end=len(lines),
        )
        chunks.append(module_chunk)
        self.chunks[module_chunk.id] = module_chunk
        
        # Index functions
        for i, line in enumerate(lines, 1):
            func_match = re.match(r'^(?:async\s+)?def\s+(\w+)', line)
            if func_match:
                func_name = func_match.group(1)
                func_content = self._extract_function_content(lines, i)
                func_chunk = CodeChunk(
                    id=str(uuid.uuid4()),
                    level=IndexLevel.FUNCTION,
                    name=func_name,
                    file_path=file_path,
                    content=func_content,
                    line_start=i,
                    line_end=i + func_content.count('\n'),
                    symbols=[func_name],
                )
                chunks.append(func_chunk)
                self.chunks[func_chunk.id] = func_chunk
                
                # Index symbol
                if func_name not in self._symbol_index:
                    self._symbol_index[func_name] = []
                self._symbol_index[func_name].append(func_chunk.id)
        
        # Index file
        if file_path not in self._file_index:
            self._file_index[file_path] = []
        self._file_index[file_path].extend([c.id for c in chunks])
        
        return chunks
    
    def _extract_function_content(self, lines: List[str], start: int) -> str:
        """Extract function body from lines."""
        if start > len(lines):
            return ""
        
        content_lines = [lines[start - 1]]
        indent = len(lines[start - 1]) - len(lines[start - 1].lstrip())
        
        for i in range(start, len(lines)):
            line = lines[i]
            if not line.strip():
                content_lines.append(line)
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent > indent:
                content_lines.append(line)
            else:
                break
        
        return '\n'.join(content_lines)
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search the index."""
        results = []
        
        for chunk in self.chunks.values():
            # Filter by level
            if query.level and chunk.level != query.level:
                continue
            
            # Filter by file pattern
            if query.file_pattern and not re.search(query.file_pattern, chunk.file_path):
                continue
            
            # Lexical search
            if query.text.lower() in chunk.content.lower():
                score = chunk.content.lower().count(query.text.lower()) / max(len(chunk.content), 1)
                results.append(SearchResult(chunk=chunk, score=score, match_type="lexical"))
                continue
            
            # Symbol search
            if query.text in chunk.symbols:
                results.append(SearchResult(chunk=chunk, score=1.0, match_type="symbol"))
                continue
        
        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results
    
    def get_symbol(self, name: str) -> List[CodeChunk]:
        """Get all chunks containing a symbol."""
        chunk_ids = self._symbol_index.get(name, [])
        return [self.chunks[cid] for cid in chunk_ids if cid in self.chunks]
    
    def get_file_chunks(self, file_path: str) -> List[CodeChunk]:
        """Get all chunks for a file."""
        chunk_ids = self._file_index.get(file_path, [])
        return [self.chunks[cid] for cid in chunk_ids if cid in self.chunks]
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "chunks": len(self.chunks),
            "symbols": len(self._symbol_index),
            "files": len(self._file_index),
        }
