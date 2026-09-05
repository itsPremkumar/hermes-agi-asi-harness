"""
Git-Backed Lineage DAG + Stagnation Supervisor — NVIDIA AVO Pattern
====================================================================
Lineage as git commits (not just in-memory DAG).
Supervisor monitors trajectory, intervenes on plateau.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LineageNodeType(str, Enum):
    """Types of lineage nodes."""
    SEED = "seed"                    # Initial version
    CANDIDATE = "candidate"          # Proposed but not committed
    COMMITTED = "committed"          # Accepted into lineage
    REVERTED = "reverted"            # Explicitly reverted
    SUPERVISOR_INTERVENTION = "supervisor_intervention"  # Supervisor action


@dataclass
class LineageNode:
    """A single node in the lineage DAG (git commit + metadata)."""
    commit_hash: str
    node_type: LineageNodeType
    score: float
    score_breakdown: dict = field(default_factory=dict)  # correctness, performance, etc.
    parent_hashes: list[str] = field(default_factory=list)
    message: str = ""
    author: str = "avo-agent"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "commit_hash": self.commit_hash,
            "node_type": self.node_type.value,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "parent_hashes": self.parent_hashes,
            "message": self.message,
            "author": self.author,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineageNode":
        return cls(
            commit_hash=data["commit_hash"],
            node_type=LineageNodeType(data["node_type"]),
            score=data["score"],
            score_breakdown=data.get("score_breakdown", {}),
            parent_hashes=data.get("parent_hashes", []),
            message=data.get("message", ""),
            author=data.get("author", "avo-agent"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ScoreVector:
    """Multi-dimensional score for correctness-gated evaluation."""
    correctness: float  # 0.0 or 1.0 (gate)
    performance: float  # e.g., TFLOPS, latency, throughput
    efficiency: float   # e.g., memory usage, power
    stability: float    # e.g., variance across runs

    def geometric_mean(self) -> float:
        """Geometric mean of non-correctness dimensions."""
        import math
        dims = [self.performance, self.efficiency, self.stability]
        dims = [d for d in dims if d > 0]
        if not dims:
            return 0.0
        return math.exp(sum(math.log(d) for d in dims) / len(dims))

    def is_correct(self) -> bool:
        return self.correctness >= 1.0

    def to_dict(self) -> dict:
        return {
            "correctness": self.correctness,
            "performance": self.performance,
            "efficiency": self.efficiency,
            "stability": self.stability,
            "geometric_mean": self.geometric_mean(),
        }


class GitLineageDAG:
    """
    Lineage DAG backed by git history.

    Each committed version is a git commit with metadata in commit message footer.
    Structure:
    - Git commits = lineage nodes
    - Tags: avo/v{N}-{score:.4f} for committed versions
    - Branch: avo/lineage for the evolution branch
    """

    def __init__(
        self,
        repo_path: Path,
        target_name: str,
        scoring_fn: Callable,
        baseline_commit: Optional[str] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.target_name = target_name
        self.scoring_fn = scoring_fn
        self.baseline_commit = baseline_commit or self._get_current_commit()

        # In-memory cache
        self._nodes: dict[str, LineageNode] = {}
        self._dag_edges: dict[str, list[str]] = {}  # parent -> children
        self._best_score: float = -1.0
        self._best_commit: Optional[str] = None

        # Ensure git repo
        self._ensure_git_repo()
        self._load_lineage()

    def _ensure_git_repo(self) -> None:
        """Ensure we're in a git repo with avo branch."""
        if not (self.repo_path / ".git").exists():
            raise RuntimeError(f"Not a git repository: {self.repo_path}")

        # Create/checkout avo/lineage branch
        result = subprocess.run(
            ["git", "branch", "--list", "avo/lineage"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if "avo/lineage" not in result.stdout:
            # Create branch from baseline
            subprocess.run(
                ["git", "checkout", "-b", "avo/lineage", self.baseline_commit],
                cwd=self.repo_path,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "checkout", "avo/lineage"],
                cwd=self.repo_path,
                check=True,
            )

    def _get_current_commit(self) -> str:
        """Get current HEAD commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _load_lineage(self) -> None:
        """Load lineage from git history."""
        # Get all commits on avo/lineage branch
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", "--grep=^AVO-", "--format=%H %s"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commit_hash, message = parts
                self._parse_commit_metadata(commit_hash, message)

        logger.info(f"Loaded {len(self._nodes)} lineage nodes")

    def _parse_commit_metadata(self, commit_hash: str, message: str) -> None:
        """Parse AVO metadata from commit message footer."""
        # Format: "AVO: message\n\nAVO-META: {...}"
        if "AVO-META:" not in message:
            return

        try:
            meta_start = message.index("AVO-META:") + len("AVO-META:")
            meta_json = message[meta_start:].strip()
            meta = json.loads(meta_json)

            node = LineageNode(
                commit_hash=commit_hash[:12],
                node_type=LineageNodeType(meta.get("type", "committed")),
                score=meta.get("score", 0.0),
                score_breakdown=meta.get("score_breakdown", {}),
                parent_hashes=meta.get("parents", []),
                message=message.split("\n\n")[0].replace("AVO: ", ""),
                timestamp=meta.get("timestamp", datetime.utcnow().isoformat()),
                metadata=meta.get("metadata", {}),
            )
            self._nodes[commit_hash[:12]] = node

            # Update DAG edges
            for parent in node.parent_hashes:
                if parent not in self._dag_edges:
                    self._dag_edges[parent] = []
                self._dag_edges[parent].append(commit_hash[:12])

            # Track best
            if node.score > self._best_score:
                self._best_score = node.score
                self._best_commit = commit_hash[:12]

        except Exception as e:
            logger.warning(f"Failed to parse commit metadata: {e}")

    def commit_version(
        self,
        version_path: Path,
        score: ScoreVector,
        message: str,
        node_type: LineageNodeType = LineageNodeType.COMMITTED,
        parents: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> LineageNode:
        """
        Commit a version to the lineage.
        Creates a git commit with AVO metadata in footer.
        """
        if not score.is_correct():
            raise ValueError("Cannot commit incorrect version (correctness gate failed)")

        # Stage changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.repo_path,
            check=True,
        )

        # Build commit message with metadata
        meta = {
            "type": node_type.value,
            "score": score.geometric_mean(),
            "score_breakdown": score.to_dict(),
            "parents": parents or [self._get_current_commit()[:12]],
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        commit_msg = f"AVO: {message}\n\nAVO-META: {json.dumps(meta)}"

        # Commit
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self.repo_path,
            check=True,
        )

        # Get new commit hash
        new_commit = self._get_current_commit()[:12]

        # Tag if committed
        if node_type == LineageNodeType.COMMITTED:
            tag = f"avo/v{len(self._nodes)+1}-{score.geometric_mean():.4f}"
            subprocess.run(
                ["git", "tag", tag, new_commit],
                cwd=self.repo_path,
                check=True,
            )

        # Create node
        node = LineageNode(
            commit_hash=new_commit,
            node_type=node_type,
            score=score.geometric_mean(),
            score_breakdown=score.to_dict(),
            parent_hashes=parents or [self._get_current_commit()[:12]],
            message=message,
            metadata=metadata or {},
        )

        self._nodes[new_commit] = node
        for parent in node.parent_hashes:
            if parent not in self._dag_edges:
                self._dag_edges[parent] = []
            self._dag_edges[parent].append(new_commit)

        # Update best
        if node.score > self._best_score:
            self._best_score = node.score
            self._best_commit = new_commit

        logger.info(f"Committed version {new_commit} with score {node.score:.4f} ({node_type.value})")
        return node

    def get_best_version(self) -> Optional[LineageNode]:
        """Get the best committed version."""
        if self._best_commit:
            return self._nodes.get(self._best_commit)
        return None

    def get_lineage_path(self, commit_hash: str) -> list[LineageNode]:
        """Get lineage path from seed to given commit."""
        path = []
        current = commit_hash[:12]
        while current in self._nodes:
            path.append(self._nodes[current])
            parents = self._nodes[current].parent_hashes
            if not parents:
                break
            current = parents[0]  # Single lineage for now
        return list(reversed(path))

    def export_dag(self) -> dict:
        """Export DAG for visualization."""
        return {
            "nodes": {h: n.to_dict() for h, n in self._nodes.items()},
            "edges": self._dag_edges,
            "best_commit": self._best_commit,
            "best_score": self._best_score,
        }


class StagnationSupervisor:
    """
    Supervisor that monitors evolution trajectory for stagnation.

    Interventions:
    - Redirect to alternative strategy
    - Suggest knowledge base queries
    - Trigger architecture review
    - Escalate to human (if configured)
    """

    def __init__(
        self,
        lineage: GitLineageDAG,
        stagnation_threshold: int = 10,  # steps without improvement
        score_plateau_threshold: float = 0.001,  # minimum improvement
        check_interval: int = 5,  # check every N steps
    ):
        self.lineage = lineage
        self.stagnation_threshold = stagnation_threshold
        self.score_plateau_threshold = score_plateau_threshold
        self.check_interval = check_interval

        self._steps_since_improvement = 0
        self._last_best_score = -1.0
        self._interventions: list[dict] = []
        self._step_count = 0

    def check_stagnation(self, current_score: float) -> Optional[dict]:
        """
        Check for stagnation and return intervention if needed.

        Returns:
            Intervention dict or None if no stagnation detected
        """
        self._step_count += 1

        # Check for improvement
        if current_score > self._last_best_score + self.score_plateau_threshold:
            self._last_best_score = current_score
            self._steps_since_improvement = 0
            return None

        self._steps_since_improvement += 1

        # Check threshold
        if self._steps_since_improvement >= self.stagnation_threshold:
            return self._generate_intervention(current_score)

        # Periodic check
        if self._step_count % self.check_interval == 0:
            return self._generate_periodic_guidance(current_score)

        return None

    def _generate_intervention(self, current_score: float) -> dict:
        """Generate a stagnation intervention."""
        intervention = {
            "type": "stagnation_intervention",
            "timestamp": datetime.utcnow().isoformat(),
            "steps_stalled": self._steps_since_improvement,
            "current_score": current_score,
            "best_score": self._last_best_score,
            "recommendations": [
                "Explore alternative optimization strategy",
                "Query domain knowledge base for new directions",
                "Review lineage for unexplored branches",
                "Consider architecture-level changes",
            ],
            "severity": "high" if self._steps_since_improvement > self.stagnation_threshold * 2 else "medium",
        }

        self._interventions.append(intervention)
        self._steps_since_improvement = 0  # Reset after intervention
        logger.warning(f"Supervisor intervention: {intervention['recommendations'][0]}")
        return intervention

    def _generate_periodic_guidance(self, current_score: float) -> dict:
        """Generate periodic guidance."""
        guidance = {
            "type": "periodic_guidance",
            "timestamp": datetime.utcnow().isoformat(),
            "step": self._step_count,
            "current_score": current_score,
            "best_score": self._last_best_score,
            "suggestions": [
                f"Current best: {self._last_best_score:.4f}",
                f"Steps since improvement: {self._steps_since_improvement}",
            ],
        }
        return guidance

    def record_intervention_response(self, response: str) -> None:
        """Record human/agent response to intervention."""
        if self._interventions:
            self._interventions[-1]["response"] = response
            self._interventions[-1]["response_time"] = datetime.utcnow().isoformat()

    def get_supervisor_brief(self) -> dict:
        """Get supervisor status brief for agent."""
        return {
            "steps_since_improvement": self._steps_since_improvement,
            "stagnation_threshold": self.stagnation_threshold,
            "current_best_score": self._last_best_score,
            "total_interventions": len(self._interventions),
            "recent_interventions": self._interventions[-3:],
        }


# AVO Evolution Engine (integrates lineage + supervisor)
class AVOEvolutionEngine:
    """
    Full AVO Evolution Engine — integrates lineage, scoring, supervisor.

    Usage:
        engine = AVOEvolutionEngine(repo_path, scoring_fn)
        result = engine.evolve(generations=100)
    """

    def __init__(
        self,
        repo_path: Path,
        scoring_fn: Callable,
        target_name: str = "target",
        stagnation_threshold: int = 10,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.target_name = target_name
        self.scoring_fn = scoring_fn

        self.lineage = GitLineageDAG(repo_path, target_name, scoring_fn)
        self.supervisor = StagnationSupervisor(
            self.lineage,
            stagnation_threshold=stagnation_threshold,
        )

        self._generation = 0
        self._running = False

    def evolve(
        self,
        generations: int = 100,
        population_size: int = 1,
        seed_path: Optional[Path] = None,
    ) -> dict:
        """
        Run autonomous evolution for N generations.

        Each generation:
        1. Agent proposes variation (using lineage + knowledge base)
        2. Score variation
        3. If correct AND (matches or improves best): commit to lineage
        4. Supervisor checks for stagnation
        5. Repeat
        """
        self._running = True
        results = {
            "generations_completed": 0,
            "total_candidates_evaluated": 0,
            "committed_versions": 0,
            "interventions_issued": 0,
            "initial_fitness": -1.0,
            "final_fitness": -1.0,
            "lineage_dag": None,
        }

        # Get baseline
        if seed_path:
            baseline_score = self.scoring_fn(seed_path)
            results["initial_fitness"] = baseline_score.geometric_mean()
            self.lineage.commit_version(
                seed_path,
                baseline_score,
                f"Baseline seed for {self.target_name}",
                LineageNodeType.SEED,
            )
        else:
            # Score current state
            baseline_score = self.scoring_fn(self.repo_path)
            results["initial_fitness"] = baseline_score.geometric_mean()
            self.lineage.commit_version(
                self.repo_path,
                baseline_score,
                f"Initial state for {self.target_name}",
                LineageNodeType.SEED,
            )

        for gen in range(generations):
            if not self._running:
                break

            self._generation = gen + 1
            logger.info(f"=== Generation {self._generation}/{generations} ===")

            # Agent proposes variation (this is where your coding agent runs)
            # For this framework, we expose the variation prompt via get_variation_prompt()
            candidate_path = self._propose_variation()

            if not candidate_path:
                logger.warning("No candidate proposed, skipping generation")
                continue

            results["total_candidates_evaluated"] += 1

            # Score candidate
            candidate_score = self.scoring_fn(candidate_path)

            # Check correctness gate
            if not candidate_score.is_correct():
                logger.info("Candidate failed correctness gate, reverting")
                self._revert_to_best()
                continue

            # Check if matches or improves best
            best_node = self.lineage.get_best_version()
            if best_node and candidate_score.geometric_mean() <= best_node.score + 1e-6:
                logger.info("Candidate does not improve best, reverting")
                self._revert_to_best()
                continue

            # Commit new best
            self.lineage.commit_version(
                candidate_path,
                candidate_score,
                f"Gen {self._generation}: {candidate_score.geometric_mean():.4f}",
                LineageNodeType.COMMITTED,
            )
            results["committed_versions"] += 1

            # Supervisor check
            intervention = self.supervisor.check_stagnation(candidate_score.geometric_mean())
            if intervention:
                results["interventions_issued"] += 1
                # In a real system, you'd feed this back to the agent
                logger.info(f"Supervisor intervention: {intervention['recommendations'][0]}")

            # Update best
            self._last_best_score = candidate_score.geometric_mean()

        results["generations_completed"] = self._generation
        results["final_fitness"] = self._last_best_score
        results["lineage_dag"] = self.lineage.export_dag()
        results["fitness_gain_percent"] = (
            (results["final_fitness"] - results["initial_fitness"]) / results["initial_fitness"] * 100
            if results["initial_fitness"] > 0 else 0
        )

        return results

    def _propose_variation(self) -> Optional[Path]:
        """
        Hook for agent to propose variation.
        In practice, this would invoke your coding agent with the variation prompt.
        Returns path to candidate version or None.
        """
        # This is a placeholder - real implementation would:
        # 1. Get variation prompt via get_variation_prompt()
        # 2. Invoke coding agent (Claude Code, Codex, etc.)
        # 3. Return path to modified code
        return None

    def get_variation_prompt(self) -> dict:
        """
        Get the variation prompt for the coding agent.

        This is the core AVO interface: the agent sees lineage, knowledge base, scoring function.
        """
        best_node = self.lineage.get_best_version()
        lineage_path = self.lineage.get_lineage_path(best_node.commit_hash) if best_node else []

        return {
            "target": self.target_name,
            "generation": self._generation + 1,
            "current_best": {
                "commit": best_node.commit_hash if best_node else None,
                "score": best_node.score if best_node else None,
                "score_breakdown": best_node.score_breakdown if best_node else None,
            },
            "lineage": [n.to_dict() for n in lineage_path],
            "knowledge_base": self._get_knowledge_base(),
            "scoring_contract": self._get_scoring_contract(),
            "supervisor_brief": self.supervisor.get_supervisor_brief(),
        }

    def _get_knowledge_base(self) -> dict:
        """Get domain knowledge base (to be customized per target)."""
        return {
            "documentation": "See docs/ in repository",
            "architecture": "See ARCHITECTURE.md",
            "api_docs": "See API documentation",
        }

    def _get_scoring_contract(self) -> dict:
        """Get scoring function contract."""
        return {
            "correctness": "Must pass all tests (gate)",
            "performance": "Primary optimization metric",
            "efficiency": "Secondary metric",
            "stability": "Variance across runs",
        }

    def _revert_to_best(self) -> None:
        """Revert working directory to best committed version."""
        best = self.lineage.get_best_version()
        if best:
            subprocess.run(
                ["git", "checkout", best.commit_hash, "--", "."],
                cwd=self.repo_path,
                check=True,
            )
            logger.info(f"Reverted to best version: {best.commit_hash}")

    def stop(self) -> None:
        self._running = False


# Scoring function signature for users to implement
def example_scoring_fn(path: Path) -> ScoreVector:
    """
    Example scoring function signature.

    Implement your own:
    - Run tests (correctness gate)
    - Benchmark performance
    - Measure efficiency
    - Check stability
    """
    # This is a template - replace with actual implementation
    return ScoreVector(
        correctness=1.0,  # 0.0 = fail, 1.0 = pass
        performance=100.0,  # e.g., TFLOPS
        efficiency=0.8,
        stability=0.9,
    )


if __name__ == "__main__":
    # Demo
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        subprocess.run(["git", "init"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

        # Create a dummy file
        (repo / "kernel.py").write_text("# kernel\npass\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True)

        # Create engine
        def score_fn(p: Path) -> ScoreVector:
            return ScoreVector(correctness=1.0, performance=100.0, efficiency=0.8, stability=0.9)

        engine = AVOEvolutionEngine(repo, score_fn, "demo_kernel")
        print("Variation prompt:")
        print(json.dumps(engine.get_variation_prompt(), indent=2))