"""Cloud provider integrations — AWS Config, Azure Policy, GCP Security Command Center."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"


@dataclass
class CloudResource:
    """A cloud resource with compliance-relevant metadata."""
    resource_id: str
    resource_type: str
    provider: CloudProvider
    region: str
    tags: dict[str, str] = field(default_factory=dict)
    compliance_state: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "provider": self.provider.value,
            "region": self.region,
            "tags": self.tags,
            "compliance_state": self.compliance_state,
            "metadata": self.metadata,
        }


@dataclass
class ComplianceRuleResult:
    """Result of evaluating a cloud compliance rule."""
    rule_id: str
    rule_name: str
    resource_id: str
    compliant: bool
    severity: str
    description: str
    evidence: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "resource_id": self.resource_id,
            "compliant": self.compliant,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class CloudIntegration(ABC):
    """Base class for cloud provider compliance integrations."""

    def __init__(self, provider: CloudProvider):
        self.provider = provider

    @abstractmethod
    def list_resources(self, resource_type: str | None = None) -> list[CloudResource]:
        """List cloud resources, optionally filtered by type."""

    @abstractmethod
    def evaluate_rules(self, resources: list[CloudResource]) -> list[ComplianceRuleResult]:
        """Evaluate compliance rules against cloud resources."""

    @abstractmethod
    def get_compliance_summary(self) -> dict[str, Any]:
        """Get a compliance summary for the cloud account."""


class AWSConfigIntegration(CloudIntegration):
    """Integration with AWS Config for compliance monitoring."""

    # Common AWS Config managed rules relevant to compliance
    MANAGED_RULES = {
        "S3_BUCKET_PUBLIC_READ_PROHIBITED": {
            "severity": "CRITICAL",
            "description": "S3 buckets should not be publicly readable",
            "frameworks": ["SOC2", "PCI-DSS", "HIPAA"],
        },
        "S3_BUCKET_PUBLIC_WRITE_PROHIBITED": {
            "severity": "CRITICAL",
            "description": "S3 buckets should not be publicly writable",
            "frameworks": ["SOC2", "PCI-DSS", "HIPAA"],
        },
        "RDS_STORAGE_ENCRYPTED": {
            "severity": "HIGH",
            "description": "RDS DB instances should have encryption at rest",
            "frameworks": ["SOC2", "PCI-DSS", "HIPAA"],
        },
        "IAM_USER_MFA_ENABLED": {
            "severity": "HIGH",
            "description": "IAM users should have MFA enabled",
            "frameworks": ["SOC2", "PCI-DSS"],
        },
        "CLOUD_TRAIL_ENCRYPTION_ENABLED": {
            "severity": "MEDIUM",
            "description": "CloudTrail logs should be encrypted at rest",
            "frameworks": ["SOC2", "HIPAA"],
        },
        "SECURITYHUB_ENABLED": {
            "severity": "MEDIUM",
            "description": "Security Hub should be enabled",
            "frameworks": ["SOC2"],
        },
        "VPC_FLOW_LOGS_ENABLED": {
            "severity": "MEDIUM",
            "description": "VPC flow logs should be enabled",
            "frameworks": ["SOC2", "PCI-DSS"],
        },
        "ENCRYPTED_VOLUMES": {
            "severity": "HIGH",
            "description": "EBS volumes should be encrypted",
            "frameworks": ["SOC2", "PCI-DSS", "HIPAA"],
        },
    }

    def __init__(self, region: str = "us-east-1", profile: str | None = None):
        super().__init__(CloudProvider.AWS)
        self.region = region
        self.profile = profile

    def list_resources(self, resource_type: str | None = None) -> list[CloudResource]:
        """List AWS resources. Returns sample data when boto3 is not available."""
        resources = self._get_sample_resources()
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        return resources

    def evaluate_rules(self, resources: list[CloudResource]) -> list[ComplianceRuleResult]:
        """Evaluate AWS Config managed rules against resources."""
        results: list[ComplianceRuleResult] = []

        for rule_id, rule_meta in self.MANAGED_RULES.items():
            for resource in resources:
                result = self._evaluate_rule_for_resource(rule_id, rule_meta, resource)
                results.append(result)

        return results

    def get_compliance_summary(self) -> dict[str, Any]:
        """Get AWS Config compliance summary."""
        resources = self.list_resources()
        rule_results = self.evaluate_rules(resources)

        compliant = sum(1 for r in rule_results if r.compliant)
        non_compliant = sum(1 for r in rule_results if not r.compliant)

        return {
            "provider": "AWS",
            "region": self.region,
            "total_resources": len(resources),
            "total_rules_evaluated": len(rule_results),
            "compliant": compliant,
            "non_compliant": non_compliant,
            "compliance_percentage": round(
                (compliant / len(rule_results) * 100) if rule_results else 100, 2
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _evaluate_rule_for_resource(
        self, rule_id: str, rule_meta: dict[str, Any], resource: CloudResource
    ) -> ComplianceRuleResult:
        """Evaluate a single rule against a resource."""
        # Simplified evaluation logic — in production, this would call AWS Config API
        compliant = resource.compliance_state == "COMPLIANT"

        return ComplianceRuleResult(
            rule_id=rule_id,
            rule_name=rule_meta["description"],
            resource_id=resource.resource_id,
            compliant=compliant,
            severity=rule_meta["severity"],
            description=rule_meta["description"],
            evidence=f"Resource {resource.resource_id} state: {resource.compliance_state}",
        )

    def _get_sample_resources(self) -> list[CloudResource]:
        """Return sample AWS resources for demonstration."""
        return [
            CloudResource(
                resource_id="arn:aws:s3:::my-app-bucket",
                resource_type="AWS::S3::Bucket",
                provider=CloudProvider.AWS,
                region=self.region,
                tags={"Environment": "production", "DataClass": "confidential"},
                compliance_state="COMPLIANT",
            ),
            CloudResource(
                resource_id="arn:aws:rds:us-east-1:123456789:db:my-database",
                resource_type="AWS::RDS::DBInstance",
                provider=CloudProvider.AWS,
                region=self.region,
                tags={"Environment": "production"},
                compliance_state="COMPLIANT",
            ),
            CloudResource(
                resource_id="arn:aws:ec2:us-east-1:123456789:volume/vol-12345",
                resource_type="AWS::EC2::Volume",
                provider=CloudProvider.AWS,
                region=self.region,
                tags={"Environment": "production"},
                compliance_state="NON_COMPLIANT",
                metadata={"reason": "Volume not encrypted"},
            ),
            CloudResource(
                resource_id="arn:aws:iam::123456789:user/developer",
                resource_type="AWS::IAM::User",
                provider=CloudProvider.AWS,
                region="global",
                tags={},
                compliance_state="NON_COMPLIANT",
                metadata={"reason": "MFA not enabled"},
            ),
        ]


class AzurePolicyIntegration(CloudIntegration):
    """Integration with Azure Policy for compliance monitoring."""

    POLICY_DEFINITIONS = {
        "storage-encryption": {
            "severity": "HIGH",
            "description": "Storage accounts should use encryption",
            "frameworks": ["SOC2", "HIPAA"],
        },
        "sql-encryption": {
            "severity": "HIGH",
            "description": "SQL databases should have transparent data encryption",
            "frameworks": ["SOC2", "PCI-DSS", "HIPAA"],
        },
        "nsg-flow-logs": {
            "severity": "MEDIUM",
            "description": "Network security groups should have flow logs",
            "frameworks": ["SOC2"],
        },
        "keyvault-soft-delete": {
            "severity": "MEDIUM",
            "description": "Key Vaults should have soft delete enabled",
            "frameworks": ["SOC2", "PCI-DSS"],
        },
    }

    def __init__(self, subscription_id: str = "default"):
        super().__init__(CloudProvider.AZURE)
        self.subscription_id = subscription_id

    def list_resources(self, resource_type: str | None = None) -> list[CloudResource]:
        """List Azure resources."""
        resources = self._get_sample_resources()
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        return resources

    def evaluate_rules(self, resources: list[CloudResource]) -> list[ComplianceRuleResult]:
        """Evaluate Azure Policy definitions against resources."""
        results: list[ComplianceRuleResult] = []

        for policy_id, policy_meta in self.POLICY_DEFINITIONS.items():
            for resource in resources:
                compliant = resource.compliance_state == "COMPLIANT"
                results.append(ComplianceRuleResult(
                    rule_id=policy_id,
                    rule_name=policy_meta["description"],
                    resource_id=resource.resource_id,
                    compliant=compliant,
                    severity=policy_meta["severity"],
                    description=policy_meta["description"],
                    evidence=f"Azure resource compliance: {resource.compliance_state}",
                ))

        return results

    def get_compliance_summary(self) -> dict[str, Any]:
        """Get Azure Policy compliance summary."""
        resources = self.list_resources()
        rule_results = self.evaluate_rules(resources)

        compliant = sum(1 for r in rule_results if r.compliant)
        non_compliant = sum(1 for r in rule_results if not r.compliant)

        return {
            "provider": "Azure",
            "subscription_id": self.subscription_id,
            "total_resources": len(resources),
            "total_rules_evaluated": len(rule_results),
            "compliant": compliant,
            "non_compliant": non_compliant,
            "compliance_percentage": round(
                (compliant / len(rule_results) * 100) if rule_results else 100, 2
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_sample_resources(self) -> list[CloudResource]:
        """Return sample Azure resources."""
        return [
            CloudResource(
                resource_id=f"/subscriptions/{self.subscription_id}/resourceGroups/prod/providers/Microsoft.Storage/storageAccounts/myappstorage",
                resource_type="Microsoft.Storage/storageAccounts",
                provider=CloudProvider.AZURE,
                region="eastus",
                tags={"Environment": "production"},
                compliance_state="COMPLIANT",
            ),
            CloudResource(
                resource_id=f"/subscriptions/{self.subscription_id}/resourceGroups/prod/providers/Microsoft.Sql/servers/myapp-db",
                resource_type="Microsoft.Sql/servers",
                provider=CloudProvider.AZURE,
                region="eastus",
                tags={"Environment": "production"},
                compliance_state="COMPLIANT",
            ),
            CloudResource(
                resource_id=f"/subscriptions/{self.subscription_id}/resourceGroups/prod/providers/Microsoft.Network/networkSecurityGroups/myapp-nsg",
                resource_type="Microsoft.Network/networkSecurityGroups",
                provider=CloudProvider.AZURE,
                region="eastus",
                tags={},
                compliance_state="NON_COMPLIANT",
                metadata={"reason": "Flow logs not enabled"},
            ),
        ]


class GCPComplianceIntegration(CloudIntegration):
    """Integration with GCP Security Command Center for compliance monitoring."""

    def __init__(self, project_id: str = "my-project"):
        super().__init__(CloudProvider.GCP)
        self.project_id = project_id

    def list_resources(self, resource_type: str | None = None) -> list[CloudResource]:
        resources = self._get_sample_resources()
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        return resources

    def evaluate_rules(self, resources: list[CloudResource]) -> list[ComplianceRuleResult]:
        results = []
        for resource in resources:
            compliant = resource.compliance_state == "COMPLIANT"
            results.append(ComplianceRuleResult(
                rule_id=f"gcp-{resource.resource_type.lower()}",
                rule_name=f"GCP {resource.resource_type} compliance check",
                resource_id=resource.resource_id,
                compliant=compliant,
                severity="HIGH" if not compliant else "INFO",
                description=f"Compliance evaluation for {resource.resource_id}",
                evidence=f"State: {resource.compliance_state}",
            ))
        return results

    def get_compliance_summary(self) -> dict[str, Any]:
        resources = self.list_resources()
        rule_results = self.evaluate_rules(resources)
        compliant = sum(1 for r in rule_results if r.compliant)
        return {
            "provider": "GCP",
            "project_id": self.project_id,
            "total_resources": len(resources),
            "total_rules_evaluated": len(rule_results),
            "compliant": compliant,
            "non_compliant": sum(1 for r in rule_results if not r.compliant),
            "compliance_percentage": round(
                (compliant / len(rule_results) * 100) if rule_results else 100, 2
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_sample_resources(self) -> list[CloudResource]:
        return [
            CloudResource(
                resource_id=f"projects/{self.project_id}/buckets/my-app-data",
                resource_type="GCS Bucket",
                provider=CloudProvider.GCP,
                region="us-central1",
                tags={"environment": "production"},
                compliance_state="COMPLIANT",
            ),
            CloudResource(
                resource_id=f"projects/{self.project_id}/instances/my-app-vm",
                resource_type="Compute Instance",
                provider=CloudProvider.GCP,
                region="us-central1",
                tags={"environment": "production"},
                compliance_state="COMPLIANT",
            ),
        ]


def get_cloud_integration(
    provider: CloudProvider,
    **kwargs: Any,
) -> CloudIntegration:
    """Factory function to create cloud integrations."""
    integrations = {
        CloudProvider.AWS: AWSConfigIntegration,
        CloudProvider.AZURE: AzurePolicyIntegration,
        CloudProvider.GCP: GCPComplianceIntegration,
    }
    cls = integrations.get(provider)
    if not cls:
        raise ValueError(f"Unsupported cloud provider: {provider}")
    return cls(**kwargs)
