"""Seed data for MCPHub — generates 500+ MCP server entries."""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict

# Categories and tags for generating realistic data
CATEGORIES = [
    "developer-tools", "data", "productivity", "communication",
    "search", "ai-ml", "security", "database", "cloud", "media",
    "finance", "education", "health", "iot", "analytics",
]

TAGS = [
    "mcp", "ai", "llm", "tool", "api", "web", "database",
    "search", "nlp", "image", "audio", "video", "file",
    "automation", "monitoring", "testing", "deployment",
]

TRANSPORTS = ["stdio", "http", "sse"]

# Server name prefixes and suffixes for realistic generation
PREFIXES = [
    "Smart", "Fast", "Cloud", "Data", "AI", "Meta", "Hyper",
    "Neuro", "Quantum", "Ultra", "Pro", "Core", "Open", "Deep",
    "Vector", "Graph", "Flow", "Sync", "Async", "Stream",
    "Block", "Node", "Link", "Bridge", "Hub", "Mesh", "Grid",
    "Stack", "Frame", "Layer", "Base", "Peak", "Edge",
]

SUFFIXES = [
    "Engine", "Bot", "Hub", "Kit", "Lab", "Forge", "Studio",
    "Works", "Base", "Box", "Link", "Net", "Flow", "Mind",
    "Sense", "View", "Scan", "Parse", "Query", "Fetch",
    "Store", "Cache", "Queue", "Pipe", "Gate", "Proxy",
    "Agent", "Helper", "Runner", "Worker", "Manager",
]

TOOLS = [
    "search", "fetch", "analyze", "transform", "generate",
    "validate", "monitor", "deploy", "test", "debug",
    "encrypt", "compress", "parse", "format", "convert",
]


def generate_server(index: int) -> Dict:
    """Generate a single MCP server entry."""
    prefix = PREFIXES[index % len(PREFIXES)]
    suffix = SUFFIXES[(index // len(PREFIXES)) % len(SUFFIXES)]
    name = f"{prefix}{suffix}"

    # Make unique by adding number if needed
    if index > len(PREFIXES) * len(SUFFIXES):
        name = f"{name}-{index}"

    category = CATEGORIES[index % len(CATEGORIES)]
    tags = [TAGS[index % len(TAGS)], TAGS[(index + 3) % len(TAGS)]]
    transport = TRANSPORTS[index % len(TRANSPORTS)]

    stars = max(0, 1000 - (index * 2) + (index % 50))
    downloads = max(0, 5000 - (index * 10) + (index % 100))

    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "slug": name.lower().replace(" ", "-"),
        "description": f"A powerful MCP server for {category} with {tags[0]} capabilities.",
        "long_description": f"{name} is a comprehensive MCP server designed for {category} workflows. "
                           f"It provides {tags[0]} and {tags[1]} tools for AI agents.",
        "author": f"developer-{index}",
        "author_github": f"dev{index}",
        "repository_url": f"https://github.com/dev{index}/{name.lower()}",
        "homepage_url": f"https://{name.lower()}.example.com",
        "version": f"1.{index % 10}.{index % 100}",
        "license": "MIT",
        "status": "approved",
        "mcp_transport": transport,
        "install_command": f"npx -y @{name.lower()}/mcp" if transport != "stdio" else f"pip install {name.lower()}-mcp",
        "tags": tags,
        "category": category,
        "github_stars": stars,
        "github_forks": stars // 5,
        "downloads": downloads,
        "health_score": 100.0 - (index % 20),
        "is_discovered": index > 400,
        "is_featured": index < 20,
        "created_at": (datetime.utcnow() - timedelta(days=index)).isoformat(),
        "updated_at": (datetime.utcnow() - timedelta(days=index % 30)).isoformat(),
    }


def generate_seed_data(count: int = 520) -> List[Dict]:
    """Generate seed data for the specified number of servers."""
    return [generate_server(i) for i in range(count)]


if __name__ == "__main__":
    data = generate_seed_data(520)
    with open("data/seed_servers.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} server entries")
