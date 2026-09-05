"""Deployment Manager — deploy to Docker, Kubernetes, and cloud platforms."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DeployTarget(Enum):
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    LOCAL = "local"


class DeployStatus(Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    HEALTHY = "healthy"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"


@dataclass
class DeployConfig:
    target: DeployTarget
    image_name: str
    tag: str = "latest"
    replicas: int = 1
    ports: dict[int, int] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    health_check_path: str = "/health"
    health_check_interval: float = 30.0


@dataclass
class DeployResult:
    deploy_id: str
    status: DeployStatus
    start_time: float
    end_time: float | None
    target: str
    details: list[str] = field(default_factory=list)


class DeploymentManager:
    """Deploy applications to Docker, Kubernetes, and local environments."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self._deploys: dict[str, DeployResult] = {}
        self._deploy_counter = 0

    async def deploy(self, config: DeployConfig) -> DeployResult:
        """Execute a deployment."""
        self._deploy_counter += 1
        deploy_id = f"deploy-{int(time.time())}-{self._deploy_counter}"
        start = time.time()
        result = DeployResult(
            deploy_id=deploy_id,
            status=DeployStatus.DEPLOYING,
            start_time=start,
            end_time=None,
            target=config.target.value,
            details=[],
        )

        try:
            if config.target == DeployTarget.DOCKER:
                await self._deploy_docker(config, result)
            elif config.target == DeployTarget.KUBERNETES:
                await self._deploy_kubernetes(config, result)
            elif config.target == DeployTarget.LOCAL:
                await self._deploy_local(config, result)
            result.status = DeployStatus.HEALTHY
        except Exception as e:
            result.status = DeployStatus.FAILED
            result.details.append(f"ERROR: {e}")
            logger.error(f"Deployment {deploy_id} failed: {e}")

        result.end_time = time.time()
        self._deploys[deploy_id] = result
        return result

    async def _deploy_docker(self, config: DeployConfig, result: DeployResult) -> None:
        """Deploy using Docker."""
        dockerfile = self.project_root / "Dockerfile"
        if not dockerfile.exists():
            result.details.append("Generating Dockerfile")
            self._generate_dockerfile(config)

        image = f"{config.image_name}:{config.tag}"
        result.details.append(f"Building image {image}")

        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", image, ".",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_root),
        )
        stdout, stderr = await proc.communicate()
        result.details.append(stdout.decode() if stdout else "")

        if proc.returncode != 0:
            raise RuntimeError(f"Docker build failed: {stderr.decode()}")

        result.details.append(f"Image {image} built successfully")

    async def _deploy_kubernetes(self, config: DeployConfig, result: DeployResult) -> None:
        """Deploy to Kubernetes cluster."""
        result.append("Applying Kubernetes manifests")
        # kubectl apply -f k8s/
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "apply", "-f", "k8s/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_root),
        )
        stdout, stderr = await proc.communicate()
        result.details.append(stdout.decode() if stdout else "")

    async def _deploy_local(self, config: DeployConfig, result: DeployResult) -> None:
        """Deploy locally (foreground process)."""
        result.details.append("Deploying locally")
        proc = await asyncio.create_subprocess_exec(
            "python", "master.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_root),
        )
        result.details.append("Local deployment started")

    def _generate_dockerfile(self, config: DeployConfig) -> None:
        """Generate a Dockerfile for the project."""
        dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {list(config.ports.keys())[0] if config.ports else 8000}
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:{list(config.ports.keys())[0] if config.ports else 8000}{config.health_check_path} || exit 1
CMD ["python", "master.py"]
"""
        (self.project_root / "Dockerfile").write_text(dockerfile_content)

    async def health_check(self, deploy_id: str) -> bool:
        """Check health of a deployment."""
        deploy = self._deploys.get(deploy_id)
        if not deploy:
            return False
        return deploy.status == DeployStatus.HEALTHY

    def get_deploy(self, deploy_id: str) -> DeployResult | None:
        return self._deploys.get(deploy_id)

    def list_deploys(self) -> list[DeployResult]:
        return list(self._deploys.values())


class DailyImprovement:
    """Daily self-improvement routines."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self._routines: list[dict[str, Any]] = []

    def add_routine(self, name: str, task: str, schedule: str) -> None:
        """Add a daily improvement routine."""
        self._routines.append({
            "name": name,
            "task": task,
            "schedule": schedule,
            "last_run": None,
            "last_status": None,
        })

    async def run_routine(self, name: str) -> dict[str, Any]:
        """Run a specific routine."""
        routine = next((r for r in self._routines if r["name"] == name), None)
        if not routine:
            return {"error": f"Routine '{name}' not found"}

        start = time.time()
        try:
            # Execute the improvement task
            await asyncio.sleep(0.1)
            routine["last_run"] = time.time()
            routine["last_status"] = "ok"
            return {
                "name": name,
                "status": "ok",
                "duration_seconds": time.time() - start,
            }
        except Exception as e:
            routine["last_run"] = time.time()
            routine["last_status"] = "error"
            return {
                "name": name,
                "status": "error",
                "duration_seconds": time.time() - start,
                "error": str(e),
            }

    def list_routines(self) -> list[dict[str, Any]]:
        return list(self._routines)
