# Hermes AGI/ASI Harness — Development Makefile

.PHONY: help install install-dev test test-cov lint format typecheck security docs clean build deploy

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
	pytest tests/ -x -q

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src/harness --cov-report=term-missing --cov-report=html

test-all: ## Run all tests (including slow)
	pytest tests/ -v

test-parallel: ## Run tests in parallel
	pytest tests/ -n auto -q

# ===== Linting & Formatting =====

lint: ## Run linter (ruff)
	ruff check src/ tests/

lint-fix: ## Fix lint issues
	ruff check --fix src/ tests/

format: ## Format code
	ruff format src/ tests/

typecheck: ## Run type checker
	mypy src/harness/

# ===== Security =====

security: ## Run security scans
	bandit -r src/ -c pyproject.toml
	pip-audit -r requirements.txt

# ===== Documentation =====

docs-serve: ## Serve docs locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build

docs-deploy: ## Deploy docs to GitHub Pages
	mkdocs gh-deploy --force

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

# ===== Release =====
bump-patch: ## Bump patch version
	bump2version patch

bump-minor: ## Bump minor version
	bump2version minor

bump-major: ## Bump major version
	bump2version major
