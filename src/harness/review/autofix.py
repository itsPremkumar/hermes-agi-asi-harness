"""AutoFixer — automatically fix common review issues.

Provides automatic fixes for simple, well-defined code quality and convention issues.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of auto-fixing."""

    fixed_files: dict[str, str] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    fixes_applied: list[dict[str, Any]] = field(default_factory=list)
    files_with_errors: list[str] = field(default_factory=list)


class AutoFixer:
    """Automatically fixes common code review issues.

    Fixes trailing whitespace, import ordering, basic formatting, and
    other safe, deterministic improvements.
    """

    def fix_files(
        self,
        files: dict[str, str],
        issues: list[dict[str, Any]] | None = None,
    ) -> FixResult:
        """Attempt to fix issues in files.

        Args:
            files: Mapping of filename to source code.
            issues: Optional list of issues to fix. If None, re-analyzes.

        Returns:
            FixResult with fixed file contents.
        """
        result = FixResult()

        for filename, source in files.items():
            if not filename.endswith(".py"):
                continue

            fixed_source = source
            file_fixes: list[dict[str, Any]] = []

            # Fix trailing whitespace
            new_source, count = self._fix_trailing_whitespace(fixed_source)
            if count > 0:
                file_fixes.append({"rule": "trailing-whitespace", "count": count})
                fixed_source = new_source

            # Fix missing newline at end of file
            if fixed_source and not fixed_source.endswith("\n"):
                fixed_source += "\n"
                file_fixes.append({"rule": "missing-final-newline", "count": 1})

            # Fix multiple consecutive blank lines (>2)
            new_source, count = self._fix_multiple_blank_lines(fixed_source)
            if count > 0:
                file_fixes.append({"rule": "multiple-blank-lines", "count": count})
                fixed_source = new_source

            # Fix bare except
            new_source, count = self._fix_bare_except(fixed_source)
            if count > 0:
                file_fixes.append({"rule": "bare-except", "count": count})
                fixed_source = new_source

            # Fix assert for validation (replace with if/raise)
            new_source, count = self._fix_assert_validation(fixed_source)
            if count > 0:
                file_fixes.append({"rule": "assert-validation", "count": count})
                fixed_source = new_source

            if file_fixes:
                result.fixed_files[filename] = fixed_source
                result.fixes_applied.extend(
                    [{"file": filename, **fix} for fix in file_fixes]
                )

        # Generate summary suggestions
        if result.fixes_applied:
            total_fixes = sum(f.get("count", 0) for f in result.fixes_applied)
            result.suggestions.append(
                f"Applied {total_fixes} auto-fix(es) across {len(result.fixed_files)} file(s)"
            )
        else:
            result.suggestions.append("No auto-fixes were applicable")

        return result

    def _fix_trailing_whitespace(self, source: str) -> tuple[str, int]:
        """Remove trailing whitespace from all lines."""
        lines = source.splitlines()
        fixed_lines = [line.rstrip() for line in lines]
        count = sum(1 for orig, fixed in zip(lines, fixed_lines) if orig != fixed)
        return "\n".join(fixed_lines), count

    def _fix_multiple_blank_lines(self, source: str) -> tuple[str, int]:
        """Reduce 3+ consecutive blank lines to 2."""
        original = source
        # Replace 3+ consecutive newlines with 2
        fixed = re.sub(r"\n{4,}", "\n\n\n", source)
        count = (len(original) - len(fixed)) // 2  # Approximate count
        return fixed, max(count, 0)

    def _fix_bare_except(self, source: str) -> tuple[str, int]:
        """Replace 'except:' with 'except Exception:'."""
        lines = source.splitlines()
        fixed_lines = []
        count = 0

        for line in lines:
            if re.search(r"^\s*except\s*:", line):
                # Replace bare except with except Exception
                indent = len(line) - len(line.lstrip())
                fixed_line = " " * indent + "except Exception:"
                fixed_lines.append(fixed_line)
                count += 1
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines), count

    def _fix_assert_validation(self, source: str) -> tuple[str, int]:
        """Replace 'assert condition' with 'if not condition: raise AssertionError(...)'."""
        lines = source.splitlines()
        fixed_lines = []
        count = 0

        for line in lines:
            match = re.match(r"^(\s*)assert\s+(.+?)(?:\s*,\s*(.+))?$", line)
            if match:
                indent = match.group(1)
                condition = match.group(2)
                message = match.group(3) or f"Assertion failed: {condition}"
                fixed_line = f"{indent}if not {condition}:\n{indent}    raise AssertionError({message})"
                fixed_lines.append(fixed_line)
                count += 1
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines), count
