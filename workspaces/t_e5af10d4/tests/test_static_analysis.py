"""Tests for TestPilot static analysis engine."""
import textwrap
from pathlib import Path

from testpilot.static_analysis import StaticAnalyzer, analyze_directory


def test_static_analyzer_detects_complex_function(tmp_path: Path) -> None:
    """Static analyzer should detect complex functions as test gaps."""
    source = textwrap.dedent('''
        def simple_add(a, b):
            return a + b

        def complex_process(data):
            result = []
            for item in data:
                if item > 0:
                    try:
                        result.append(item * 2)
                    except Exception:
                        pass
                elif item == -1:
                    break
            return result
    ''')

    (tmp_path / "module.py").write_text(source, encoding="utf-8")

    analyzer = StaticAnalyzer(str(tmp_path))
    gaps = analyzer.analyze()

    assert len(gaps) >= 1
    gap_names = [g.function_name for g in gaps]
    assert "complex_process" in gap_names
    # simple_add should NOT appear (too simple)
    assert "simple_add" not in gap_names


def test_static_analyzer_respects_exclude_patterns(tmp_path: Path) -> None:
    """Analyzer should skip excluded directories."""
    source = textwrap.dedent('''
        def func_with_logic(x):
            if x > 0:
                return x * 2
            return -1
    ''')

    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "main.py").write_text(source, encoding="utf-8")
    (tmp_path / "tests" / "test_main.py").write_text(source, encoding="utf-8")

    analyzer = StaticAnalyzer(str(tmp_path), exclude_patterns=["*/tests/*"])
    gaps = analyzer.analyze()

    assert all("tests" not in g.file_path for g in gaps)


def test_analyze_directory_convenience(tmp_path: Path) -> None:
    """analyze_directory should work as a convenience function."""
    source = textwrap.dedent('''
        def process(items):
            for item in items:
                if item:
                    yield item
    ''')
    (tmp_path / "app.py").write_text(source, encoding="utf-8")

    gaps = analyze_directory(str(tmp_path))
    assert isinstance(gaps, list)
