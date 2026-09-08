"""
CLI entry point for the DeepResearch engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from deepresearch.agents.pipeline import ResearchPipeline
from deepresearch.config import ResearchConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deepresearch",
        description="Autonomous Scientific Research Agent",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Research query to investigate",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON config file with query and options",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output",
        help="Output directory for the generated paper",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        default=True,
        help="Run quality evaluation after the pipeline (default: True)",
    )

    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config_data = json.load(f)
        query = config_data.get("query", "")
    elif args.query:
        query = args.query
    else:
        parser.print_help()
        sys.exit(1)

    if not query:
        print("Error: no research query provided")
        sys.exit(1)

    print(f"DeepResearch Engine v1.0.0")
    print(f"Query: {query}")
    print("-" * 60)

    config = ResearchConfig()
    pipeline = ResearchPipeline(config)
    state = pipeline.run(query)

    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    # Write LaTeX paper
    latex = pipeline.get_paper_latex(state)
    latex_path = output_dir / "paper.tex"
    with open(latex_path, "w") as f:
        f.write(latex)
    print(f"LaTeX paper written to: {latex_path}")

    # Write state JSON
    state_path = output_dir / "research_state.json"
    import deepresearch.memory.research_memory as mem_mod
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, default=str)
    print(f"Research state written to: {state_path}")

    # Print summary
    print("-" * 60)
    print(f"Papers found:      {len(state.get('papers', []))}")
    print(f"Hypotheses generated: {len(state.get('hypotheses', []))}")
    print(f"Experiments designed:  {len(state.get('experiments', []))}")
    print(f"Drafts written:      {len(state.get('drafts', []))}")

    if state.get("evaluations"):
        ev = state["evaluations"][-1]
        print(f"Overall quality:   {ev.get('overall_score', 0.0):.3f}")

    print("-" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
