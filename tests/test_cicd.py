"""Tests for CI/CD integration."""
import pytest

from hermes.core.cicd import CICDManager, CICDPlatform, GitHubActionsIntegration, GitLabCIIntegration


class TestCICDManager:
    def test_create(self):
        manager = CICDManager()
        assert manager.github is not None
        assert manager.gitlab is not None

    def test_detect_github(self, tmp_path):
        manager = CICDManager()
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        platform = manager.detect_platform(str(tmp_path))
        assert platform == CICDPlatform.GITHUB_ACTIONS

    def test_detect_gitlab(self, tmp_path):
        manager = CICDManager()
        (tmp_path / ".gitlab-ci.yml").touch()
        platform = manager.detect_platform(str(tmp_path))
        assert platform == CICDPlatform.GITLAB_CI

    def test_detect_jenkins(self, tmp_path):
        manager = CICDManager()
        (tmp_path / "Jenkinsfile").touch()
        platform = manager.detect_platform(str(tmp_path))
        assert platform == CICDPlatform.JENKINS

    def test_detect_none(self, tmp_path):
        manager = CICDManager()
        platform = manager.detect_platform(str(tmp_path))
        assert platform is None

    @pytest.mark.asyncio
    async def test_handle_github_webhook(self):
        manager = CICDManager()
        payload = {"action": "completed", "workflow_run": {"conclusion": "success", "name": "CI"}}
        result = await manager.handle_webhook("github", payload)
        assert result is not None
        assert result["event"] == "workflow_completed"

    @pytest.mark.asyncio
    async def test_handle_unknown_webhook(self):
        manager = CICDManager()
        result = await manager.handle_webhook("unknown", {})
        assert result is None


class TestGitHubActionsIntegration:
    def test_create(self):
        gh = GitHubActionsIntegration()
        assert gh.api_base == "https://api.github.com"

    @pytest.mark.asyncio
    async def test_handle_completed(self):
        gh = GitHubActionsIntegration()
        payload = {"action": "completed", "workflow_run": {"conclusion": "success"}}
        result = await gh.handle_webhook(payload)
        assert result["status"] == "success"


class TestGitLabCIIntegration:
    def test_create(self):
        gl = GitLabCIIntegration()
        assert gl.base_url == "https://gitlab.com"
