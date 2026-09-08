"""
Research Quality Evaluator

Evaluates the quality of generated hypotheses, experiment designs,
and paper drafts to ensure the research output meets quality standards.
"""

from __future__ import annotations

from typing import Any

from deepresearch.config import ResearchConfig
from deepresearch.state import (
    EvaluationResult,
    Hypothesis,
    PaperDraft,
    ResearchState,
)


class QualityEvaluator:
    """Evaluator for research quality metrics."""

    def __init__(self, config: ResearchConfig | None = None):
        self.config = config or ResearchConfig()

    def evaluate_hypothesis(self, hypothesis: Hypothesis) -> float:
        """Score a hypothesis for novelty and testability (0.0-1.0)."""
        score = 0.0

        # Novelty: check if the hypothesis statement is specific and non-obvious
        novelty = hypothesis.get("novelty_score", 0.5)
        score += novelty * 0.5

        # Falsifiability: a good hypothesis must be falsifiable
        if hypothesis.get("falsifiability", False):
            score += 0.2

        # Rationale quality: must have non-empty rationale
        rationale = hypothesis.get("rationale", "")
        if len(rationale) > 50:
            score += 0.1

        # Counterfactual basis: must reference counterfactual reasoning
        cfb = hypothesis.get("counterfactual_basis", "")
        if len(cfb) > 20:
            score += 0.1

        # Supporting papers: should reference at least one paper
        if len(hypothesis.get("supporting_papers", [])) > 0:
            score += 0.1

        return min(1.0, score)

    def evaluate_experiment(self, experiment: dict[str, Any]) -> float:
        """Score an experiment design for feasibility (0.0-1.0)."""
        score = 0.0

        # Experiment type
        etype = experiment.get("experiment_type", "")
        if etype in ("simulation", "computational", "analytical"):
            score += 0.3

        # Methodology quality
        method = experiment.get("methodology", "")
        if len(method) > 50:
            score += 0.3

        # Resources specified
        resources = experiment.get("required_resources", [])
        if len(resources) > 0:
            score += 0.2

        # Timeline specified
        timeline = experiment.get("estimated_timeline", "")
        if timeline:
            score += 0.1

        # Simulated outcome
        outcome = experiment.get("simulated_outcome", "")
        if outcome:
            score += 0.1

        return min(1.0, score)

    def evaluate_paper(self, draft: PaperDraft) -> float:
        """Score a paper draft for quality (0.0-1.0)."""
        score = 0.0

        # Title
        if len(draft.get("title", "")) > 10:
            score += 0.15

        # Abstract
        if len(draft.get("abstract", "")) > 50:
            score += 0.2

        # Sections
        sections = draft.get("sections", {})
        expected_sections = {"Introduction", "Literature Review", "Research Hypotheses",
                             "Experiment Design", "Results", "Discussion"}
        found = set(sections.keys()) & expected_sections
        score += (len(found) / len(expected_sections)) * 0.35

        # References / bibliography
        if draft.get("bibliography_tex"):
            score += 0.15

        # Hypotheses included
        if len(draft.get("hypotheses", [])) > 0:
            score += 0.1

        # Experiment included
        if draft.get("experiment"):
            score += 0.05

        return min(1.0, score)

    def evaluate(self, state: ResearchState) -> EvaluationResult:
        """Run full evaluation on a completed research state."""
        hypotheses = state.get("hypotheses", [])
        experiments = state.get("experiments", [])
        drafts = state.get("drafts", [])

        # Hypothesis novelty (average of all hypotheses)
        if hypotheses:
            hyp_scores = [self.evaluate_hypothesis(h) for h in hypotheses]
            hypothesis_novelty = sum(hyp_scores) / len(hyp_scores)
        else:
            hypothesis_novelty = 0.0

        # Experiment feasibility (average of all experiments)
        if experiments:
            exp_scores = [self.evaluate_experiment(e) for e in experiments]
            experiment_feasibility = sum(exp_scores) / len(exp_scores)
        else:
            experiment_feasibility = 0.0

        # Paper quality
        if drafts:
            paper_quality = self.evaluate_paper(drafts[-1])
        else:
            paper_quality = 0.0

        overall = (hypothesis_novelty + experiment_feasibility + paper_quality) / 3.0

        feedback = []
        recommendations = []

        if hypothesis_novelty < 0.5:
            feedback.append("Hypothesis novelty score is below threshold")
            recommendations.append("Generate more diverse hypotheses with stronger counterfactual reasoning")
        else:
            feedback.append("Hypotheses demonstrate adequate novelty")

        if experiment_feasibility < 0.5:
            feedback.append("Experiment design feasibility is low")
            recommendations.append("Specify more detailed methodology and resource requirements")
        else:
            feedback.append("Experiment designs are sufficiently detailed")

        if paper_quality < 0.7:
            feedback.append("Paper quality needs improvement")
            recommendations.append("Expand abstract and ensure all expected sections are present")
        else:
            feedback.append("Paper draft meets quality standards")

        return EvaluationResult(
            hypothesis_novelty=round(hypothesis_novelty, 3),
            experiment_feasibility=round(experiment_feasibility, 3),
            paper_quality=round(paper_quality, 3),
            overall_score=round(overall, 3),
            feedback=feedback,
            recommendations=recommendations,
        )
