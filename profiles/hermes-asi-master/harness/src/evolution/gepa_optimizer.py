#!/usr/bin/env python3
"""
gepa_optimizer.py — Genetic Pareto Prompt & Strategy Optimizer
Evolves cognitive prompts and workflow templates along the multi-objective Pareto frontier.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class PromptMutation:
    variant_id: str
    prompt_text: str
    generation: int
    accuracy_score: float = 0.0
    latency_ms: float = 0.0
    token_cost: int = 0
    is_pareto_optimal: bool = False

class GEPAOptimizer:
    MUTATION_STRATEGIES = [
        "add_chain_of_thought_step",
        "add_negative_constraint",
        "add_self_critique_phase",
        "compress_redundancy"
    ]

    def __init__(self, base_prompt: str):
        self.base_prompt = base_prompt
        self.population: List[PromptMutation] = [
            PromptMutation(variant_id="gen_0_base", prompt_text=base_prompt, generation=0)
        ]

    def mutate(self, candidate: PromptMutation, strategy: str) -> PromptMutation:
        new_text = candidate.prompt_text
        if strategy == "add_chain_of_thought_step":
            new_text += "\n[Rule] Think step-by-step and explicitly list your intermediate reasoning."
        elif strategy == "add_negative_constraint":
            new_text += "\n[Rule] Never return an unverified assertion without earned proof evidence."
        elif strategy == "add_self_critique_phase":
            new_text += "\n[Rule] Before producing final output, critique your draft against edge cases."
        elif strategy == "compress_redundancy":
            new_text = new_text.replace("  ", " ").strip()

        variant_id = f"gen_{candidate.generation + 1}_{strategy[:10]}"
        return PromptMutation(variant_id=variant_id, prompt_text=new_text, generation=candidate.generation + 1)

    def evolve_population(self, iterations: int = 2) -> List[PromptMutation]:
        for i in range(iterations):
            current_best = self.population[-1]
            for strat in self.MUTATION_STRATEGIES:
                mut = self.mutate(current_best, strat)
                # Assign simulated fitness
                mut.accuracy_score = min(1.0, 0.85 + (mut.generation * 0.03))
                self.population.append(mut)
        return self.population

    def get_best_prompt(self) -> PromptMutation:
        return max(self.population, key=lambda p: p.accuracy_score)
