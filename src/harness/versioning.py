"""Versioning — semantic versioning and compatibility checks."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Version:
    """Semantic version."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse a version string like '1.2.3' or '1.2.3-beta'."""
        parts = version_str.split("-", 1)
        nums = parts[0].split(".")
        if len(nums) != 3:
            raise ValueError(f"Invalid version: {version_str}")
        prerelease = parts[1] if len(parts) > 1 else ""
        return cls(int(nums[0]), int(nums[1]), int(nums[2]), prerelease)

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += f"-{self.prerelease}"
        return s

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch, self.prerelease) == (other.major, other.minor, other.patch, other.prerelease)

    def __lt__(self, other: "Version") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # No prerelease > prerelease (1.0.0 > 1.0.0-alpha)
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and not other.prerelease:
            return True
        return self.prerelease < other.prerelease

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        return not self < other

    def is_compatible_with(self, other: "Version") -> bool:
        """Check if this version is compatible with another (same major)."""
        return self.major == other.major


@dataclass
class VersionRange:
    """A range of versions."""
    min_version: Optional[Version] = None
    max_version: Optional[Version] = None
    min_inclusive: bool = True
    max_inclusive: bool = True

    def contains(self, version: Version) -> bool:
        """Check if a version is within this range."""
        if self.min_version is not None:
            if self.min_inclusive and version < self.min_version:
                return False
            if not self.min_inclusive and version <= self.min_version:
                return False
        if self.max_version is not None:
            if self.max_inclusive and version > self.max_version:
                return False
            if not self.max_inclusive and version >= self.max_version:
                return False
        return True

    def __str__(self) -> str:
        parts = []
        if self.min_version:
            parts.append(f"{'>=' if self.min_inclusive else '>'}{self.min_version}")
        if self.max_version:
            parts.append(f"{'<=' if self.max_inclusive else '<'}{self.max_version}")
        return " && ".join(parts) if parts else "*"


class Compatibility:
    """Check compatibility between plugins."""

    @staticmethod
    def check_version_compatibility(actual: str, required: str) -> bool:
        """Check if an actual version satisfies a required version."""
        try:
            actual_v = Version.parse(actual)
            required_v = Version.parse(required)
            return actual_v.is_compatible_with(required_v)
        except ValueError:
            return False

    @staticmethod
    def is_api_compatible(provider: str, consumer: str) -> bool:
        """Check if a provider's API is compatible with a consumer."""
        try:
            provider_v = Version.parse(provider)
            consumer_v = Version.parse(consumer)
            # Same major version = API compatible
            return provider_v.major == consumer_v.major
        except ValueError:
            return False

    @staticmethod
    def check_range(version_str: str, range_str: str) -> bool:
        """Check if a version string is within a version range."""
        version = Version.parse(version_str)
        range_obj = Compatibility._parse_range(range_str)
        return range_obj.contains(version)

    @staticmethod
    def _parse_range(range_str: str) -> VersionRange:
        """Parse a version range string like '>=1.0.0 <2.0.0'."""
        range_obj = VersionRange()
        parts = range_str.split()
        for part in parts:
            if part.startswith(">="):
                range_obj.min_version = Version.parse(part[2:])
                range_obj.min_inclusive = True
            elif part.startswith(">"):
                range_obj.min_version = Version.parse(part[1:])
                range_obj.min_inclusive = False
            elif part.startswith("<="):
                range_obj.max_version = Version.parse(part[2:])
                range_obj.max_inclusive = True
            elif part.startswith("<"):
                range_obj.max_version = Version.parse(part[1:])
                range_obj.max_inclusive = False
            elif part == "*":
                continue
        return range_obj


__all__ = ["Version", "VersionRange", "Compatibility"]
