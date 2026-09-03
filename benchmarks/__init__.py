"""
Hermes Capacity Benchmark Suite.

Independent benchmark evaluation suite for measuring agent and model capacity
across reasoning, coding, math, commonsense, software engineering, and safety.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow relative and package-level imports
_CURRENT_DIR = str(Path(__file__).parent.resolve())
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

# Register alias so imports from "benchmark" resolve to "benchmarks"
sys.modules.setdefault("benchmark", sys.modules[__name__])

from .mmlu_benchmark import MMLUBenchmark
from .gsm8k_benchmark import GSM8KBenchmark
from .hellaswag_benchmark import HellaSwagBenchmark
from .human_eval_benchmark import HumanEvalBenchmark
from .mbpp_benchmark import MBPPBenchmark
from .boolq_benchmark import BoolQBenchmark
from .piqa_benchmark import PIQABenchmark
from .siqa_benchmark import SIQABenchmark
from .openbookqa_benchmark import OpenBookQABenchmark
from .wino_grande_benchmark import WinogradBenchmark, WinogradBenchmark as WinoGrandeBenchmark
from .winogender_benchmark import WinogenderBenchmark
from .real_toxicity_prompts_benchmark import RealToxicityPromptsBenchmark
from .swe_bench_pro_benchmark import SWEBenchPro
from .swe_bench_verified_benchmark import SWEBenchVerifiedBenchmark, SWEBenchVerifiedBenchmark as SWEBenchVerified
from .arc_agi_3_full_eval import FullEvaluationSuite as ARCAGI3FullEval
from .score_aggregator import ScoreAggregator
from .full_evaluation_suite import FullEvaluationSuite
from .evaluation_suite import EvaluationSuite

BENCHMARK_REGISTRY = {
    "mmlu": MMLUBenchmark,
    "gsm8k": GSM8KBenchmark,
    "humaneval": HumanEvalBenchmark,
    "mbpp": MBPPBenchmark,
    "swe_bench_pro": SWEBenchPro,
    "swe_bench_verified": SWEBenchVerifiedBenchmark,
    "hellaswag": HellaSwagBenchmark,
    "boolq": BoolQBenchmark,
    "piqa": PIQABenchmark,
    "openbookqa": OpenBookQABenchmark,
    "siqa": SIQABenchmark,
    "winogrande": WinogradBenchmark,
    "winogender": WinogenderBenchmark,
    "real_toxicity_prompts": RealToxicityPromptsBenchmark,
    "arc_agi_3": ARCAGI3FullEval,
}

__all__ = [
    "MMLUBenchmark",
    "GSM8KBenchmark",
    "HellaSwagBenchmark",
    "HumanEvalBenchmark",
    "MBPPBenchmark",
    "BoolQBenchmark",
    "PIQABenchmark",
    "SIQABenchmark",
    "OpenBookQABenchmark",
    "WinogradBenchmark",
    "WinoGrandeBenchmark",
    "WinogenderBenchmark",
    "RealToxicityPromptsBenchmark",
    "SWEBenchPro",
    "SWEBenchVerified",
    "SWEBenchVerifiedBenchmark",
    "ARCAGI3FullEval",
    "ScoreAggregator",
    "FullEvaluationSuite",
    "EvaluationSuite",
    "BENCHMARK_REGISTRY",
]
