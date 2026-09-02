"""Tests for plugin.py and approval.py modules."""

from __future__ import annotations

import sys
import os
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "..", "..")
sys.path.insert(0, SRC_DIR)

from evolution.plugin import (
    IdentityPlugin,
    NoopPlugin,
    PluginBase,
    PluginMetadata,
    PluginRegistry,
    plugin,
)
from evolution.approval import (
    ApprovalGate,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalStatus,
    check_approval_gate,
)

passed = 0
failed = 0
errors = []


def test(name):
    def decorator(fn):
        global passed, failed, errors
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception as e:
            failed += 1
            errors.append((name, traceback.format_exc()))
            print(f"  FAIL  {name}: {e}")
        return fn
    return decorator


print("=" * 60)
print("  HERMES-ASI-MASTER Phase 8: Plugin & Approval Tests")
print("=" * 60)

# =========================================================================
# plugin.py
# =========================================================================
print("\n--- plugin.py ---")


@test("PluginMetadata: create")
def _():
    m = PluginMetadata(name="test", version="1.0.0", description="test plugin")
    assert m.name == "test"
    assert m.version == "1.0.0"
    assert m.level == 1
    assert m.requires_approval is False


@test("PluginMetadata: level 10 requires approval")
def _():
    m = PluginMetadata(name="risky", version="1.0.0", description="risky", level=10)
    assert m.requires_approval is True


@test("PluginMetadata: to_dict / from_dict")
def _():
    m = PluginMetadata(name="test", version="1.0.0", description="d", level=5)
    d = m.to_dict()
    m2 = PluginMetadata.from_dict(d)
    assert m2.name == "test"
    assert m2.level == 5


@test("IdentityPlugin: run returns state")
def _():
    p = IdentityPlugin()
    state = {"a": 1, "b": 2}
    result = p.run(state)
    assert result == state


@test("IdentityPlugin: metadata")
def _():
    p = IdentityPlugin()
    assert p.name == "identity"
    assert p.level == 1
    assert p.requires_approval is False


@test("NoopPlugin: run returns state")
def _():
    p = NoopPlugin()
    state = {"x": 10}
    result = p.run(state)
    assert result == state


@test("PluginRegistry: register and get")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    assert "identity" in reg
    p = reg.get("identity")
    assert isinstance(p, IdentityPlugin)


@test("PluginRegistry: list_plugins")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    reg.register(NoopPlugin)
    plugins = reg.list_plugins()
    assert len(plugins) == 2
    names = {p.name for p in plugins}
    assert "identity" in names
    assert "noop" in names


@test("PluginRegistry: list_requires_approval")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    reg.register(NoopPlugin)
    approved = reg.list_requires_approval()
    assert len(approved) == 0


@test("PluginRegistry: unregister")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    assert reg.unregister("identity") is True
    assert "identity" not in reg
    assert reg.unregister("missing") is False


@test("PluginRegistry: clear")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    reg.register(NoopPlugin)
    reg.clear()
    assert len(reg) == 0


@test("PluginRegistry: len and contains")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    assert len(reg) == 1
    assert "identity" in reg
    assert "missing" not in reg


@test("PluginRegistry: iterate")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    reg.register(NoopPlugin)
    names = list(reg)
    assert len(names) == 2


@test("PluginRegistry: get_class")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    cls = reg.get_class("identity")
    assert cls is IdentityPlugin


@test("PluginRegistry: register non-plugin raises")
def _():
    reg = PluginRegistry()
    try:
        reg.register(object)
        assert False, "Should have raised"
    except TypeError:
        pass


@test("PluginRegistry: list_plugins_by_level")
def _():
    reg = PluginRegistry()
    reg.register(IdentityPlugin)
    reg.register(NoopPlugin)
    level1 = reg.list_plugins_by_level(1)
    assert len(level1) == 2


@test("PluginBase: validate default")
def _():
    p = IdentityPlugin()
    ok, violations = p.validate({})
    assert ok is True
    assert violations == []


@test("PluginBase: to_dict")
def _():
    p = IdentityPlugin()
    d = p.to_dict()
    assert d["metadata"]["name"] == "identity"
    assert d["class"] == "IdentityPlugin"


@test("plugin decorator: registers metadata")
def _():
    @plugin(name="decorated", version="2.0.0", description="test", level=3)
    class DecoratedPlugin(PluginBase):
        def run(self, state):
            return state

    assert DecoratedPlugin.METADATA.name == "decorated"
    assert DecoratedPlugin.METADATA.version == "2.0.0"
    assert DecoratedPlugin.METADATA.level == 3


@test("plugin decorator: requires approval at level 10")
def _():
    @plugin(name="risky", version="1.0.0", description="risky", level=10)
    class RiskyPlugin(PluginBase):
        def run(self, state):
            return state

    assert RiskyPlugin.METADATA.requires_approval is True


# =========================================================================
# approval.py
# =========================================================================
print("\n--- approval.py ---")


@test("ApprovalRequest: create")
def _():
    r = ApprovalRequest(
        request_id="r1",
        plugin_name="test",
        description="test change",
        changes={"x": 1},
        risk_level=10,
    )
    assert r.request_id == "r1"
    assert r.status == ApprovalStatus.PENDING
    assert r.is_pending is True


