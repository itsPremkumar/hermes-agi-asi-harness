"""
TestPilot — AI-Powered Test Generation Platform
================================================
A comprehensive test automation platform with:
- Static analysis engine for test gap detection
- AI test case generation from requirements
- Playwright-based E2E test runner
- Visual regression testing (pixel-perfect diff)
- API contract testing (Pact-compatible)
- Performance testing integration (Locust, k6)
- Test data management (synthetic data generation)
- Flaky test detection and quarantine
- CI/CD integration with quality gates
"""
__version__ = "1.0.0"
__all__ = [
    "static_analysis",
    "ai_test_gen",
    "e2e_runner",
    "visual_regression",
    "contract_testing",
    "perf_integration",
    "test_data",
    "flaky_detect",
    "quality_gates",
    "cli",
]
