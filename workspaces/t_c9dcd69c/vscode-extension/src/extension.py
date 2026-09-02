"""VS Code extension for MCPHub server discovery and installation."""
import vscode
from vscode import ExtensionContext, window, commands, workspace

EXTENSION_ID = "mcphub.mcphub-vscode"
API_BASE = "http://localhost:8000/api/v1"


def activate(context: ExtensionContext):
    """Activate the MCPHub extension."""
    print("MCPHub extension activated")

    # Register commands
    commands.registerCommand("mcphub.search", search_servers)
    commands.registerCommand("mcphub.install", install_server)
    commands.registerCommand("mcphub.browse", browse_servers)
    commands.registerCommand("mcphub.submit", submit_server)

    # Create tree view for server browser
    tree_provider = ServerTreeProvider()
    window.registerTreeDataProvider("mcphubServers", tree_provider)


def deactivate():
    """Deactivate the extension."""
    pass


async def search_servers():
    """Search MCP servers from VS Code command palette."""
    query = await window.showInputBox({
        prompt: "Search MCP servers",
        placeHolder: "Enter server name or description",
    })
    if not query:
        return

    try:
        import urllib.request
        import json
        url = f"{API_BASE}/search?q={urllib.parse.quote(query)}&per_page=20"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())

        if not data["results"]:
            window.showInformationMessage(f"No servers found for '{query}'")
            return

        items = [
            {
                "label": s["name"],
                "description": f"⭐{s['github_stars']} ⬇{s['downloads']}",
                "detail": s["description"] or "",
                "server": s,
            }
            for s in data["results"]
        ]

        selected = await window.showQuickPick(items, {
            placeHolder: f"Found {data['total']} servers",
        })
        if selected:
            await install_server_by_data(selected["server"])
    except Exception as e:
        window.showErrorMessage(f"Search failed: {e}")


async def install_server(server_id: str = None):
    """Install an MCP server by ID or search first."""
    if not server_id:
        server_id = await window.showInputBox({
            prompt: "Server ID or slug",
            placeHolder: "Enter server identifier",
        })
    if not server_id:
        return

    try:
        import urllib.request
        import json
        url = f"{API_BASE}/servers/{server_id}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            server = json.loads(resp.read())
        await install_server_by_data(server)
    except Exception as e:
        window.showErrorMessage(f"Failed to fetch server: {e}")


async def install_server_by_data(server: dict):
    """Install an MCP server from its data."""
    config = {
        "mcpServers": {
            server["slug"]: {
                "command": server.get("install_command", "npx").split()[0],
                "args": ["-y", server["name"]],
            }
        }
    }

    # Write to workspace settings or mcp.json
    config_path = workspace.root_path or "."
    mcp_json_path = f"{config_path}/.mcp.json"

    try:
        import os
        existing = {}
        if os.path.exists(mcp_json_path):
            with open(mcp_json_path) as f:
                existing = json.load(f)

        existing.setdefault("mcpServers", {})
        existing["mcpServers"][server["slug"]] = config["mcpServers"][server["slug"]]

        with open(mcp_json_path, "w") as f:
            json.dump(existing, f, indent=2)

        window.showInformationMessage(
            f"✓ Installed {server['name']} to .mcp.json"
        )
    except Exception as e:
        window.showErrorMessage(f"Failed to write config: {e}")


async def browse_servers():
    """Open the MCPHub server browser in VS Code."""
    vscode.env.openExternal(vscode.Uri.parse("https://mcphub.dev/servers"))


async def submit_server():
    """Submit a new MCP server to the registry."""
    name = await window.showInputBox({
        prompt: "Server name",
        placeHolder: "MyAwesomeServer",
    })
    if not name:
        return

    description = await window.showInputBox({
        prompt: "Description",
        placeHolder: "What does your server do?",
    })

    author = await window.showInputBox({
        prompt: "Author",
        placeHolder: "Your name",
    })
    if not author:
        return

    repo = await window.showInputBox({
        prompt: "Repository URL",
        placeHolder: "https://github.com/you/server",
    })

    try:
        import urllib.request
        import json
        payload = json.dumps({
            "name": name,
            "description": description,
            "author": author,
            "repository_url": repo,
        }).encode()
        req = urllib.request.Request(
            f"{API_BASE}/submissions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        window.showInformationMessage(
            f"✓ Submitted {name} (ID: {data['id']})"
        )
    except Exception as e:
        window.showErrorMessage(f"Submission failed: {e}")


class ServerTreeItem(vscode.TreeItem):
    """Tree item representing an MCP server."""
    def __init__(self, server: dict):
        super().__init__(server["name"], vscode.TreeItemCollapsibleState.NONE)
        self.description = f"⭐{server['github_stars']} ⬇{server['downloads']}"
        self.tooltip = server.get("description", "")
        self.command = {
            "command": "mcphub.install",
            "title": "Install Server",
            "arguments": [server["id"]],
        }


class ServerTreeProvider:
    """Tree data provider for MCPHub servers."""
    def get_children(self, element=None):
        if element is None:
            # Root: fetch featured servers
            return self._fetch_featured()
        return []

    def get_tree_item(self, element):
        return element

    def _fetch_featured(self):
        try:
            import urllib.request
            import json
            url = f"{API_BASE}/servers?sort=stars&per_page=10"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            return [ServerTreeItem(s) for s in data["servers"]]
        except Exception:
            return []
