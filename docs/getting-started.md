# Getting Started

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

## Installation

### From Source

```bash
git clone https://github.com/itsPremkumar/hermes-agi-asi-harness.git
cd hermes-agi-asi-harness
uv pip install -e ".[dev]"
```

### Docker

```bash
docker-compose up -d
```

## Quick Start

```python
from harness import Harness

h = Harness()
h.load_plugin("safety")
h.load_plugin("reasoning")
h.run()
```

## Running Tests

```bash
# All tests
pytest tests/ -x

# With coverage
pytest tests/ --cov=src/harness --cov-report=html

# Parallel
pytest tests/ -n auto
```

## Development Setup

```bash
# Install dev dependencies
make install-dev

# Run all CI checks locally
make ci

# Run linter
make lint

# Format code
make format

# Type check
make typecheck
```

## Project Structure

```
hermes-agi-asi-harness/
├── src/harness/          # Main package
│   ├── core/             # Core components
│   ├── plugins/          # Plugin implementations
│   ├── config.py         # Configuration
│   ├── health.py         # Health checks
│   └── lifecycle.py      # Lifecycle management
├── tests/                # Test suite
├── docs/                 # Documentation
├── .github/workflows/    # CI/CD pipelines
├── pyproject.toml        # Project manifest
├── Makefile              # Dev commands
├── Dockerfile            # Container image
└── docker-compose.yml    # Local dev environment
```

## Next Steps

- Read the [Architecture](architecture.md) guide
- Explore the [API Reference](api.md)
- See [Contributing](contributing.md) for how to contribute
