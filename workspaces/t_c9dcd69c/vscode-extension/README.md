"""VS Code extension README."""
# MCPHub for VS Code

Discover and install MCP servers from the MCPHub registry directly within VS Code.

## Features

- Search MCP servers from the command palette
- Install servers with one click
- Browse featured servers in the sidebar
- Submit your own servers

## Installation

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "MCPHub"
4. Click Install

## Usage

Open the Command Palette (Ctrl+Shift+P) and type:

- `MCPHub: Search Servers` — Search for MCP servers
- `MCPHub: Install Server` — Install a server by ID
- `MCPHub: Browse Registry` — Open the web registry
- `MCPHub: Submit Server` — Submit a new server

## Configuration

```json
{
  "mcphub.apiUrl": "http://localhost:8000/api/v1",
  "mcphub.autoInstall": false
}
```
