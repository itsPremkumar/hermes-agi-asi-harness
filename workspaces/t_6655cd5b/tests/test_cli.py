"""Tests for the CLI entry point."""

import pytest
from unittest.mock import patch, MagicMock
from deepresearch.cli import main
import sys
import io


class TestCLI:
    def test_main_with_query(self, capsys, tmp_path, monkeypatch):
        """CLI should run the pipeline and produce output files."""
        monkeypatch.chdir(tmp_path)
        test_args = ["deepresearch", "test query"]
        monkeypatch.setattr(sys, "argv", test_args)

        with patch("deepresearch.cli.ResearchPipeline") as MockPipeline:
            mock_instance = MagicMock()
            mock_pipeline_cls = MockPipeline.return_value
            mock_pipeline_cls.run.return_value = {
                "query": "test query",
                "run_id": "test-run",
                "stage": "done",
                "papers": [{}],
                "summaries": [{}],
                "hypotheses": [{}],
                "experiments": [{}],
                "drafts": [{
                    "id": "d1",
                    "title": "Test",
                    "abstract": "Abstract",
                    "sections": {},
                    "references": [],
                    "hypotheses": [],
                    "experiment": None,
                    "bibliography_tex": "",
                }],
                "evaluations": [{"overall_score": 0.8}],
            }
            mock_pipeline_cls.get_paper_latex.return_value = "\\documentclass{article}\\begin{document}test\\end{document}"
            main()

        captured = capsys.readouterr()
        assert "DeepResearch Engine" in captured.out
        assert "test query" in captured.out
        assert "Done" in captured.out

    def test_main_no_query_no_config(self, capsys, monkeypatch):
        """CLI should print help and exit when no args given."""
        monkeypatch.setattr(sys, "argv", ["deepresearch"])
        with pytest.raises(SystemExit):
            main()

    def test_main_with_config(self, capsys, tmp_path, monkeypatch):
        """CLI should accept a config file."""
        import json
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"query": "config query"}))
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(sys, "argv", ["deepresearch", "--config", str(config_path)])

        with patch("deepresearch.cli.ResearchPipeline") as MockPipeline:
            mock_pipeline_cls = MockPipeline.return_value
            mock_pipeline_cls.run.return_value = {
                "query": "config query",
                "run_id": "test",
                "stage": "done",
                "papers": [],
                "summaries": [],
                "hypotheses": [],
                "experiments": [],
                "drafts": [],
                "evaluations": [],
            }
            mock_pipeline_cls.get_paper_latex.return_value = "test"
            main()

        captured = capsys.readouterr()
        assert "config query" in captured.out
