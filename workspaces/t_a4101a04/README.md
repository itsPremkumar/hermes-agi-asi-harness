# CodeReview Bot — Automated Pull Request Review

A GitHub App that provides AI-powered code review with static analysis, security scanning, and custom rule engine.

## Features

- **GitHub App Integration** — Webhook-driven PR review automation
- **Static Analysis** — pylint, mypy, ruff, eslint integration
- **AI-Powered Review** — LLM-based code suggestions and improvements
- **Security Scanning** — Detect vulnerabilities and insecure patterns
- **Performance Regression** — Identify performance anti-patterns
- **Test Coverage Impact** — Analyze coverage changes in PRs
- **Review Assignment** — CODEOWNERS-based reviewer assignment
- **Custom Rule Engine** — YAML-configurable review rules
- **Slack/Teams Integration** — Notifications and review summaries

## Quick Start

```bash
pip install -e ".[dev]"
codereview-bot
```

## Configuration

Set environment variables:

```bash
export GITHUB_APP_ID=123456
export GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
export GITHUB_WEBHOOK_SECRET=your-webhook-secret
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
```

## Architecture

```
src/codereview_bot/
├── __init__.py          # Package version
├── app.py               # FastAPI entry point
├── config.py            # Configuration management
├── github_app.py        # GitHub App authentication & webhooks
├── review.py            # Core review orchestrator
├── static_analysis.py   # pylint/mypy/ruff/eslint integration
├── ai_review.py         # LLM-powered code review
├── security.py          # Security vulnerability scanning
├── performance.py       # Performance regression detection
├── coverage.py          # Test coverage impact analysis
├── assignment.py        # Reviewer assignment (CODEOWNERS)
├── rules.py             # Custom rule engine
├── notifications.py     # Slack/Teams integration
└── models.py            # Data models
```

## License

MIT
