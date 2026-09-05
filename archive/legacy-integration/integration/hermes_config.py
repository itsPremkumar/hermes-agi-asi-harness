"""
Hermes config integration — add this to your ~/.hermes/config.yaml

This registers the harnix MCP server and makes all harness tools available in Hermes.
"""

HERMES_CONFIG_ADDITION = """
# ── ASI Harness Integration ──────────────────────────────────────────
# Add this to your ~/.hermes/config.yaml

mcp_servers:
  harnix:
    command: python
    args: ["-m", "integration.mcp_server"]
    timeout: 120
    connect_timeout: 60

# Optional: Auto-load bridge on session start
hooks:
  on_session_start: python -m integration.hermes_bridge.boot
"""

if __name__ == "__main__":
    print(HERMES_CONFIG_ADDITION)
