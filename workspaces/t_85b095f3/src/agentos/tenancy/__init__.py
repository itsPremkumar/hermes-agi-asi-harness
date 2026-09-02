"""Multi-tenancy with resource quotas."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from agentos.governor import ResourceGovernor, ResourceLimits, ResourceUsage


@dataclass
class Tenant:
    """Represents a tenant with quotas and metadata."""
    id: str
    name: str
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    created_at: float = 0.0

    def __post_init__(self) -> None:
        import time
        if self.created_at == 0.0:
            self.created_at = time.time()


class TenantManager:
    """Manages multi-tenancy with resource quotas."""

    def __init__(self, governor: ResourceGovernor | None = None) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._governor = governor or ResourceGovernor()
        self._lock = Lock()

    def create_tenant(self, tenant_id: str, name: str,
                      limits: ResourceLimits | None = None,
                      metadata: dict[str, Any] | None = None) -> Tenant:
        """Create a new tenant."""
        with self._lock:
            if tenant_id in self._tenants:
                raise ValueError(f"Tenant '{tenant_id}' already exists")

            tenant = Tenant(
                id=tenant_id,
                name=name,
                limits=limits or ResourceLimits(),
                metadata=metadata or {},
            )
            self._tenants[tenant_id] = tenant
            self._governor.register_tenant(tenant_id, tenant.limits)
            return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    def update_tenant(self, tenant_id: str, **kwargs: Any) -> Tenant:
        """Update tenant properties."""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                raise ValueError(f"Tenant '{tenant_id}' not found")

            for key, value in kwargs.items():
                if hasattr(tenant, key):
                    setattr(tenant, key, value)

            return tenant

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant."""
        with self._lock:
            if tenant_id not in self._tenants:
                return False
            del self._tenants[tenant_id]
            return True

    def list_tenants(self, active_only: bool = False) -> list[Tenant]:
        """List all tenants."""
        tenants = list(self._tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.active]
        return tenants

    def check_quota(self, tenant_id: str, resource: str,
                    requested: float) -> bool:
        """Check if a tenant has quota available for a resource."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None or not tenant.active:
            return False

        if resource == "cpu":
            return self._governor.check_cpu(tenant_id, requested)
        elif resource == "memory":
            return self._governor.check_memory(tenant_id, int(requested))
        elif resource == "api":
            return self._governor.check_api_rate(tenant_id)
        elif resource == "agents":
            usage = self._governor.get_usage(tenant_id)
            if usage is None:
                return False
            return usage.concurrent_agents < tenant.limits.max_concurrent_agents
        return False

    def allocate(self, tenant_id: str, resource: str,
                 amount: float) -> bool:
        """Allocate a resource to a tenant."""
        if resource == "cpu":
            return self._governor.allocate_cpu(tenant_id, amount)
        elif resource == "memory":
            return self._governor.allocate_memory(tenant_id, int(amount))
        elif resource == "api":
            return self._governor.record_api_request(tenant_id)
        return False

    def release(self, tenant_id: str, resource: str, amount: float) -> None:
        """Release a resource from a tenant."""
        if resource == "cpu":
            self._governor.release_cpu(tenant_id, amount)
        elif resource == "memory":
            self._governor.release_memory(tenant_id, int(amount))

    def get_usage(self, tenant_id: str) -> ResourceUsage | None:
        """Get resource usage for a tenant."""
        return self._governor.get_usage(tenant_id)

    def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend a tenant (deactivate)."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False
        tenant.active = False
        return True

    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False
        tenant.active = True
        return True
