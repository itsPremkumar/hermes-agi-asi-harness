"""GitHub App authentication and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any

import jwt


class GitHubAppAuth:
    """Handles GitHub App JWT and installation token authentication."""

    def __init__(self, app_id: int, private_key: str):
        self.app_id = app_id
        self.private_key = private_key

    def generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication."""
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued at time (60s clock drift buffer)
            "exp": now + 600,  # Expiration time (10 min max)
            "iss": str(self.app_id),
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature."""
        if not signature.startswith("sha256="):
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature[7:], expected)


class GitHubAPI:
    """GitHub API client for App installations."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodeReview-Bot/1.0",
        }

    async def create_check_run(
        self,
        owner: str,
        repo: str,
        name: str,
        head_sha: str,
        status: str = "in_progress",
        conclusion: str | None = None,
        output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a check run for a commit."""
        import httpx

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/check-runs"
        data: dict[str, Any] = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
        }
        if conclusion:
            data["conclusion"] = conclusion
        if output:
            data["output"] = output

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=data, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a pull request review."""
        import httpx

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        data: dict[str, Any] = {
            "body": body,
            "event": event,
        }
        if comments:
            data["comments"] = comments

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=data, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the diff for a pull request."""
        import httpx

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> str:
        """Get file content from a repository."""
        import httpx

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}?ref={ref}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            import base64
            return base64.b64decode(data["content"]).decode("utf-8")
