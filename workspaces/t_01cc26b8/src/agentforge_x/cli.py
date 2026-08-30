"""AgentForge-X CLI — minimal entry point."""
import click
from rich.console import Console

console = Console()


@click.group()
def main():
    """AgentForge-X — Kernel + Evolution Engine."""
    pass


@main.command()
def verify():
    """Run conformance harness self-check."""
    from agentforge_x.contracts import assert_agent_state_keys, assert_jsonl_line
    import json
    
    # Self-check
    state = {"id": "self", "name": "agentforge-x", "status": "idle", "model": "gpt-4"}
    assert assert_agent_state_keys(state) == []
    
    event = {"ts": "2026-08-30T00:00:00Z", "task_id": "self", "event": "heartbeat"}
    line = json.dumps(event)
    assert assert_jsonl_line(line)
    
    console.print("[green]✓ Conformance harness self-check passed[/green]")


@main.command()
def version():
    """Show version."""
    console.print("AgentForge-X v1.0.0")
