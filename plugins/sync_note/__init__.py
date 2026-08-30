"""SyncNote — collaborative note-taking and sync."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NoteStatus(str, Enum):
    DRAFT = "draft"
    SYNCED = "synced"
    CONFLICT = "conflict"


@dataclass
class Note:
    id: str
    title: str
    content: str
    status: NoteStatus = NoteStatus.DRAFT
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


class SyncNote:
    """Manage notes."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._notes: dict[str, Note] = {}

    def create(self, title: str, content: str) -> Note:
        note = Note(id=str(uuid.uuid4()), title=title, content=content)
        self._notes[note.id] = note
        return note

    def sync(self, note_id: str) -> bool:
        if note_id in self._notes:
            self._notes[note_id].status = NoteStatus.SYNCED
            return True
        return False

    def get(self, note_id: str) -> Note | None:
        return self._notes.get(note_id)

    def list_all(self) -> list[Note]:
        return list(self._notes.values())

    def count(self) -> int:
        return len(self._notes)
