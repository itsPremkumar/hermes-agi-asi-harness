"""CLI for ContextVault — manage memory store from the terminal."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from contextvault.access_control import AccessController
from contextvault.consolidation import ConsolidationPipeline
from contextvault.memory_store import MemoryStore
from contextvault.models import MemoryMetadata, MemoryTier, MemoryType, AccessLevel
from contextvault.relevance import RelevanceScorer
from contextvault.search import MemorySearch
from contextvault.ttl import ColdStorage, TTLManager
from contextvault.vector_store import VectorStore

console = Console()
logger = logging.getLogger(__name__)


def _make_store(persist_path: Optional[str] = None) -> MemoryStore:
    """Create a MemoryStore with default configuration."""
    store = MemoryStore(persist_path=persist_path, dimension=128)
    return store


@click.group()
@click.option("--persist", "-p", default=None, help="Path to persist store data.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
@click.pass_context
def main(ctx: click.Context, persist: Optional[str], verbose: bool) -> None:
    """ContextVault — Agent Long-Term Memory Store."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["store"] = _make_store(persist)
    ctx.obj["persist"] = persist


@main.command()
@click.argument("content")
@click.option("--type", "memory_type", default="fact", help="Memory type.")
@click.option("--tier", default="semantic", help="Memory tier.")
@click.option("--agent", default="default", help="Agent ID.")
@click.option("--tag", multiple=True, help="Tags for the memory.")
@click.option("--importance", default=0.5, type=float, help="Importance (0-1).")
@click.option("--ttl", default=None, type=float, help="TTL in seconds.")
@click.pass_context
def store(
    ctx: click.Context,
    content: str,
    memory_type: str,
    tier: str,
    agent: str,
    tag: tuple,
    importance: float,
    ttl: Optional[float],
) -> None:
    """Store a new memory."""
    ms = ctx.obj["store"]
    from contextvault.models import MemoryMetadata

    metadata = MemoryMetadata(
        agent_id=agent,
        importance=importance,
        tags=list(tag),
    )
    mem = ms.store(
        content=content,
        memory_type=MemoryType(memory_type),
        tier=MemoryTier(tier),
        metadata=metadata,
        ttl=ttl,
    )
    console.print(f"[green]Stored memory:[/green] {mem.id}")
    console.print(f"  Type: {mem.memory_type.value}")
    console.print(f"  Tier: {mem.tier.value}")
    console.print(f"  Tags: {', '.join(mem.metadata.tags) if mem.metadata.tags else 'none'}")


