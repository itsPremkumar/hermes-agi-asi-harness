# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Pytest collection error caused by `test_pass = _pass` alias in test_phase3_4.py, test_phase5.py, test_phase6.py, test_phase7.py, test_phase8.py — removed the alias and replaced all `test_pass()` calls with `_pass()` to prevent pytest from collecting them as test functions
- All 1995 tests now pass (previously 39 failed due to pytest NameError/collection issues)

### Added
- Created state/self_model.json with empirical capability metrics (test counts, pass rates, calibration)
- Created state/belief_graph.json with structured belief tracking
- Complete CI/CD pipeline with GitHub Actions
- Docker multi-stage build and docker-compose for local dev
- Pre-commit hooks for code quality
- Mkdocs documentation site
- Monitoring stack (Prometheus + Grafana)
- Security scanning (bandit, pip-audit)
- Type checking with mypy
- Linting and formatting with ruff
- Test coverage reporting
- Release automation (PyPI, GitHub Releases)

## [1.0.0] - 2026-08-30

### Added
- Plugin framework with 82+ plugins
- Dynamic configuration with hot-reload
- High availability (circuit breaker, failover, degradation)
- Hermes Agent integration (profiles, kanban, cron, MCP)
- Continuous development system (24/7 improvement loop)
- A/B testing and canary deployments
- Rollback capabilities
- Progress dashboard
- Training pipeline with fine-tuning
- Daily improvement scheduler
- Threat modeler for security analysis
- Proof checker for formal verification
- Capability registry (31 capabilities, 5 domains)
- V9 engineering operations (CI, deploy, incidents, releases)
- V10 full system integration
- V11 coding intelligence and dynamic workflows

[Unreleased]: https://github.com/itsPremkumar/hermes-agi-asi-harness/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/itsPremkumar/hermes-agi-asi-harness/releases/tag/v1.0.0
