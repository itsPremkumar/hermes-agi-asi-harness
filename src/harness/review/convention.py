"""ConventionEnforcer — enforce harness coding conventions.

Validates code against project-specific coding conventions for the harness.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConventionViolation:
    """A convention violation."""

    file: str
    line: int
    severity: str
    message: str
    rule: str
    fix_hint: str = ""


class ConventionEnforcer:
    """Enforces harness coding conventions.

    Rules cover naming, imports, structure, docstrings, type hints,
    and other project-specific standards.
    """

    # Supported convention rules
    RULES = {
        "naming",
        "imports",
        "docstrings",
        "type-hints",
        "structure",
        "logging",
        "error-handling",
        "module-header",
    }

    def __init__(self, default_rules: set[str] | None = None) -> None:
        self.default_rules = default_rules or self.RULES.copy()

    def check_files(
        self,
        files: dict[str, str],
        rules: list[str] | None = None,
    ) -> list[ConventionViolation]:
        """Check files against conventions.

        Args:
            files: Mapping of filename to source code.
            rules: Optional subset of rules to enforce.

        Returns:
            List of ConventionViolation entries.
        """
        violations: list[ConventionViolation] = []

        active_rules: set[str]
        if rules is not None:
            active_rules = set(rules) & self.RULES
            unknown = set(rules) - self.RULES
            if unknown:
                logger.warning("Unknown convention rules: %s", unknown)
        else:
            active_rules = self.default_rules.copy()

        for filename, source in files.items():
            if not filename.endswith(".py"):
                continue
            file_violations = self._check_file(filename, source, active_rules)
            violations.extend(file_violations)

        return violations

    def _check_file(
        self, filename: str, source: str, rules: set[str]
    ) -> list[ConventionViolation]:
        """Check a single file against active rules."""
        violations: list[ConventionViolation] = []
        lines = source.splitlines()

        # Rule: module-header
        if "module-header" in rules:
            violations.extend(self._check_module_header(filename, source, lines))

        # Rule: imports
        if "imports" in rules:
            violations.extend(self._check_imports(filename, source, lines))

        # Rule: logging
        if "logging" in rules:
            violations.extend(self._check_logging(filename, lines))

        # Rule: error-handling
        if "error-handling" in rules:
            violations.extend(self._check_error_handling(filename, lines))

        # AST-based rules
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return violations  # Can't parse, skip AST rules

        if "naming" in rules:
            violations.extend(self._check_naming(filename, tree))
        if "docstrings" in rules:
            violations.extend(self._check_docstrings(filename, tree))
        if "type-hints" in rules:
            violations.extend(self._check_type_hints(filename, tree))
        if "structure" in rules:
            violations.extend(self._check_structure(filename, tree))

        return violations

    def _check_module_header(
        self, filename: str, source: str, lines: list[str]
    ) -> list[ConventionViolation]:
        """Check that file has a module docstring."""
        violations: list[ConventionViolation] = []

        # Skip empty files
        if not lines or all(not line.strip() for line in lines):
            return violations

        # Check for module docstring
        has_docstring = False
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                has_docstring = True
                break
            elif stripped.startswith("#") or stripped == "":
                continue
            else:
                break

        if not has_docstring:
            violations.append(
                ConventionViolation(
                    file=filename,
                    line=1,
                    severity="medium",
                    message="File missing module docstring",
                    rule="module-header",
                    fix_hint='Add a docstring at the top of the file',
                )
            )

        return violations

    def _check_imports(
        self, filename: str, source: str, lines: list[str]
    ) -> list[ConventionViolation]:
        """Check import ordering and usage."""
        violations: list[ConventionViolation] = []

        import_lines: list[tuple[int, str]] = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_lines.append((i, stripped))

        # Check for unused imports (simple heuristic: name not found elsewhere)
        for line_no, imp_line in import_lines:
            if imp_line.startswith("import "):
                module = imp_line.split()[1].split(".")[0]
            elif imp_line.startswith("from "):
                parts = imp_line.split()
                if len(parts) >= 4:
                    module = parts[1].split(".")[0]
                else:
                    continue
            else:
                continue

            # Check if module is used elsewhere
            rest_of_file = "\n".join(
                l for j, l in enumerate(lines, 1) if j != line_no
            )
            # Simple usage check (not perfect but catches obvious cases)
            if module not in rest_of_file and module.replace("_", "") not in rest_of_file.lower():
                # Only flag if it's clearly unused (not __future__ etc.)
                if module not in ("__future__", "typing"):
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=line_no,
                            severity="low",
                            message=f"Potentially unused import: {module}",
                            rule="imports",
                            fix_hint=f"Remove unused import or use it",
                        )
                    )

        # Check ordering: stdlib first, then third-party, then local
        prev_category = 0
        for line_no, imp_line in import_lines:
            category = self._import_category(imp_line)
            if category < prev_category:
                violations.append(
                    ConventionViolation(
                        file=filename,
                        line=line_no,
                        severity="low",
                        message="Import not in correct order (stdlib → third-party → local)",
                        rule="imports",
                        fix_hint="Reorder imports: standard library, then third-party, then local",
                    )
                )
            prev_category = category

        return violations

    def _import_category(self, import_line: str) -> int:
        """Classify import category: 0=stdlib, 1=third-party, 2=local."""
        stdlib_modules = {
            "os", "sys", "json", "re", "math", "time", "datetime", "pathlib",
            "typing", "collections", "itertools", "functools", "hashlib",
            "logging", "unittest", "abc", "io", "warnings", "copy", "ast",
            "dataclasses", "enum", "types", "inspect", "importlib", "string",
            "textwrap", "traceback", "contextlib", "concurrent", "asyncio",
        }

        module = ""
        if import_line.startswith("import "):
            module = import_line.split()[1].split(".")[0]
        elif import_line.startswith("from "):
            module = import_line.split()[1].split(".")[0]

        if module in stdlib_modules:
            return 0
        if module in ("harness", "hermes", "agent", "mcp", "plugins"):
            return 2
        if module:
            return 1
        return 0

    def _check_naming(self, filename: str, tree: ast.Module) -> list[ConventionViolation]:
        """Check naming conventions (snake_case for functions/vars, PascalCase for classes)."""
        violations: list[ConventionViolation] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Functions should be snake_case
                if not re.match(r"^[a-z_][a-z0-9_]*$", node.name) and not node.name.startswith("__"):
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message=f"Function '{node.name}' should use snake_case naming",
                            rule="naming",
                            fix_hint=f"Rename to '{self._to_snake_case(node.name)}'",
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                # Classes should be PascalCase
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message=f"Class '{node.name}' should use PascalCase naming",
                            rule="naming",
                            fix_hint=f"Rename to '{self._to_pascal_case(node.name)}'",
                        )
                    )

            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                # Variables should be snake_case (simple check for module-level)
                if re.match(r"^[A-Z][a-z]", node.name) and not node.name.isupper():
                    # Likely a constant or local var
                    pass  # Skip to reduce false positives

        return violations

    def _check_docstrings(
        self, filename: str, tree: ast.Module
    ) -> list[ConventionViolation]:
        """Check that public functions and classes have docstrings."""
        violations: list[ConventionViolation] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private functions (single underscore is OK to have no docstring)
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue
                # Skip simple property-like functions with only ...
                if (len(node.body) == 1 and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        node.body[0].value.value is ...):
                    continue

                has_docstring = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if not has_docstring:
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=node.lineno,
                            severity="low",
                            message=f"Public function '{node.name}' missing docstring",
                            rule="docstrings",
                            fix_hint="Add a docstring describing the function",
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                has_docstring = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if not has_docstring:
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=node.lineno,
                            severity="low",
                            message=f"Class '{node.name}' missing docstring",
                            rule="docstrings",
                            fix_hint="Add a class docstring",
                        )
                    )

        return violations

    def _check_type_hints(
        self, filename: str, tree: ast.Module
    ) -> list[ConventionViolation]:
        """Check that public functions have type hints."""
        violations: list[ConventionViolation] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue

                # Check return annotation
                if node.returns is None:
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=node.lineno,
                            severity="low",
                            message=f"Function '{node.name}' missing return type hint",
                            rule="type-hints",
                            fix_hint="Add return type annotation",
                        )
                    )

                # Check parameter annotations
                for arg in node.args.args:
                    if arg.arg == "self":
                        continue
                    if arg.annotation is None:
                        violations.append(
                            ConventionViolation(
                                file=filename,
                                line=node.lineno,
                                severity="low",
                                message=f"Parameter '{arg.arg}' in '{node.name}' missing type hint",
                                rule="type-hints",
                                fix_hint=f"Add type annotation for '{arg.arg}'",
                            )
                        )

        return violations

    def _check_structure(
        self, filename: str, tree: ast.Module
    ) -> list[ConventionViolation]:
        """Check structural conventions (file length, class size)."""
        violations: list[ConventionViolation] = []

        # Check file line count
        lines = ast.unparse(tree).splitlines()
        if len(lines) > 500:
            violations.append(
                ConventionViolation(
                    file=filename,
                    line=1,
                    severity="medium",
                    message=f"File too large ({len(lines)} lines) — consider splitting",
                    rule="structure",
                    fix_hint="Break into smaller modules",
                )
            )

        # Check class method count
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(
                    1 for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                if method_count > 20:
                    violations.append(
                        ConventionViolation(
                            file=filename,
                            line=node.lineno,
                            severity="medium",
                            message=f"Class '{node.name}' has too many methods ({method_count})",
                            rule="structure",
                            fix_hint="Consider extracting a helper class or mixin",
                        )
                    )

        return violations

    def _check_logging(
        self, filename: str, lines: list[str]
    ) -> list[ConventionViolation]:
        """Check logging conventions (no print statements in production code)."""
        violations: list[ConventionViolation] = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"\bprint\s*\(", stripped):
                violations.append(
                    ConventionViolation(
                        file=filename,
                        line=i,
                        severity="low",
                        message="Use logging instead of print() for output",
                        rule="logging",
                        fix_hint="Replace print() with logger.info/debug/warning",
                    )
                )

        return violations

    def _check_error_handling(
        self, filename: str, lines: list[str]
    ) -> list[ConventionViolation]:
        """Check error handling conventions."""
        violations: list[ConventionViolation] = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Check for bare except
            if re.search(r"^\s*except\s*:", stripped):
                violations.append(
                    ConventionViolation(
                        file=filename,
                        line=i,
                        severity="medium",
                        message="Bare except clause — catch specific exceptions",
                        rule="error-handling",
                        fix_hint="Replace 'except:' with 'except Exception:' or specific exception types",
                    )
                )

            # Check for pass in except blocks
            if i > 1 and re.search(r"^\s*except\b", stripped):
                # Check if next non-empty line is pass
                for j in range(i, min(i + 3, len(lines))):
                    next_line = lines[j].strip()
                    if next_line == "pass":
                        violations.append(
                            ConventionViolation(
                                file=filename,
                                line=i + 1,
                                severity="medium",
                                message="Empty except block with pass — at minimum log the exception",
                                rule="error-handling",
                                fix_hint="Add logging or proper error handling",
                            )
                        )
                        break
                    elif next_line and not next_line.startswith("#"):
                        break

        return violations

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert camelCase to snake_case."""
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert snake_case to PascalCase."""
        return "".join(word.capitalize() for word in name.split("_"))
