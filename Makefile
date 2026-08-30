# Hermes AGI/ASI Harness — Development Makefile

.PHONY: help install install-dev test test-cov lint format typecheck security docs clean build deploy ci ci-local

PYTHON := python
PIP := uv pip
VENV := .venv

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ===== Installation =====

install: ## Install production dependencies
	uv pip install -e .

install-dev: ## Install development dependencies
	uv pip install -e ".[dev,docs,security]"
	pre-commit install

# ===== Testing =====

test: ## Run tests
	uv run python -m pytest tests/ -x -q

test-cov: ## Run tests with coverage
	uv run python -m pytest tests/ --cov=src/harness --cov-report=term-missing --cov-report=html

test-all: ## Run all tests (including slow)
	uv run python -m pytest tests/ -v

test-parallel: ## Run tests in parallel
	uv run python -m pytest tests/ -n auto -q

# ===== Linting & Formatting =====

lint: ## Run linter (ruff)
	uv run ruff check src/ tests/

lint-fix: ## Fix lint issues
	uv run ruff check --fix src/ tests/

format: ## Format code
	uv run ruff format src/ tests/

typecheck: ## Run type checker
	uv run mypy src/harness/

# ===== Security =====

security: ## Run security scans
	uv run bandit -r src/ -c pyproject.toml
	uv run pip-audit -r requirements.txt

# ===== Documentation =====

docs-serve: ## Serve docs locally
	uv run mkdocs serve

docs-build: ## Build documentation
	uv run mkdocs build

docs-deploy: ## Deploy docs to GitHub Pages
	uv run mkdocs gh-deploy --force

# ===== Docker =====

docker-build: ## Build Docker image
	docker build -t hermes-agi-asi-harness:latest .

docker-run: ## Run Docker container
	docker-compose up -d

docker-stop: ## Stop Docker container
	docker-compose down

# ===== Build & Release =====

build: ## Build package
	uv build

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# ===== CI (all checks) =====
ci: lint typecheck test security ## Run all CI checks locally
	@echo "All CI checks passed!"

ci-local: ## Run full CI pipeline locally (like GitHub Actions)
	@echo "=== Running local CI pipeline ==="
	@echo "--- Lint ---"
	$(MAKE) lint
	@echo "--- Type Check ---"
	$(MAKE) typecheck
	@echo "--- Test ---"
	$(MAKE) test
	@echo "--- Security ---"
	$(MAKE) security
	@echo "--- Build ---"
	$(MAKE) build
	@echo "=== All CI checks passed! ==="

# ===== Release =====
bump-patch: ## Bump patch version
	bump2version patch

bump-minor: ## Bump minor version
	bump2version minor

bump-major: ## Bump major version
	bump2version major
