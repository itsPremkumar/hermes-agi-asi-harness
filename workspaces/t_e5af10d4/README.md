# TestPilot — AI-Powered Test Generation Platform

TestPilot is a comprehensive test automation platform that combines static analysis,
AI-driven test generation, E2E testing, visual regression, contract testing, performance
testing, synthetic data generation, flaky test detection, and CI/CD quality gates.

## Features

1. **Static Analysis Engine** — Detects test gaps by analyzing code coverage and identifying
   untested functions, branches, and edge cases.
2. **AI Test Case Generation** — Generates test cases from natural language requirements
   using LLM integration.
3. **Playwright E2E Runner** — Browser-based end-to-end test execution with automatic
   waiting, screenshots, and tracing.
4. **Visual Regression Testing** — Pixel-perfect image diff to catch unintended UI changes.
5. **API Contract Testing** — Pact-compatible consumer-driven contract verification.
6. **Performance Testing** — Integration with Locust and k6 for load testing.
7. **Test Data Management** — Synthetic data generation using Faker with deterministic seeding.
8. **Flaky Test Detection** — Statistical analysis to identify and quarantine flaky tests.
9. **CI/CD Quality Gates** — Automated pass/fail gates for pipelines.

## Installation

```bash
pip install testpilot
```

## Quick Start

```bash
# Run static analysis
testpilot analyze ./src

# Generate AI tests from requirements
testpilot generate --requirement "User can login with email and password" --output tests/

# Run E2E tests
testpilot e2e --browser chromium

# Run visual regression
testpilot visual --baseline ./baselines --current ./screenshots

# Run contract tests
testpilot contract --pact-dir ./pacts

# Run performance tests
testpilot perf --tool locust --users 100 --duration 60s

# Run full quality gate suite
testpilot gate --config testpilot.yaml
```

## Requirements

- Python >= 3.10
- Playwright browsers (for E2E)
- Node.js (for k6 performance tests)
