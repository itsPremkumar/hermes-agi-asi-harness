"""Release Management — versioning, changelog, and release automation."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReleaseStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VersionBump(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class Release:
    """A release."""
    id: str
    version: str
    status: ReleaseStatus
    notes: str = ""
    changes: list[str] = field(default_factory=list)
    created_at: float = 0.0
    published_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangelogEntry:
    """A changelog entry."""
    id: str
    version: str
    description: str
    change_type: str  # added, fixed, changed, removed, security
    timestamp: float = 0.0


class ReleaseManager:
    """Manage releases and versioning."""

    def __init__(self, current_version: str = "0.1.0"):
        self.id = str(uuid.uuid4())
        self.current_version = current_version
        self._releases: dict[str, Release] = {}
        self._changelog: list[ChangelogEntry] = []

    def bump_version(self, bump: VersionBump = VersionBump.PATCH) -> str:
        """Bump the version number."""
        parts = self.current_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if bump == VersionBump.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif bump == VersionBump.MINOR:
            minor += 1
            patch = 0
        else:
            patch += 1

        self.current_version = f"{major}.{minor}.{patch}"
        return self.current_version

    def create_release(self, version: str | None = None, notes: str = "") -> Release:
        """Create a new release."""
        release = Release(
            id=str(uuid.uuid4()),
            version=version or self.current_version,
            status=ReleaseStatus.DRAFT,
            notes=notes,
        )
        self._releases[release.id] = release
        return release

    def add_change(self, version: str, description: str, change_type: str = "changed") -> ChangelogEntry:
        """Add a changelog entry."""
        entry = ChangelogEntry(
            id=str(uuid.uuid4()),
            version=version,
            description=description,
            change_type=change_type,
        )
        self._changelog.append(entry)

        # Also add to release if exists
        for release in self._releases.values():
            if release.version == version:
                release.changes.append(description)
                break

        return entry

    def publish_release(self, release_id: str) -> bool:
        """Publish a release."""
        if release_id in self._releases:
            self._releases[release_id].status = ReleaseStatus.PUBLISHED
            return True
        return False

    def get_release(self, release_id: str) -> Release | None:
        """Get a release by ID."""
        return self._releases.get(release_id)

    def list_releases(self) -> list[Release]:
        """List all releases."""
        return list(self._releases.values())

    def get_changelog(self, version: str | None = None) -> list[ChangelogEntry]:
        """Get changelog entries."""
        if version:
            return [e for e in self._changelog if e.version == version]
        return list(self._changelog)

    def get_latest_release(self) -> Release | None:
        """Get the latest published release."""
        published = [r for r in self._releases.values() if r.status == ReleaseStatus.PUBLISHED]
        if not published:
            return None
        return max(published, key=lambda r: r.version)

    def get_state(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "total_releases": len(self._releases),
            "published": sum(1 for r in self._releases.values() if r.status == ReleaseStatus.PUBLISHED),
            "changelog_entries": len(self._changelog),
        }
