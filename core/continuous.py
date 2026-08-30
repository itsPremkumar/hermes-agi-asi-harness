"""Hermes AGI/ASI Harness — continuous evolution engine.

Runs AVO + benchmark in a loop for autonomous, long-horizon
improvement. Mirrors the AVO paper's days-long autonomous search.

Usage:
    python -m hermes.continuous --goal "optimize kernel" --max-iterations 100
    python -m hermes.continuous --onetime                       # run one pass
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("hermes.continuous")


@dataclass
class EvolutionRound:
    round: int = 0
    started_at: str = ""
    finished_at: str = ""
    iterations: int = 0
    best_version: str | None = None
    mean_score: float = 0.0
    accepted: int = 0
    stagnation_events: int = 0
    memory_entries: int = 0
    lineage_versions: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


class ContinuousEngine:
    """Continuous evolution loop.

    Wraps AVOEngine + BenchmarkRunner into an indefinitely-running
    process that:
    1. Runs an AVO search pass
    2. Benchmarks the result
    3. Persists state to disk
    4. Sleeps, then repeats
    """

    def __init__(
        self,
        goal: str,
        max_iterations: int = 50,
        max_no_improve: int = 10,
        sleep_seconds: float = 60.0,
        store_dir: str = ".evo_continuous",
        max_rounds: int | None = None,
    ) -> None:
        self.goal = goal
        self.max_iterations = max_iterations
        self.max_no_improve = max_no_improve
        self.sleep_seconds = sleep_seconds
        self.store_dir = Path(store_dir)
        self.max_rounds = max_rounds
        self._rounds: List[EvolutionRound] = []
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._store_dir / "state.json"
        self._load()

    def run_once(self) -> EvolutionRound:
        from core.avo.engine import AVOEngine, AVOConfig
        from core.benchmark.harness import BenchmarkRunner, ScoringFunction

        round_num = len(self._rounds) + 1
        started = datetime.now(timezone.utc).isoformat()
        logger.info("Continuous evolution round %d started: %s", round_num, self.goal)

        config = AVOConfig(
            max_iterations=self.max_iterations,
            max_no_improve=self.max_no_improve,
            store_dir=str(self._store_dir / "avo"),
        )
        engine = AVOEngine(config)
        avo_result = engine.run({"goal": self.goal})

        # Benchmark the result honestly
        runner = BenchmarkRunner(ScoringFunction())
        tasks = [
            {"name": "ava_correctness", "fn": lambda: avo_result["iterations"] > 0},
            {"name": "ava_committed", "fn": lambda: avo_result["lineage_stats"]["accepted_or_better"] > 0},
        ]
        runner.run(tasks, n_runs=1)
        bench_summary = runner.summary()

        round_rec = EvolutionRound(
            round=round_num,
            started_at=started,
            finished_at=datetime.now(timezone.utc).isoformat(),
            iterations=avo_result["iterations"],
            best_version=avo_result["best_version"],
            mean_score=bench_summary["mean_score"],
            accepted=bench_summary["passed_tasks"],
            stagnation_events=sum(
                1 for h in avo_result["history"] if h.get("stagnation")
            ),
            memory_entries=avo_result["memory_stats"]["total_entries"],
            lineage_versions=avo_result["lineage_stats"]["total_versions"],
            meta={
                "goal": self.goal,
                "bench_measured": bench_summary["measured"],
            },
        )
        self._rounds.append(round_rec)
        self._save()
        logger.info("Round %d finished: best=%s score=%.3f", round_num, round_rec.best_version, round_rec.mean_score)
        return round_rec

    def run(self) -> List[EvolutionRound]:
        round_num = 0
        try:
            while self.max_rounds is None or round_num < self.max_rounds:
                round_num += 1
                self.run_once()
                if self.max_rounds and round_num >= self.max_rounds:
                    break
                logger.info("Sleeping %.0fs before next round", self.sleep_seconds)
                time.sleep(self.sleep_seconds)
        except KeyboardInterrupt:
            logger.info("Continuous evolution stopped by user after %d rounds", round_num)
        self._save()
        return self._rounds

    def summary(self) -> Dict[str, Any]:
        if not self._rounds:
            return {"rounds": 0, "best_mean_score": 0.0, "total_accepted": 0}
        return {
            "rounds": len(self._rounds),
            "best_mean_score": max(r.mean_score for r in self._rounds),
            "total_accepted": sum(r.accepted for r in self._rounds),
            "total_stagnation_events": sum(r.stagnation_events for r in self._rounds),
            "total_lineage_versions": sum(r.lineage_versions for r in self._rounds),
            "last_round": self._rounds[-1].to_dict() if self._rounds else None,
        }

    # -- Persistence -------------------------------------------------

    def _save(self) -> None:
        data = {
            "goal": self.goal,
            "rounds": [r.to_dict() for r in self._rounds],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp = self._state_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self._state_path)

    def _load(self) -> None:
        if not self._state_path.exists():
            return
        try:
            with open(self._state_path, encoding="utf-8") as f:
                data = json.load(f)
            for rd in data.get("rounds", []):
                self._rounds.append(EvolutionRound(**rd))
        except (json.JSONDecodeError, OSError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes continuous evolution engine")
    parser.add_argument("--goal", default="optimize", help="Optimization goal")
    parser.add_argument("--max-iterations", type=int, default=50)
    parser.add_argument("--max-no-improve", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=60.0, help="Seconds between rounds")
    parser.add_argument("--max-rounds", type=int, default=None, help="Stop after N rounds")
    parser.add_argument("--store-dir", default=".evo_continuous")
    parser.add_argument("--onetime", action="store_true", help="Run one round and exit")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    engine = ContinuousEngine(
        goal=args.goal,
        max_iterations=args.max_iterations,
        max_no_improve=args.max_no_improve,
        sleep_seconds=args.sleep,
        store_dir=args.store_dir,
        max_rounds=args.max_rounds,
    )
    if args.onetime:
        r = engine.run_once()
        print(json.dumps(r.to_dict(), indent=2))
        return
    rounds = engine.run()
    print(json.dumps(engine.summary(), indent=2))


if __name__ == "__main__":
    main()
