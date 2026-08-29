"""Tests for evidence collection and cloud integrations."""

from __future__ import annotations

import os
import pytest
from pathlib import Path

from compliance_as_code.evidence import (
    EvidenceArtifact,
    EvidenceCollector,
    ConfigurationEvidenceCollector,
    EnvironmentEvidenceCollector,
    LogEvidenceCollector,
    EvidenceStore,
)
from compliance_as_code.cloud import (
    CloudProvider,
    CloudResource,
    AWSConfigIntegration,
    AzurePolicyIntegration,
    GCPComplianceIntegration,
    get_cloud_integration,
)


class TestEvidenceArtifact:
    """Tests for EvidenceArtifact."""

    def test_checksum_computed(self):
        artifact = EvidenceArtifact(
            artifact_id="test-001",
            control_id="SOC2-CC6.1",
            source="test",
            content_type="text/plain",
            content={"key": "value"},
        )
        assert artifact.checksum is not None
        assert len(artifact.checksum) == 64  # SHA-256 hex

    def test_to_dict(self):
        artifact = EvidenceArtifact(
            artifact_id="test-001",
            control_id="SOC2-CC6.1",
            source="test",
            content_type="text/plain",
            content={"key": "value"},
        )
        data = artifact.to_dict()
        assert data["artifact_id"] == "test-001"
        assert data["checksum"] is not None


class TestConfigurationEvidenceCollector:
    """Tests for ConfigurationEvidenceCollector."""

    def test_collect_existing_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("setting: value")

        collector = ConfigurationEvidenceCollector([str(config_file)])
        artifacts = collector.collect()

        assert len(artifacts) == 1
        assert artifacts[0].source == str(config_file)

    def test_collect_missing_file(self, tmp_path):
        collector = ConfigurationEvidenceCollector([str(tmp_path / "nonexistent.yaml")])
        artifacts = collector.collect()

        assert len(artifacts) == 0


class TestEnvironmentEvidenceCollector:
    """Tests for EnvironmentEvidenceCollector."""

    def test_collect_env_vars(self, monkeypatch):
        monkeypatch.setenv("COMPLIANCE_ENABLED", "true")
        monkeypatch.setenv("SECURITY_LEVEL", "high")
        monkeypatch.setenv("UNRELATED_VAR", "ignore")

        collector = EnvironmentEvidenceCollector()
        artifacts = collector.collect()

        assert len(artifacts) == 1
        content = artifacts[0].content
        assert "COMPLIANCE_ENABLED" in content
        assert "SECURITY_LEVEL" in content
        assert "UNRELATED_VAR" not in content


class TestLogEvidenceCollector:
    """Tests for LogEvidenceCollector."""

    def test_collect_matching_logs(self, tmp_path):
        log_file = tmp_path / "app.log"
        log_file.write_text("INFO: User authentication successful\nERROR: Disk full\n")

        collector = LogEvidenceCollector(tmp_path)
        artifacts = collector.collect()

        assert len(artifacts) == 1
        assert len(artifacts[0].content["matching_lines"]) == 1

    def test_no_logs(self, tmp_path):
        collector = LogEvidenceCollector(tmp_path)
        artifacts = collector.collect()
        assert len(artifacts) == 0


class TestEvidenceStore:
    """Tests for EvidenceStore."""

    def test_save_and_load(self, tmp_path):
        store = EvidenceStore(tmp_path / "evidence")
        artifact = EvidenceArtifact(
            artifact_id="test-001",
            control_id="SOC2-CC6.1",
            source="test",
            content_type="text/plain",
            content={"key": "value"},
        )

        path = store.save(artifact)
        assert path.exists()

        loaded = store.load("test-001")
        assert loaded is not None
        assert loaded.artifact_id == "test-001"

    def test_list_all(self, tmp_path):
        store = EvidenceStore(tmp_path / "evidence")
        artifact = EvidenceArtifact(
            artifact_id="test-001",
            control_id="SOC2-CC6.1",
            source="test",
            content_type="text/plain",
            content={"key": "value"},
        )
        store.save(artifact)

        all_files = store.list_all()
        assert len(all_files) == 1


class TestCloudIntegrations:
    """Tests for cloud provider integrations."""

    def test_aws_integration(self):
        integration = AWSConfigIntegration(region="us-west-2")
        resources = integration.list_resources()
        assert len(resources) > 0

        summary = integration.get_compliance_summary()
        assert summary["provider"] == "AWS"
        assert summary["total_resources"] > 0

    def test_azure_integration(self):
        integration = AzurePolicyIntegration(subscription_id="test-sub")
        resources = integration.list_resources()
        assert len(resources) > 0

        summary = integration.get_compliance_summary()
        assert summary["provider"] == "Azure"

    def test_gcp_integration(self):
        integration = GCPComplianceIntegration(project_id="test-project")
        resources = integration.list_resources()
        assert len(resources) > 0

        summary = integration.get_compliance_summary()
        assert summary["provider"] == "GCP"

    def test_factory_function(self):
        aws = get_cloud_integration(CloudProvider.AWS, region="eu-west-1")
        assert isinstance(aws, AWSConfigIntegration)

        azure = get_cloud_integration(CloudProvider.AZURE, subscription_id="sub")
        assert isinstance(azure, AzurePolicyIntegration)

        gcp = get_cloud_integration(CloudProvider.GCP, project_id="proj")
        assert isinstance(gcp, GCPComplianceIntegration)