@main.command()
@click.argument("query")
@click.option("--top-k", "-k", default=10, help="Number of results.")
@click.option("--tier", default=None, help="Filter by tier.")
@click.option("--type", "memory_type", default=None, help="Filter by type.")
@click.option("--agent", default=None, help="Agent ID for access control.")
@click.option("--min-score", default=0.0, type=float, help="Minimum score threshold.")
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    top_k: int,
    tier: Optional[str],
    memory_type: Optional[str],
    agent: Optional[str],
    min_score: float,
) -> None:
    """Search memories."""
    ms = ctx.obj["store"]
    tier_enum = MemoryTier(tier) if tier else None
    type_enum = MemoryType(memory_type) if memory_type else None

    results = ms.search(
        query=query,
        top_k=top_k,
        tier=tier_enum,
        memory_type=type_enum,
        agent_id=agent,
        min_score=min_score,
    )

    if not results:
        console.print("[yellow]No memories found.[/yellow]")
        return

    table = Table(title=f"Search Results for: {query}")
    table.add_column("ID", style="cyan")
    table.add_column("Content", style="white")
    table.add_column("Tier", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("Importance", style="yellow")

    for r in results:
        table.add_row(
            r["id"][:8] + "...",
            r["content"][:60] + ("..." if len(r["content"]) > 60 else ""),
            r["tier"],
            f"{r['score']:.3f}",
            f"{r['importance']:.2f}",
        )

    console.print(table)


@main.command()
@click.argument("memory_id")
@click.pass_context
def recall(ctx: click.Context, memory_id: str) -> None:
    """Recall a memory by ID."""
    ms = ctx.obj["store"]
    mem = ms.recall(memory_id)
    if mem is None:
        console.print(f"[red]Memory {memory_id} not found.[/red]")
        sys.exit(1)

    console.print(f"[cyan]ID:[/cyan] {mem.id}")
    console.print(f"[cyan]Content:[/cyan] {mem.content}")
    console.print(f"[cyan]Type:[/cyan] {mem.memory_type.value}")
    console.print(f"[cyan]Tier:[/cyan] {mem.tier.value}")
    console.print(f"[cyan]Agent:[/cyan] {mem.metadata.agent_id}")
    console.print(f"[cyan]Importance:[/cyan] {mem.metadata.importance}")
    console.print(f"[cyan]Access Count:[/cyan] {mem.access_count}")
    console.print(f"[cyan]Tags:[/cyan] {', '.join(mem.metadata.tags) if mem.metadata.tags else 'none'}")


@main.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show store statistics."""
    ms = ctx.obj["store"]
    s = ms.get_stats()

    table = Table(title="ContextVault Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Stored", str(s["total_stored"]))
    table.add_row("Total Archived", str(s["total_archived"]))
    table.add_row("Total Consolidated", str(s["total_consolidated"]))
    table.add_row("Relations", str(s["relations"]))
    table.add_row("Vector Store Size", str(s["vector_store_size"]))

    for tier_name, count in s["tiers"].items():
        table.add_row(f"Tier: {tier_name}", str(count))

    console.print(table)


@main.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all memories."""
    ms = ctx.obj["store"]
    memories = ms.list_memories()

    if not memories:
        console.print("[yellow]No memories stored.[/yellow]")
        return

    table = Table(title="All Memories")
    table.add_column("ID", style="cyan")
    table.add_column("Content", style="white")
    table.add_column("Tier", style="magenta")
    table.add_column("Type", style="blue")
    table.add_column("Agent", style="green")

    for m in memories:
        table.add_row(
            m.id[:8] + "...",
            m.content[:50] + ("..." if len(m.content) > 50 else ""),
            m.tier.value,
            m.memory_type.value,
            m.metadata.agent_id,
        )

    console.print(table)


@main.command()
@click.argument("memory_id")
@click.option("--tier", required=True, help="Target tier for promotion.")
@click.pass_context
def promote(ctx: click.Context, memory_id: str, tier: str) -> None:
    """Promote a memory to a higher tier."""
    ms = ctx.obj["store"]
    result = ms.promote(memory_id, MemoryTier(tier))
    if result is None:
        console.print(f"[red]Memory {memory_id} not found.[/red]")
        sys.exit(1)
    console.print(f"[green]Promoted to {tier}:[/green] {result.id}")


@main.command()
@click.argument("memory_id")
@click.pass_context
def archive(ctx: click.Context, memory_id: str) -> None:
    """Archive a memory (soft delete)."""
    ms = ctx.obj["store"]
    if ms.archive(memory_id):
        console.print(f"[green]Archived:[/green] {memory_id}")
    else:
        console.print(f"[red]Memory {memory_id} not found or already archived.[/red]")
        sys.exit(1)


@main.command()
@click.option("--source-id", required=True, help="Source memory ID.")
@click.option("--target-id", required=True, help="Target memory ID.")
@click.option("--relation", default="related_to", help="Relation type.")
@click.option("--strength", default=0.5, type=float, help="Relation strength.")
@click.pass_context
def relate(
    ctx: click.Context,
    source_id: str,
    target_id: str,
    relation: str,
    strength: float,
) -> None:
    """Create a relationship between two memories."""
    ms = ctx.obj["store"]
    rel = ms.relate(source_id, target_id, relation, strength)
    if rel:
        console.print(f"[green]Created relation:[/green] {rel.id}")
    else:
        console.print("[red]One or both memories not found.[/red]")
        sys.exit(1)


@main.command()
@click.option("--agent-id", required=True, help="Agent ID.")
@click.option("--name", required=True, help="Agent name.")
@click.option("--description", default="", help="Agent description.")
@click.pass_context
def register_agent(
    ctx: click.Context,
    agent_id: str,
    name: str,
    description: str,
) -> None:
    """Register a new agent for access control."""
    ac = AccessController()
    profile = ac.register_agent(agent_id, name, description)
    console.print(f"[green]Registered agent:[/green] {profile.agent_id} ({profile.name})")


@main.command()
@click.pass_context
def self_test(ctx: click.Context) -> None:
    """Run self-test to verify ContextVault functionality."""
    console.print("[bold]ContextVault Self-Test[/bold]")
    console.print("=" * 40)

    # Test 1: Store memory
    ms = ctx.obj["store"]
    from contextvault.models import MemoryMetadata

    mem = ms.store(
        content="The capital of France is Paris",
        memory_type=MemoryType.FACT,
        tier=MemoryTier.SEMANTIC,
        metadata=MemoryMetadata(agent_id="test-agent", tags=["geography"]),
    )
    console.print("[green]✓[/green] Store memory")

    # Test 2: Recall memory
    recalled = ms.recall(mem.id)
    assert recalled is not None
    assert recalled.content == "The capital of France is Paris"
    console.print("[green]✓[/green] Recall memory")

    # Test 3: Search memory
    results = ms.search("capital France", top_k=5)
    assert len(results) > 0
    console.print("[green]✓[/green] Search memory")

    # Test 4: Promote memory
    promoted = ms.promote(mem.id, MemoryTier.PROCEDURAL)
    assert promoted is not None
    assert promoted.tier == MemoryTier.PROCEDURAL
    console.print("[green]✓[/green] Promote memory")

    # Test 5: Archive memory
    assert ms.archive(mem.id)
    console.print("[green]✓[/green] Archive memory")

    # Test 6: Relevance scoring
    scorer = RelevanceScorer()
    score = scorer.composite_relevance(mem)
    assert 0.0 <= score <= 1.0
    console.print("[green]✓[/green] Relevance scoring")

    # Test 7: Consolidation
    pipeline = ConsolidationPipeline()
    mems = [
        ms.store(f"Memory {i}", MemoryType.FACT, MemoryTier.WORKING)
        for i in range(3)
    ]
    consolidated = pipeline.consolidate(mems, MemoryTier.SEMANTIC, "merge")
    assert consolidated is not None
    console.print("[green]✓[/green] Consolidation")

    # Test 8: TTL
    ttl_mgr = TTLManager()
    ttl_mem = ms.store(
        "Temporary memory",
        MemoryType.BUFFER,
        MemoryTier.WORKING,
        ttl=1.0,
    )
    assert ttl_mgr.get_remaining_ttl(ttl_mem) is not None
    console.print("[green]✓[/green] TTL management")

    # Test 9: Access control
    ac = AccessController()
    ac.register_agent("agent-1", "Test Agent")
    ac.register_agent("agent-2", "Another Agent")
    shared_mem = ms.store(
        "Shared info",
        MemoryType.FACT,
        MemoryTier.SEMANTIC,
        metadata=MemoryMetadata(agent_id="agent-1", access_level=AccessLevel.SHARED),
    )
    ac.grant_access(shared_mem, "agent-2")
    assert ac.can_access(shared_mem, "agent-2")
    console.print("[green]✓[/green] Access control")

    # Test 10: Stats
    s = ms.get_stats()
    assert s["total_stored"] > 0
    console.print("[green]✓[/green] Statistics")

    console.print("=" * 40)
    console.print("[bold green]All 10 self-tests passed![/bold green]")


if __name__ == "__main__":
    main()
