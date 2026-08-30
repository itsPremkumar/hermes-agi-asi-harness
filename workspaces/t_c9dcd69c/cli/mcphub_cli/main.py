"""MCPHub CLI tool for server installation and management."""
import json
import os
import sys
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
API_BASE = os.getenv("MCPHUB_API_URL", "http://localhost:8000/api/v1")


@click.group()
@click.version_option(version="1.0.0", prog_name="mcphub")
def cli():
    """MCPHub CLI — Discover, install, and manage MCP servers."""
    pass


@cli.command()
@click.argument("query", required=False)
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--transport", "-t", default=None, help="Filter by transport type")
@click.option("--sort", "-s", default="relevance", type=click.Choice(["relevance", "stars", "downloads", "newest", "health"]))
@click.option("--limit", "-l", default=20, help="Number of results")
def search(query, category, transport, sort, limit):
    """Search MCP servers in the registry."""
    params = {"q": query, "sort": sort, "per_page": limit}
    if category:
        params["category"] = category
    if transport:
        params["transport"] = transport

    try:
        resp = httpx.get(f"{API_BASE}/search", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not data["results"]:
        console.print("[yellow]No servers found.[/yellow]")
        return

    table = Table(title=f"MCPHub Search Results ({data['total']} total)")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white", max_width=50)
    table.add_column("Author", style="green")
    table.add_column("Stars", style="yellow", justify="right")
    table.add_column("Downloads", style="magenta", justify="right")
    table.add_column("Transport", style="blue")

    for s in data["results"]:
        table.add_row(
            s["name"],
            (s["description"] or "")[:60],
            s["author"],
            str(s["github_stars"]),
            str(s["downloads"]),
            s["mcp_transport"],
        )

    console.print(table)


@cli.command()
@click.argument("name")
@click.option("--output", "-o", default=None, help="Output path for config")
def install(name, output):
    """Install an MCP server by name or slug."""
    try:
        resp = httpx.get(f"{API_BASE}/servers/slug/{name}", timeout=10)
        if resp.status_code == 404:
            # Try searching
            search_resp = httpx.get(f"{API_BASE}/search", params={"q": name, "per_page": 1}, timeout=10)
            search_data = search_resp.json()
            if search_data["results"]:
                server = search_data["results"][0]
            else:
                console.print(f"[red]Server '{name}' not found.[/red]")
                sys.exit(1)
        else:
            resp.raise_for_status()
            server = resp.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Track download
    httpx.post(f"{API_BASE}/servers/{server['id']}/download", timeout=5)

    config = {
        "mcpServers": {
            server["slug"]: {
                "command": server.get("install_command", "npx"),
                "args": ["-y", server["name"]],
            }
        }
    }

    if output:
        with open(output, "w") as f:
            json.dump(config, f, indent=2)
        console.print(f"[green]Configuration written to {output}[/green]")
    else:
        console.print_json(json.dumps(config, indent=2))

    console.print(f"[green]✓ Installed {server['name']} v{server['version']}[/green]")


@cli.command()
@click.argument("server_id")
def info(server_id):
    """Show detailed information about a server."""
    try:
        resp = httpx.get(f"{API_BASE}/servers/{server_id}", timeout=10)
        resp.raise_for_status()
        server = resp.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    console.print(f"[bold cyan]{server['name']}[/bold cyan] v{server['version']}")
    console.print(f"[dim]ID:[/dim] {server['id']}")
    console.print(f"[dim]Slug:[/dim] {server['slug']}")
    console.print(f"[dim]Author:[/dim] {server['author']}")
    console.print(f"[dim]License:[/dim] {server['license']}")
    console.print(f"[dim]Status:[/dim] {server['status']}")
    console.print(f"[dim]Transport:[/dim] {server['mcp_transport']}")
    console.print(f"[dim]Category:[/dim] {server['category'] or 'uncategorized'}")
    console.print(f"[dim]Tags:[/dim] {', '.join(server['tags'])}")
    console.print(f"[dim]Stars:[/dim] {server['github_stars']}")
    console.print(f"[dim]Downloads:[/dim] {server['downloads']}")
    console.print(f"[dim]Health:[/dim] {server['health_score']}%")
    console.print(f"[dim]Repository:[/dim] {server.get('repository_url', 'N/A')}")
    console.print(f"[dim]Homepage:[/dim] {server.get('homepage_url', 'N/A')}")
    if server.get("description"):
        console.print(f"\n[white]{server['description']}[/white]")


@cli.command()
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--limit", "-l", default=20, help="Number of results")
def list(status, limit):
    """List approved MCP servers."""
    params = {"per_page": limit, "sort": "newest"}
    if status:
        params["status"] = status

    try:
        resp = httpx.get(f"{API_BASE}/servers", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not data["servers"]:
        console.print("[yellow]No servers found.[/yellow]")
        return

    table = Table(title=f"MCPHub Servers ({data['total']} total)")
    table.add_column("Name", style="cyan")
    table.add_column("Author", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Stars", style="magenta", justify="right")
    table.add_column("Status", style="blue")

    for s in data["servers"]:
        table.add_row(s["name"], s["author"], s["category"] or "-", str(s["github_stars"]), s["status"])

    console.print(table)


@cli.command()
@click.option("--server-id", "-s", required=True, help="Server ID")
@click.option("--status-code", "-c", default=None, type=int, help="HTTP status code")
@click.option("--response-time", "-r", default=0.0, type=float, help="Response time in ms")
@click.option("--is-up/--is-down", default=True, help="Whether server is up")
def healthcheck(server_id, status_code, response_time, is_up):
    """Record a health check for a server."""
    try:
        resp = httpx.post(
            f"{API_BASE}/health/{server_id}/check",
            params={"status_code": status_code, "response_time_ms": response_time, "is_up": is_up},
            timeout=10,
        )
        resp.raise_for_status()
        console.print(f"[green]✓ Health check recorded for {server_id}[/green]")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
def stats():
    """Show registry statistics."""
    try:
        resp = httpx.get(f"{API_BASE}/analytics", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    console.print(f"[bold cyan]MCPHub Registry Statistics[/bold cyan]")
    console.print(f"Total Servers: [green]{data['total_servers']}[/green]")
    console.print(f"Total Downloads: [green]{data['total_downloads']}[/green]")
    console.print(f"Total Views: [green]{data['total_views']}[/green]")

    if data.get("top_servers"):
        table = Table(title="Top Servers by Downloads")
        table.add_column("Name", style="cyan")
        table.add_column("Downloads", style="magenta", justify="right")
        for s in data["top_servers"]:
            table.add_row(s["name"], str(s["downloads"]))
        console.print(table)


@cli.command()
@click.argument("name")
@click.option("--description", "-d", default=None, help="Server description")
@click.option("--author", "-a", required=True, help="Author name")
@click.option("--repo", "-r", default=None, help="Repository URL")
def submit(name, description, author, repo):
    """Submit a new MCP server to the registry."""
    payload = {"name": name, "description": description, "author": author, "repository_url": repo}
    try:
        resp = httpx.post(f"{API_BASE}/submissions", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        console.print(f"[green]✓ Submission created (ID: {data['id']})[/green]")
        console.print(f"[dim]Status: {data['status']}[/dim]")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
