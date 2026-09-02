import agentos
print("version:", agentos.__version__)

from agentos.scheduler import Agent, Priority, Scheduler
s = Scheduler(max_concurrent=2)
a = Agent(id="a1", name="test", cpu_quota=1.0, memory_quota=256)
r = s.submit(a)
print("schedule result:", r.action)

from agentos.governor import ResourceGovernor, ResourceLimits
g = ResourceGovernor(ResourceLimits(max_cpu=2.0))
g.register_tenant("t1")
print("allocate cpu:", g.allocate_cpu("t1", 1.0))

from agentos.state import StateManager
st = StateManager()
st.set("k", "v")
print("state get:", st.get("k"))

from agentos.bus import Bus, Message
b = Bus()
msgs = []
b.subscribe("t", lambda m: msgs.append(m))
b.publish(Message(topic="t", payload="data"))
print("bus delivered:", len(msgs))

from agentos.observability import Observability
o = Observability()
with o.trace("op"):
    pass
print("spans:", len(o.tracer.get_spans()))

from agentos.tenancy import TenantManager
tm = TenantManager()
tm.create_tenant("t1", "Test")
print("tenants:", len(tm.list_tenants()))

from agentos.sandbox import Sandbox
sand = Sandbox()
result = sand.run(["echo", "hello"])
print("sandbox stdout:", result.stdout.strip())

from agentos.plugins import PluginManager, PluginManifest
pm = PluginManager()
pm.load_from_manifest(PluginManifest(name="p1", version="1.0.0"))
print("plugins:", len(pm.list_plugins()))

print("ALL OK")
