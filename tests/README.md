# Test Suite

This directory contains the complete test suite for the Hermes AGI/ASI Harness.

## Structure

```
tests/
├── test_core.py                      # Core config, HA, Hermes integration
├── test_harness.py                   # Harness control plane tests
├── test_plugins.py                   # Plugin system tests
├── test_operations.py                # Operations tests
├── test_production.py                # Production readiness tests
├── test_pipeline.py                  # Training pipeline tests
├── test_continuous_dev.py            # Continuous development tests
├── test_daily_improvement_scheduler.py # Scheduler tests
├── test_deploy.py                    # Deployment tests
├── test_threat_modeler.py            # Security threat modeler tests
├── test_coding_phase1.py             # Coding phase 1 tests
├── test_v9_core.py                   # V9 core tests
├── test_v9_full.py                   # V9 full integration tests
├── test_v10_full.py                  # V10 full system tests
├── test_v11_coding.py                # V11 coding intelligence tests
├── test_v11_dynamic.py               # V11 dynamic workflow tests
├── test_v11_workflow.py              # V11 workflow tests
└── test_coding_phase1.py             # Coding tests
```

## Running Tests

```bash
# All tests
pytest tests/ -x

# With coverage
pytest tests/ --cov=src/harness --cov-report=html

# Parallel execution
pytest tests/ -n auto

# Specific test file
pytest tests/test_core.py -v

# Specific test class
pytest tests/test_core.py::TestDynamicConfig -v

# Specific test
pytest tests/test_core.py::TestDynamicConfig::test_create -v
```

## Test Categories

- **Unit Tests** — Test individual components in isolation
- **Integration Tests** — Test component interactions
- **Production Tests** — Test production readiness
- **Security Tests** — Test security features

## Coverage Requirements

- Minimum coverage: 80%
- Current coverage: See CI badge in README

## Writing Tests

```python
import pytest
from harness.core.dynamic_config import DynamicConfig

class TestMyFeature:
    def test_basic(self):
        config = DynamicConfig()
        assert config.get_all() == {}

    def test_with_fixture(self, tmp_path):
        # Use pytest fixtures
        pass

    @pytest.mark.slow
    def test_slow_operation(self):
        # Mark slow tests
        pass

    @pytest.mark.asyncio
    async def test_async_operation(self):
        # Async tests
        pass
```
