"""Quick smoke test for both benchmark modules."""

from src.security.benchmark_security import SecurityBenchmark
from src.benchmark.winogender_benchmark import WinogenderBenchmark


def main():
    # Run security benchmark
    sb = SecurityBenchmark()
    results = sb.run_all()
    score = sb.get_overall_score()
    print("=== SECURITY BENCHMARK ===")
    for r in results:
        print(f"  {r.plugin}: {r.passed}/{r.total} passed ({r.pass_rate:.1%})")
    print(f"  Overall: {score['total_passed']}/{score['total']} ({score['pass_rate']:.1%})")
    print()

    # Run winogender benchmark
    wb = WinogenderBenchmark()
    wb.load_problems()
    result = wb.run_all(genders=["male", "female"])
    print("=== WINOGENDER BIAS BENCHMARK ===")
    print(f"  Problems: {result.total_problems}")
    print(f"  Accuracy: {result.accuracy:.1%}")
    print(f"  Bias detected: {result.bias_detected} ({result.bias_rate:.1%})")
    print(f"  Occupations tested: 24")


if __name__ == "__main__":
    main()
