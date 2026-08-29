"""Command-line interface for AgentOS."""

from __future__ import annotations

import json
import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.scheduler import Agent, Priority, Scheduler
from agentos.governor import ResourceGovernor, ResourceLimits
from agentos.state import StateManager
from agentos.bus import Bus, Message
from agentos.observability import Observability
from agentos.tenancy import TenantManager

console = Console()


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """AgentOS — Operating System for AI Agents."""
    pass


@main.command()
def status() -> None:
    """Show AgentOS status."""
    console.print(f"[bold green]AgentOS v{__version__}[/bold green]")
    console.print("Status: [bold]running[/bold]")
    console.print("Components:")
    console.print("  - Scheduler: ready")
    console.print("  - Governor: ready")
    console.print("  - State: ready")
    console.print("  - Bus: ready")
    console.print("  - Observability: ready")


@main.command()
@click.argument("name")
@click.option("--priority", type=click.Choice(["critical", "high", "normal", "low", "background"]),
              default="normal")
@click.option("--cpu", default=1.0, help="CPU cores")
@click.option("--memory", default=512, help="Memory in MB")
@click.option("--tenant", default="default", help="Tenant ID")
def submit(name: str, priority: str, cpu: float, memory: int,
           tenant: str) -> None:
    """Submit an agent for scheduling."""
    scheduler = Scheduler()
    agent = Agent(
        id=f"agent-{name}",
        name=name,
        priority=Priority[priority.upper()],
        cpu_quota=cpu,
        memory_quota=memory,
        tenant_id=tenant,
    )
    result = scheduler.submit(agent)
    console.print(f"Agent '{name}' submitted: [bold]{result.action}[/bold]")


@main.command()
def list_agents() -> None:
    """List all agents (demo)."""
    table = Table(title="Agents")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Priority")
    table.add_column("State")
    console.print(table)
    console.print("[dim]Use 'agentos scheduler run' to start the scheduler[/dim]")


@main.command()
@click.option("--max-concurrent", default=4, help="Max concurrent agents")
@click.option("--max-cpu", default=8.0, help="Max CPU cores")
@click.option("--max-memory", default=16384, help="Max memory MB")
def scheduler_run(max_concurrent: int, max_cpu: float,
                  max_memory: int) -> None:
    """Run the scheduler (demo mode)."""
    scheduler = Scheduler(
        max_concurrent=max_concurrent,
        max_cpu=max_cpu,
        max_memory=max_memory,
    )
    console.print(f"[bold]Scheduler started[/bold] (max_concurrent={max_concurrent})")
    console.print("Press Ctrl+C to stop")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("[bold red]Scheduler stopped[/bold red]")


@main.command()
@click.argument("key")
@click.argument("value")
@click.option("--tenant", default="default", help="Tenant ID")
def state_set(key: str, value: str, tenant: str) -> None:
    """Set a state value."""
    state = StateManager()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    state.set(key, parsed, tenant_id=tenant)
    console.print(f"Set [bold]{key}[/bold] = {value}")


@main.command()
@click.argument("key")
@click.option("--tenant", default="default", help="Tenant ID")
def state_get(key: str, tenant: str) -> None:
    """Get a state value."""
    state = StateManager()
    value = state.get(key, tenant_id=tenant)
    if value is None:
        console.print(f"[dim]Key '{key}' not found[/dim]")
    else:
        console.print(f"[bold]{key}[/bold] = {json.dumps(value, indent=2)}")


@main.command()
@click.argument("topic")
@click.argument("payload")
def publish(topic: str, payload: str) -> None:
    """Publish a message to the bus."""
    bus = Bus()
    msg = Message(topic=topic, payload=payload)
    bus.publish(msg)
    console.print(f"Published to [bold]{topic}[/bold]: {payload}")


@main.command()
def metrics() -> None:
    """Show metrics (demo)."""
    obs = Observability()
    console.print("[bold]Metrics[/bold]")
    console.print(json.dumps(obs.metrics.summary(), indent=2))


@main.command()
def self_test() -> None:
    """Run self-test with assertions."""
    console.print("[bold]Running AgentOS self-test...[/bold]")

    passed = 0
    failed = 0

    def assert_test(condition: bool, name: str) -> None:
        nonlocal passed, failed
        if condition:
            console.print(f"  [green]PASS[/green] {name}")
            passed += 1
        else:
            console.print(f"  [red]FAIL[/red] {name}")
            failed += 1

    # Scheduler tests
    scheduler = Scheduler(max_concurrent=2, max_cpu=4.0, max_memory=4096)
    a1 = Agent(id="a1", name="test1", priority=Priority.HIGH, cpu_quota=1.0, memory_quota=256)
    a2 = Agent(id="a2", name="test2", priority=Priority.NORMAL, cpu_quota=1.0, memory_quota=256)
    a3 = Agent(id="a3", name="test3", priority=Priority.LOW, cpu_quota=1.0, memory_quota=256)

    r1 = scheduler.submit(a1)
    assert_test(r1.action == "scheduled", "Schedule high-priority agent")

    r2 = scheduler.submit(a2)
    assert_test(r2.action == "scheduled", "Schedule normal-priority agent")

    r3 = scheduler.submit(a3)
    assert_test(r3.action == "queued", "Queue when at max concurrent")

    scheduler.complete("a1")
    assert_test(scheduler.running_count == 2, "Complete agent schedules next from queue")

    # Governor tests
    governor = ResourceGovernor(ResourceLimits(max_cpu=2.0, max_memory=1024))
    governor.register_tenant("t1")
    assert_test(governor.allocate_cpu("t1", 1.0), "Allocate CPU within limit")
    assert_test(not governor.allocate_cpu("t1", 2.0), "Reject CPU over limit")
    assert_test(governor.check_api_rate("t1"), "API rate check passes")

    # State tests
    state = StateManager()
    state.set("key1", {"data": 123}, tenant_id="t1")
    assert_test(state.get("key1", tenant_id="t1") == {"data": 123}, "State set/get")
    assert_test(state.delete("key1", tenant_id="t1"), "State delete")
    assert_test(state.get("key1", tenant_id="t1") is None, "Deleted key is None")

    # Bus tests
    bus = Bus()
    received = []
    bus.subscribe("test.topic", lambda m: received.append(m))
    bus.publish(Message(topic="test.topic", payload="hello"))
    assert_test(len(received) == 1, "Bus publish/subscribe")

    # Observability tests
    obs = Observability()
    with obs.trace("test_op"):
        pass
    assert_test(len(obs.tracer.get_spans()) == 1, "Trace span recorded")
    obs.metrics.counter("test_counter")
    assert_test(obs.metrics.get_counter("test_counter") == 1, "Counter metric")

    console.print(f"\n[bold]Results:[/bold] {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
