"""Kubernetes operator for ContextVault — horizontal scaling and management."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ScalingPolicy:
    """Policy for auto-scaling ContextVault replicas."""
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    scale_up_cooldown: int = 60  # seconds
    scale_down_cooldown: int = 300  # seconds


@dataclass
class ResourceConfig:
    """Resource configuration for ContextVault pods."""
    cpu_request: str = "250m"
    cpu_limit: str = "1000m"
    memory_request: str = "512Mi"
    memory_limit: str = "2Gi"
    storage_size: str = "10Gi"
    storage_class: str = "standard"


@dataclass
class ContextVaultSpec:
    """Specification for a ContextVault deployment."""
    name: str
    namespace: str = "contextvault"
    replicas: int = 3
    image: str = "contextvault:latest"
    image_pull_policy: str = "IfNotPresent"
    service_type: str = "ClusterIP"
    service_port: int = 8000
    grpc_port: int = 50051
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    scaling: ScalingPolicy = field(default_factory=ScalingPolicy)
    env: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=lambda: {
        "app": "contextvault",
        "component": "memory-store",
    })
    annotations: Dict[str, str] = field(default_factory=dict)
    node_selector: Dict[str, str] = field(default_factory=dict)
    tolerations: List[Dict[str, Any]] = field(default_factory=list)
    anti_affinity: bool = True


class KubernetesManifestGenerator:
    """Generate Kubernetes manifests for ContextVault."""

    def __init__(self, spec: ContextVaultSpec) -> None:
        self.spec = spec

    def generate_all(self) -> Dict[str, Any]:
        """Generate all Kubernetes manifests."""
        return {
            "namespace": self._namespace(),
            "deployment": self._deployment(),
            "service": self._service(),
            "service_account": self._service_account(),
            "configmap": self._configmap(),
            "hpa": self._hpa(),
            "pdb": self._pdb(),
            "network_policy": self._network_policy(),
        }

    def _namespace(self) -> Dict[str, Any]:
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": self.spec.namespace,
                "labels": {
                    "app.kubernetes.io/name": "contextvault",
                    "app.kubernetes.io/managed-by": "contextvault-operator",
                    **self.spec.labels,
                },
            },
        }

    def _deployment(self) -> Dict[str, Any]:
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": self.spec.name,
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
                "annotations": self.spec.annotations,
            },
            "spec": {
                "replicas": self.spec.replicas,
                "selector": {
                    "matchLabels": {
                        "app": self.spec.name,
                    },
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": self.spec.name,
                            **self.spec.labels,
                        },
                        "annotations": {
                            "prometheus.io/scrape": "true",
                            "prometheus.io/port": "8000",
                            "prometheus.io/path": "/metrics",
                            **self.spec.annotations,
                        },
                    },
                    "spec": {
                        "serviceAccountName": f"{self.spec.name}-sa",
                        "containers": [
                            {
                                "name": "contextvault",
                                "image": self.spec.image,
                                "imagePullPolicy": self.spec.image_pull_policy,
                                "ports": [
                                    {
                                        "name": "http",
                                        "containerPort": self.spec.service_port,
                                        "protocol": "TCP",
                                    },
                                    {
                                        "name": "grpc",
                                        "containerPort": self.spec.grpc_port,
                                        "protocol": "TCP",
                                    },
                                ],
                                "envFrom": [
                                    {"configMapRef": {"name": f"{self.spec.name}-config"}},
                                ],
                                "resources": {
                                    "requests": {
                                        "cpu": self.spec.resources.cpu_request,
                                        "memory": self.spec.resources.memory_request,
                                    },
                                    "limits": {
                                        "cpu": self.spec.resources.cpu_limit,
                                        "memory": self.spec.resources.memory_limit,
                                    },
                                },
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/api/v1/health",
                                        "port": "http",
                                    },
                                    "initialDelaySeconds": 10,
                                    "periodSeconds": 30,
                                    "timeoutSeconds": 5,
                                    "failureThreshold": 3,
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/api/v1/health",
                                        "port": "http",
                                    },
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 10,
                                    "timeoutSeconds": 3,
                                    "failureThreshold": 3,
                                },
                                "volumeMounts": [
                                    {
                                        "name": "data",
                                        "mountPath": "/data",
                                    },
                                ],
                            },
                        ],
                        "volumes": [
                            {
                                "name": "data",
                                "persistentVolumeClaim": {
                                    "claimName": f"{self.spec.name}-data",
                                },
                            },
                        ],
                        "nodeSelector": self.spec.node_selector or None,
                        "tolerations": self.spec.tolerations or None,
                    },
                },
            },
        }

    def _service(self) -> Dict[str, Any]:
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": self.spec.name,
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
            "spec": {
                "type": self.spec.service_type,
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "targetPort": self.spec.service_port,
                        "protocol": "TCP",
                    },
                    {
                        "name": "grpc",
                        "port": self.spec.grpc_port,
                        "targetPort": self.spec.grpc_port,
                        "protocol": "TCP",
                    },
                ],
                "selector": {
                    "app": self.spec.name,
                },
            },
        }

    def _service_account(self) -> Dict[str, Any]:
        return {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": f"{self.spec.name}-sa",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
        }

    def _configmap(self) -> Dict[str, Any]:
        env_vars = {
            "CONTEXTVAULT_LOG_LEVEL": "info",
            "CONTEXTVAULT_PERSIST_PATH": "/data",
            "CONTEXTVAULT_HTTP_PORT": str(self.spec.service_port),
            "CONTEXTVAULT_GRPC_PORT": str(self.spec.grpc_port),
            "CONTEXTVAULT_DIMENSION": "128",
            "CONTEXTVAULT_INDEX_TYPE": "flat",
            **self.spec.env,
        }
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{self.spec.name}-config",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
            "data": env_vars,
        }

    def _hpa(self) -> Dict[str, Any]:
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{self.spec.name}-hpa",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": self.spec.name,
                },
                "minReplicas": self.spec.scaling.min_replicas,
                "maxReplicas": self.spec.scaling.max_replicas,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": int(self.spec.scaling.target_cpu_utilization),
                            },
                        },
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": int(self.spec.scaling.target_memory_utilization),
                            },
                        },
                    },
                ],
                "behavior": {
                    "scaleUp": {
                        "stabilizationWindowSeconds": self.spec.scaling.scale_up_cooldown,
                    },
                    "scaleDown": {
                        "stabilizationWindowSeconds": self.spec.scaling.scale_down_cooldown,
                    },
                },
            },
        }

    def _pdb(self) -> Dict[str, Any]:
        return {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": {
                "name": f"{self.spec.name}-pdb",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
            "spec": {
                "minAvailable": max(1, self.spec.replicas - 1),
                "selector": {
                    "matchLabels": {
                        "app": self.spec.name,
                    },
                },
            },
        }

    def _network_policy(self) -> Dict[str, Any]:
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": f"{self.spec.name}-netpol",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
            "spec": {
                "podSelector": {
                    "matchLabels": {
                        "app": self.spec.name,
                    },
                },
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [
                    {
                        "from": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {
                                        "name": self.spec.namespace,
                                    },
                                },
                            },
                        ],
                        "ports": [
                            {"protocol": "TCP", "port": self.spec.service_port},
                            {"protocol": "TCP", "port": self.spec.grpc_port},
                        ],
                    },
                ],
                "egress": [
                    {
                        "to": [
                            {
                                "namespaceSelector": {},
                            },
                        ],
                    },
                ],
            },
        }

    def generate_pvc(self) -> Dict[str, Any]:
        """Generate PersistentVolumeClaim for data storage."""
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{self.spec.name}-data",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": self.spec.resources.storage_class,
                "resources": {
                    "requests": {
                        "storage": self.spec.resources.storage_size,
                    },
                },
            },
        }

    def generate_ingress(self, host: str = "contextvault.local") -> Dict[str, Any]:
        """Generate Ingress resource."""
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{self.spec.name}-ingress",
                "namespace": self.spec.namespace,
                "labels": self.spec.labels,
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                },
            },
            "spec": {
                "rules": [
                    {
                        "host": host,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": self.spec.name,
                                            "port": {
                                                "number": 80,
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        }

    def write_manifests(self, output_dir: str) -> List[str]:
        """Write all manifests to files. Returns list of file paths."""
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        manifests = self.generate_all()
        written = []

        for name, manifest in manifests.items():
            if manifest is None:
                continue
            file_path = output / f"{name}.yaml"
            with open(file_path, "w") as f:
                yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
            written.append(str(file_path))

        # Also write PVC and Ingress
        pvc = self.generate_pvc()
        pvc_path = output / "pvc.yaml"
        with open(pvc_path, "w") as f:
            yaml.dump(pvc, f, default_flow_style=False, sort_keys=False)
        written.append(str(pvc_path))

        ingress = self.generate_ingress()
        ingress_path = output / "ingress.yaml"
        with open(ingress_path, "w") as f:
            yaml.dump(ingress, f, default_flow_style=False, sort_keys=False)
        written.append(str(ingress_path))

        return written


class ContextVaultOperator:
    """Operator for managing ContextVault deployments on Kubernetes."""

    def __init__(self, kubeconfig: Optional[str] = None) -> None:
        self.kubeconfig = kubeconfig
        self._deployments: Dict[str, ContextVaultSpec] = {}

    def create_deployment(self, spec: ContextVaultSpec) -> ContextVaultSpec:
        """Register a new ContextVault deployment."""
        if spec.name in self._deployments:
            raise ValueError(f"Deployment {spec.name} already exists")
        self._deployments[spec.name] = spec
        logger.info("Created deployment spec: %s/%s", spec.namespace, spec.name)
        return spec

    def get_deployment(self, name: str) -> Optional[ContextVaultSpec]:
        """Get a deployment spec by name."""
        return self._deployments.get(name)

    def list_deployments(self) -> List[ContextVaultSpec]:
        """List all registered deployments."""
        return list(self._deployments.values())

    def update_replicas(self, name: str, replicas: int) -> Optional[ContextVaultSpec]:
        """Update the replica count for a deployment."""
        spec = self._deployments.get(name)
        if spec is None:
            return None
        spec.replicas = max(spec.scaling.min_replicas, min(spec.scaling.max_replicas, replicas))
        logger.info("Updated %s replicas to %d", name, spec.replicas)
        return spec

    def scale_up(self, name: str) -> Optional[ContextVaultSpec]:
        """Scale up a deployment by one replica."""
        spec = self._deployments.get(name)
        if spec is None:
            return None
        return self.update_replicas(name, spec.replicas + 1)

    def scale_down(self, name: str) -> Optional[ContextVaultSpec]:
        """Scale down a deployment by one replica."""
        spec = self._deployments.get(name)
        if spec is None:
            return None
        return self.update_replicas(name, spec.replicas - 1)

    def delete_deployment(self, name: str) -> bool:
        """Remove a deployment spec."""
        if name in self._deployments:
            del self._deployments[name]
            logger.info("Deleted deployment: %s", name)
            return True
        return False

    def generate_manifests(self, name: str, output_dir: str) -> List[str]:
        """Generate Kubernetes manifests for a deployment."""
        spec = self._deployments.get(name)
        if spec is None:
            raise ValueError(f"Deployment {name} not found")
        generator = KubernetesManifestGenerator(spec)
        return generator.write_manifests(output_dir)

    def get_status(self, name: str) -> Dict[str, Any]:
        """Get deployment status summary."""
        spec = self._deployments.get(name)
        if spec is None:
            return {"error": "Deployment not found"}
        return {
            "name": spec.name,
            "namespace": spec.namespace,
            "replicas": spec.replicas,
            "image": spec.image,
            "scaling": {
                "min": spec.scaling.min_replicas,
                "max": spec.scaling.max_replicas,
            },
            "resources": {
                "cpu": f"{spec.resources.cpu_request}/{spec.resources.cpu_limit}",
                "memory": f"{spec.resources.memory_request}/{spec.resources.memory_limit}",
            },
        }


def generate_default_manifests(output_dir: str = "k8s") -> List[str]:
    """Generate default Kubernetes manifests."""
    spec = ContextVaultSpec(
        name="contextvault",
        namespace="contextvault",
        replicas=3,
        image="contextvault:1.0.0",
    )
    generator = KubernetesManifestGenerator(spec)
    return generator.write_manifests(output_dir)


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "k8s"
    files = generate_default_manifests(output)
    print(f"Generated {len(files)} manifests:")
    for f in files:
        print(f"  - {f}")
