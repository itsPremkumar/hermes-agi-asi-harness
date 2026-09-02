"""Tests for AgentOS multi-tenancy module."""

from __future__ import annotations

import pytest

from agentos.governor import ResourceLimits
from agentos.tenancy import Tenant, TenantManager


class TestTenant:
    def test_create_tenant(self) -> None:
        tenant = Tenant(id="t1", name="Test Tenant")
        assert tenant.id == "t1"
        assert tenant.name == "Test Tenant"
        assert tenant.active is True

    def test_tenant_with_limits(self) -> None:
        limits = ResourceLimits(max_cpu=2.0, max_memory=1024)
        tenant = Tenant(id="t1", name="Test", limits=limits)
        assert tenant.limits.max_cpu == 2.0


class TestTenantManager:
    def test_create_tenant(self) -> None:
        manager = TenantManager()
        tenant = manager.create_tenant("t1", "Test Tenant")
        assert tenant.id == "t1"
        assert tenant.name == "Test Tenant"

    def test_duplicate_tenant(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Test")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_tenant("t1", "Test 2")

    def test_get_tenant(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Test")
        tenant = manager.get_tenant("t1")
        assert tenant is not None
        assert tenant.name == "Test"

    def test_update_tenant(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Test")
        updated = manager.update_tenant("t1", name="Updated")
        assert updated.name == "Updated"

    def test_delete_tenant(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Test")
        assert manager.delete_tenant("t1") is True
        assert manager.get_tenant("t1") is None

    def test_list_tenants(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Tenant 1")
        manager.create_tenant("t2", "Tenant 2")
        assert len(manager.list_tenants()) == 2

    def test_list_active_tenants(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Active")
        manager.create_tenant("t2", "Inactive")
        manager.suspend_tenant("t2")
        active = manager.list_tenants(active_only=True)
        assert len(active) == 1
        assert active[0].id == "t1"

    def test_check_quota_cpu(self) -> None:
        manager = TenantManager()
        limits = ResourceLimits(max_cpu=2.0)
        manager.create_tenant("t1", "Test", limits=limits)
        assert manager.check_quota("t1", "cpu", 1.0) is True
        assert manager.check_quota("t1", "cpu", 3.0) is False

    def test_check_quota_memory(self) -> None:
        manager = TenantManager()
        limits = ResourceLimits(max_memory=1024)
        manager.create_tenant("t1", "Test", limits=limits)
        assert manager.check_quota("t1", "memory", 512) is True
        assert manager.check_quota("t1", "memory", 2048) is False

    def test_allocate_and_release_cpu(self) -> None:
        manager = TenantManager()
        limits = ResourceLimits(max_cpu=2.0)
        manager.create_tenant("t1", "Test", limits=limits)
        assert manager.allocate("t1", "cpu", 1.0) is True
        manager.release("t1", "cpu", 0.5)
        usage = manager.get_usage("t1")
        assert usage is not None
        assert usage.cpu == 0.5

    def test_suspend_tenant(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Test")
        assert manager.suspend_tenant("t1") is True
        tenant = manager.get_tenant("t1")
        assert tenant is not None
        assert tenant.active is False

    def test_activate_tenant(self) -> None:
        manager = TenantManager()
        manager.create_tenant("t1", "Test")
        manager.suspend_tenant("t1")
        assert manager.activate_tenant("t1") is True
        tenant = manager.get_tenant("t1")
        assert tenant is not None
        assert tenant.active is True

    def test_unknown_tenant_quota(self) -> None:
        manager = TenantManager()
        assert manager.check_quota("unknown", "cpu", 1.0) is False
