"""
Historical Engineering Memory — Store commit/PR/review/issue history as queryable memory.
"""

from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HistoryType(str, Enum):
    COMMIT = "commit"
    PR = "pull_request"
    REVIEW = "review"
    ISSUE = "issue"
    BUG = "bug"
    REVERT = "revert"
    INCIDENT = "incident"
    RELEASE = "release"


@dataclass
class HistoryEntry:
    id: str
    type: HistoryType
    title: str
    description: str
    author: str
    timestamp: float
    files_changed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BugPattern:
    id: str
    description: str
    affected_files: List[str]
    root_cause: str
    fix: str
    recurrence_risk: float
    first_seen: float
    last_seen: float


class HistoricalMemory:
    """Store and query repository history."""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.entries: List[HistoryEntry] = []
        self.bug_patterns: List[BugPattern] = []
    
    def ingest_git_history(self, repo_path: str) -> List[HistoryEntry]:
        """Ingest git history."""
        entries = []
        
        try:
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%an|%ae|%ad|%s', '--date=iso'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('|', 4)
                    if len(parts) >= 5:
                        entry = HistoryEntry(
                            id=parts[0],
                            type=HistoryType.COMMIT,
                            title=parts[4],
                            description="",
                            author=parts[1],
                            timestamp=datetime.fromisoformat(parts[3]).timestamp(),
                        )
                        entries.append(entry)
        
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        self.entries.extend(entries)
        return entries
    
    def query(self, query: str) -> List[HistoryEntry]:
        """Query history entries."""
        query_lower = query.lower()
        results = []
        
        for entry in self.entries:
            if query_lower in entry.title.lower() or query_lower in entry.description.lower():
                results.append(entry)
        
        return results
    
    def get_recent_changes(self, days: int = 30) -> List[HistoryEntry]:
        """Get recent changes."""
        cutoff = time.time() - (days * 86400)
        return [e for e in self.entries if e.timestamp >= cutoff]
    
    def get_bugs_in_area(self, filepath: str) -> List[BugPattern]:
        """Get bugs related to a file area."""
        return [b for b in self.bug_patterns if filepath in b.affected_files]
    
    def add_bug_pattern(self, pattern: BugPattern):
        """Add a bug pattern."""
        self.bug_patterns.append(pattern)
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "entries": len(self.entries),
            "bug_patterns": len(self.bug_patterns),
            "commits": sum(1 for e in self.entries if e.type == HistoryType.COMMIT),
            "issues": sum(1 for e in self.entries if e.type == HistoryType.ISSUE),
        }
