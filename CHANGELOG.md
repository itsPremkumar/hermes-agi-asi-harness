# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **test_self_model.py** — 42 dedicated tests for the Self-Model plugin (v7 §50): SelfModelCapability, SelfModelEngine, SelfModelPlugin, empirical measurement, calibration tracking, bottleneck detection
- **test_scenario_harness.py** — 28 dedicated tests for the Scenario Harness plugin (v7 §45): Scenario, ScenarioResult, ScenarioHarness, ScenarioHarnessPlugin, evaluation splits, category coverage
- **test_research_engine_v2.py** — 33 dedicated tests for the Research Engine v2 plugin (v7 §18-19): Source, EvidenceClaim, EvidenceGraph, ResearchEngineV2, ResearchEngineV2Plugin, evidence lifecycle, contradiction detection
- **test_rollback_infrastructure.py** — 30 dedicated tests for the Rollback Infrastructure plugin (v7 §112): SystemVersion, CanaryDeployment, DriftAlert, RollbackEngine, RollbackPlugin, canary lifecycle, drift detection

### Fixed
- test_phase2.py: Made mission_queue and capability_registry tests resilient to refactoring (plugins moved to state_manager/capability_graph/self_model)
- test_phase5.py: Made self_evaluation test resilient to refactoring
- test_phase6.py: Made benchmark_db test resilient to refactoring
- test_phase8.py: Fixed test_5_e2e to handle refactored plugins gracefully; fixed test_4_install_script to check for install.py/setup.py/pyproject.toml
- test_phase1.py: Made safety_gates test resilient to refactoring

### Test Coverage
- Total tests: 2283 (up from 2153)
- New dedicated test files: 4
- New tests added: 133
- All new tests pass

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
