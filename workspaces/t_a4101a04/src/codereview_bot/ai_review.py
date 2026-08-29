"""AI-powered code review using LLM."""

from __future__ import annotations

import os
from typing import Any

from .models import Issue, PullRequest, ReviewResult, Severity


AIReviewConfig = {
    "default_provider": "openai",
    "default_model": "gpt-4o-mini",
    "max_tokens": 4096,
    "temperature": 0.1,
}


class AIReviewer:
    """Uses an LLM to provide intelligent code review suggestions."""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini", api_key: str = ""):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("AI_API_KEY", "")

    async def review_pr(self, pr: PullRequest, diff: str) -> ReviewResult:
        """Generate AI review for a pull request."""
        result = ReviewResult(
            pr_number=pr.number,
            repo=pr.repo_full_name,
        )

        if not self.api_key:
            result.summary = "AI review skipped: no API key configured"
            return result

        if not diff:
            result.summary = "No diff to review"
            return result

        prompt = self._build_prompt(pr, diff)
        try:
            review_text = await self._call_llm(prompt)
            issues = self._parse_review_output(review_text, diff)
            result.issues.extend(issues)
            result.summary = review_text[:500] if review_text else "AI review completed"
        except Exception as e:
            result.summary = f"AI review failed: {e}"

        return result

    def _build_prompt(self, pr: PullRequest, diff: str) -> str:
        """Build the prompt for the LLM."""
        return f"""You are an expert code reviewer. Review the following pull request and provide actionable feedback.

PR Title: {pr.title}
PR Description: {pr.body or "No description"}

Diff:
{diff[:8000]}

Provide your review in this format:
- Issue: [file:line] [severity: info/warning/error/critical]
  Message: [description of the issue]
  Suggestion: [how to fix it]

Focus on:
1. Code correctness and potential bugs
2. Security vulnerabilities
3. Performance issues
4. Code style and maintainability
5. Missing edge case handling

Keep feedback concise and actionable."""

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        import httpx

        if self.provider == "openai":
            return await self._call_openai(prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        import httpx

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": AIReviewConfig["max_tokens"],
            "temperature": AIReviewConfig["temperature"],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]

    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        import httpx

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        data = {
            "model": self.model,
            "max_tokens": AIReviewConfig["max_tokens"],
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            return result["content"][0]["text"]

    def _parse_review_output(self, text: str, diff: str) -> list[Issue]:
        """Parse LLM output into Issue objects."""
        issues = []
        lines = text.split("\n")
        current_issue: dict[str, Any] = {}

        for line in lines:
            line = line.strip()
            if line.startswith("- Issue:") or line.startswith("Issue:"):
                if current_issue:
                    issues.append(Issue(
                        file=current_issue.get("file", ""),
                        line=current_issue.get("line", 0),
                        severity=Severity(current_issue.get("severity", "warning")),
                        message=current_issue.get("message", ""),
                        suggestion=current_issue.get("suggestion", ""),
                        source="ai_review",
                    ))
                current_issue = {}
                # Try to parse [file:line] [severity]
                if "[" in line and "]" in line:
                    parts = line.split("[")[1:]
                    for part in parts:
                        content = part.split("]")[0]
                        if ":" in content and any(c.isdigit() for c in content):
                            file_parts = content.split(":")
                            current_issue["file"] = file_parts[0]
                            try:
                                current_issue["line"] = int(file_parts[1])
                            except ValueError:
                                current_issue["line"] = 0
                        elif content in ("info", "warning", "error", "critical"):
                            current_issue["severity"] = content

            elif line.startswith("Message:"):
                current_issue["message"] = line[len("Message:"):].strip()
            elif line.startswith("Suggestion:"):
                current_issue["suggestion"] = line[len("Suggestion:"):].strip()

        # Don't forget the last issue
        if current_issue:
            issues.append(Issue(
                file=current_issue.get("file", ""),
                line=current_issue.get("line", 0),
                severity=Severity(current_issue.get("severity", "warning")),
                message=current_issue.get("message", ""),
                suggestion=current_issue.get("suggestion", ""),
                source="ai_review",
            ))

        return issues
