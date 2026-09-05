# AgentEye app shell (read-only)

Entry points and app surface with zero importers: `__main__`, `api`,
`cli`, `cli_ux`, `mcp_server`, `spellcheck`. The research capacity itself
stays live in `src/agent_eye/` (core, backends, extractors) behind
`src/hermes_os/eagle_adapter.py`. If Eagle Eye's own MCP server is ever
preferred over our hub specs, restore `mcp_server.py` from here.
