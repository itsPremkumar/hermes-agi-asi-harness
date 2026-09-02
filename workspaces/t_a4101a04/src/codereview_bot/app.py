"""FastAPI entry point for CodeReview Bot."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from .config import Config
from .github_app import GitHubAppAuth, GitHubAPI
from .models import PullRequest
from .review import ReviewOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
config = Config.from_env()
orchestrator = ReviewOrchestrator(config)
auth: GitHubAppAuth | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global auth
    if config.github_private_key_path and Path(config.github_private_key_path).exists():
        private_key = Path(config.github_private_key_path).read_text()
        auth = GitHubAppAuth(config.github_app_id, private_key)
        logger.info("GitHub App auth initialized for app ID %s", config.github_app_id)
    else:
        logger.warning("GitHub App auth not initialized: private key not found")
    yield
    # Cleanup
    auth = None


app = FastAPI(
    title="CodeReview Bot",
    description="Automated Pull Request Review",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "codereview-bot", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request):
    """Handle GitHub webhook events."""
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    event_type = request.headers.get("x-github-event", "")

    # Verify webhook signature
    if config.github_webhook_secret and auth:
        if not auth.verify_webhook_signature(body, signature, config.github_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)

    # Handle pull request events
    if event_type == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            pr = PullRequest.from_webhook(payload)
            logger.info("Processing PR #%d from %s", pr.number, pr.repo_full_name)
            # Process asynchronously in production
            # For now, just acknowledge
            return {"status": "processing", "pr": pr.number}

    # Handle check run events
    if event_type == "check_run":
        action = payload.get("action", "")
        if action == "rerequested":
            # Re-run the check
            pass

    return {"status": "ok"}


@app.post("/review")
async def review_pr_endpoint(request: Request):
    """Manual review endpoint (for testing)."""
    data = await request.json()
    pr = PullRequest(
        number=data.get("pr_number", 0),
        title=data.get("title", ""),
        body=data.get("body", ""),
        head_sha=data.get("head_sha", ""),
        base_sha=data.get("base_sha", ""),
        head_ref=data.get("head_ref", ""),
        base_ref=data.get("base_ref", ""),
        user=data.get("user", ""),
        repo_full_name=data.get("repo", ""),
        diff_url=data.get("diff_url", ""),
    )
    diff = data.get("diff", "")
    result = await orchestrator.review_pr(pr, GitHubAPI(""), diff)
    return result.to_dict()


def main():
    """Run the application."""
    import uvicorn

    # Validate config
    errors = config.validate()
    if errors:
        for error in errors:
            logger.warning("Config error: %s", error)

    uvicorn.run(
        "codereview_bot.app:app",
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