@test("ApprovalRequest: approve")
def _():
    r = ApprovalRequest(
        request_id="r1",
        plugin_name="test",
        description="test",
        changes={},
        risk_level=10,
    )
    r.approve("operator")
    assert r.is_approved is True
    assert r.approved_by == "operator"


@test("ApprovalRequest: reject")
def _():
    r = ApprovalRequest(
        request_id="r1",
        plugin_name="test",
        description="test",
        changes={},
        risk_level=10,
    )
    r.reject("too risky")
    assert r.is_rejected is True
    assert r.rejection_reason == "too risky"


@test("ApprovalRequest: cancel")
def _():
    r = ApprovalRequest(
        request_id="r1",
        plugin_name="test",
        description="test",
        changes={},
        risk_level=10,
    )
    r.cancel()
    assert r.status == ApprovalStatus.CANCELLED


@test("ApprovalRequest: to_dict / from_dict")
def _():
    r = ApprovalRequest(
        request_id="r1",
        plugin_name="test",
        description="test",
        changes={"x": 1},
        risk_level=10,
    )
    d = r.to_dict()
    r2 = ApprovalRequest.from_dict(d)
    assert r2.request_id == "r1"
    assert r2.plugin_name == "test"
    assert r2.risk_level == 10


@test("ApprovalRecord: create")
def _():
    r = ApprovalRecord(
        request_id="r1",
        plugin_name="test",
        decision="approved",
        approver="operator",
    )
    assert r.decision == "approved"
    assert r.approver == "operator"


@test("ApprovalRecord: to_dict / from_dict")
def _():
    r = ApprovalRecord(
        request_id="r1",
        plugin_name="test",
        decision="rejected",
        approver="operator",
        reason="risky",
    )
    d = r.to_dict()
    r2 = ApprovalRecord.from_dict(d)
    assert r2.decision == "rejected"
    assert r2.reason == "risky"


@test("ApprovalGate: request_approval")
def _():
    gate = ApprovalGate()
    req = gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    assert req.status == ApprovalStatus.PENDING
    assert req.plugin_name == "test"


@test("ApprovalGate: approve")
def _():
    gate = ApprovalGate()
    req = gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    assert gate.approve(req.request_id, "operator") is True
    assert gate.is_approved(req.request_id) is True


@test("ApprovalGate: reject")
def _():
    gate = ApprovalGate()
    req = gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    assert gate.reject(req.request_id, "too risky") is True
    assert req.is_rejected is True


@test("ApprovalGate: cancel")
def _():
    gate = ApprovalGate()
    req = gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    assert gate.cancel(req.request_id) is True
    assert req.status == ApprovalStatus.CANCELLED


@test("ApprovalGate: list_pending")
def _():
    gate = ApprovalGate()
    gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    gate.request_approval("test2", "desc", {"y": 2}, risk_level=10)
    pending = gate.list_pending()
    assert len(pending) == 2


@test("ApprovalGate: list_all")
def _():
    gate = ApprovalGate()
    gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    all_reqs = gate.list_all()
    assert len(all_reqs) == 1


@test("ApprovalGate: list_records")
def _():
    gate = ApprovalGate()
    req = gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    gate.approve(req.request_id, "operator")
    records = gate.list_records()
    assert len(records) == 1
    assert records[0].decision == ApprovalStatus.APPROVED


@test("ApprovalGate: requires_approval")
def _():
    gate = ApprovalGate()
    assert gate.requires_approval(10) is True
    assert gate.requires_approval(9) is False
    assert gate.requires_approval(1) is False


@test("ApprovalGate: get_request")
def _():
    gate = ApprovalGate()
    req = gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    fetched = gate.get_request(req.request_id)
    assert fetched is not None
    assert fetched.request_id == req.request_id


@test("ApprovalGate: clear")
def _():
    gate = ApprovalGate()
    gate.request_approval("test", "desc", {"x": 1}, risk_level=10)
    gate.clear()
    assert len(gate) == 0


@test("ApprovalGate: approve nonexistent returns False")
def _():
    gate = ApprovalGate()
    assert gate.approve("nonexistent", "operator") is False


@test("ApprovalGate: reject nonexistent returns False")
def _():
    gate = ApprovalGate()
    assert gate.reject("nonexistent", "reason") is False


@test("ApprovalGate: is_approved nonexistent returns False")
def _():
    gate = ApprovalGate()
    assert gate.is_approved("nonexistent") is False


@test("check_approval_gate: level < 10 passes")
def _():
    ok, reason = check_approval_gate(5)
    assert ok is True
    assert "no approval" in reason


@test("check_approval_gate: level 10 without approver blocked")
def _():
    ok, reason = check_approval_gate(10)
    assert ok is False
    assert "requires human approval" in reason


@test("check_approval_gate: level 10 with approver passes")
def _():
    ok, reason = check_approval_gate(10, approver="operator")
    assert ok is True
    assert "approved by operator" in reason


# =========================================================================
# Summary
# =========================================================================
print("\n" + "=" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\n--- FAILURES ---")
    for name, tb in errors:
        print(f"\n{name}:")
        print(tb)
print("=" * 60)

sys.exit(1 if failed else 0)
