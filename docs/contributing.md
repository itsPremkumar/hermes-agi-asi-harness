# Contributing

Thank you for your interest in contributing! Here's how to get involved.

## Development Setup

```bash
git clone https://github.com/itsPremkumar/hermes-agi-asi-harness.git
cd hermes-agi-asi-harness
make install-dev
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
make lint        # Check code
make lint-fix    # Fix issues
make format      # Format code
```

Type checking with mypy:

```bash
make typecheck
```

## Testing

```bash
make test              # Run tests
make test-cov          # With coverage
make test-all          # Including slow tests
make test-parallel     # Parallel execution
```

All PRs must have ≥80% coverage and all tests passing.

## Pull Request Process

1. Fork the repo and create a feature branch (`feat/your-feature`)
2. Write tests for new functionality
3. Ensure all CI checks pass (`make ci`)
4. Update documentation
5. Submit a PR with a clear description

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Tests
- `refactor:` — Code refactor
- `chore:` — Maintenance

Example: `feat(plugin): add sentiment analysis plugin`

## Plugin Development

```python
from harness.plugin_base import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"
    description = "Does something useful"

    def setup(self):
        """Called on plugin load"""
        pass

    def run(self, input_data):
        """Main plugin logic"""
        return input_data

    def teardown(self):
        """Cleanup on unload"""
        pass
```

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints

## License

By contributing, you agree your contributions will be licensed under the MIT License.
