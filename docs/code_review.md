# CodeReview System — Documentation

The CodeReview System is an autonomous code review agent for the harness. It
analyzes code changes against quality standards, security best practices, and
harness conventions.

## Architecture

The system is composed of 6 modules:

| Module | File | Purpose |
|--------|------|---------|
| ReviewEngine | `engine.py` | Main orchestrator — runs all sub-systems |
| QualityChecker | `quality.py` | Code quality analysis (complexity, duplication, style) |
| SecurityScanner | `security.py` | Security vulnerability detection |
| ConventionEnforcer | `convention.py` | Enforce harness coding conventions |
| ReviewReporter | `reporter.py` | Generate structured review reports |
| AutoFixer | `autofix.py` | Automatically fix common review issues |

## Quick Start

```python
from harness.review import ReviewEngine

engine = ReviewEngine()

# Review files
files = {
    "src/my_module.py": "def foo():\n    pass\n",
}
result = engine.review_files(files)

print(f"Score: {result.score:.1f}")
print(f"Passed: {result.passed}")
print(f"Issues: {len(result.issues)}")

# Generate a report
report = engine.generate_report(result, format="markdown")
print(report)
```

## Features

### Quality Checks

- Line length (max 120 chars)
- Trailing whitespace
- Function length (max 50 lines)
- Cyclomatic complexity (max 10)
- Parameter count (max 7)
- Missing docstrings
- Duplicate code blocks across files
- TODO/FIXME comments
- Bare except clauses
- Dangerous functions (eval, exec)

### Security Scans

- Hardcoded credentials (passwords, API keys, private keys)
- Unsafe deserialization (pickle, marshal, yaml.load)
- OS command injection (subsystem, os.system, os.popen)
- SQL injection (string concatenation/formatting)
- Path traversal
- Code injection (eval, exec, compile)
- `__import__` usage
- `globals()`/`locals()` usage
- Assert statements for validation

### Convention Enforcement

- Module docstrings
- Function/class docstrings
- Naming conventions (snake_case, PascalCase)
- Import ordering (stdlib → third-party → local)
- Type hints on public functions
- Print vs logging
- Error handling (no bare except, no empty except blocks)
- File structure (max 500 lines, max 20 methods per class)

### Auto-Fix

- Remove trailing whitespace
- Add missing final newline
- Reduce multiple blank lines (4+ → 2)
- Replace bare except with `except Exception:`
- Convert assert to `if not condition: raise AssertionError(...)`

## API Reference

### ReviewEngine

```python
class ReviewEngine:
    def __init__(
        self,
        quality_checker: QualityChecker | None = None,
        security_scanner: SecurityScanner | None = None,
        convention_enforcer: ConventionEnforcer | None = None,
        autofixer: AutoFixer | None = None,
        reporter: ReviewReporter | None = None,
        pass_threshold: float = 70.0,
    ) -> None

    def review_files(
        self,
        files: dict[str, str],
        auto_fix: bool = False,
        conventions: list[str] | None = None,
    ) -> ReviewResult

    def review_diff(self, diff_text: str, auto_fix: bool = False) -> ReviewResult

    def generate_report(self, result: ReviewResult, format: str = "markdown") -> str
```

### ReviewResult

```python
@dataclass
class ReviewResult:
    passed: bool
    score: float  # 0.0 to 100.0
    issues: list[dict[str, Any]]
    suggestions: list[str]
    quality_report: QualityReport | None
    security_report: SecurityReport | None
    convention_violations: list[ConventionViolation]
    fixed_code: dict[str, str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]
```

## Output Formats

### Markdown

```markdown
# Code Review Report

**Status:** PASSED
**Score:** 85.0/100
**Issues:** 3
**Suggestions:** 2

## Issues
| File | Line | Severity | Category | Rule | Message |
|------|------|----------|----------|------|---------|
| ... |
```

### JSON

```json
{
  "passed": true,
  "score": 85.0,
  "issue_count": 3,
  "suggestion_count": 2,
  "issues": [...],
  "suggestions": [...],
  "quality_score": 88.0,
  "security_score": 92.0,
  "convention_violations": 1
}
```

### Plain Text

```
============================================================
CODE REVIEW REPORT
============================================================
Status:     PASSED
Score:      85.0/100
Issues:     3
Suggestions: 2
...
```

## Integration

### With CI/CD

```python
import sys
from harness.review import ReviewEngine

engine = ReviewEngine(pass_threshold=75.0)
files = {"main.py": open("main.py").read()}
result = engine.review_files(files)

if not result.passed:
    print(engine.generate_report(result, format="text"))
    sys.exit(1)
```

### With Git Diffs

```python
from harness.review import ReviewEngine

engine = ReviewEngine()
diff_output = get_git_diff()  # your git diff function
result = engine.review_diff(diff_output)
report = engine.generate_report(result, format="markdown")
post_to_pr(report)
```

## Testing

```bash
pytest tests/test_review_engine.py tests/test_quality_checker.py \
       tests/test_security_scanner.py tests/test_convention_enforcer.py \
       tests/test_review_reporter.py tests/test_autofix.py
```

All tests should pass (65+ total tests).

## Severity Levels

| Level | Weight | Description |
|-------|--------|-------------|
| INFO | 1 | Informational, style suggestion |
| LOW | 3 | Minor issue, should fix |
| MEDIUM | 5 | Significant issue, fix recommended |
| HIGH | 10 | Major issue, should fix before merge |
| CRITICAL | 25 | Security/correctness risk, must fix |

## Scoring

The overall score starts at 100 and deducts weighted points for each issue:

```
score = 100 - sum(severity_weight * count)
```

The score is then blended with quality and security sub-scores (weighted 15% each).

Pass threshold: 70.0 (configurable via `pass_threshold` parameter).
