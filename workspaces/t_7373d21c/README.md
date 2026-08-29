# MCPTest

**Automated MCP Server Testing Framework**

MCPTest is a comprehensive testing toolkit for Model Context Protocol servers. It provides conformance testing, fuzzing, benchmarking, security scanning, and compliance reporting.

## Features

- **Conformance Testing** — Validate MCP protocol compliance (init, tools, resources, prompts, error handling)
- **Fuzzing Engine** — Test server robustness with malformed inputs, type confusion, and boundary values
- **Performance Benchmarking** — Measure throughput, latency percentiles, and memory usage
- **Security Scanning** — OWASP Top 10 checks for injection, SSRF, misconfiguration, and more
- **Compliance Reports** — HTML, JSON, and Markdown reports with compliance scores
- **Badge Generation** — Shields.io-compatible SVG badges for README display
- **MCPHub Registry** — Publish results to the MCPHub registry

## Installation

```bash
pip install mcptest
```

Or from source:

```bash
git clone https://github.com/itsPremkumar/mcptest.git
cd mcptest
pip install -e ".[dev]"
```

## Quick Start

1. Create a config file:

```bash
mcptest init
```

2. Edit `mcptest.yaml` with your server details:

```yaml
target:
  name: my-mcp-server
  command: python
  args: ["-m", "my_mcp_server"]
  transport: stdio

thresholds:
  min_requests_per_second: 10.0
  max_avg_latency_ms: 500.0
  max_p99_latency_ms: 2000.0

output_dir: mcptest-report
report_formats: [html, json]
```

3. Run the full test suite:

```bash
mcptest run --config mcptest.yaml
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `mcptest run` | Run full test suite |
| `mcptest conformance` | Run only conformance tests |
| `mcptest fuzz` | Run only fuzzing tests |
| `mcptest benchmark` | Run only benchmark tests |
| `mcptest security` | Run only security scan |
| `mcptest validate` | Validate config file |
| `mcptest init` | Create sample config |

## Transport Support

- **stdio** — Connect via subprocess stdin/stdout
- **http** — Connect via HTTP POST
- **sse** — Connect via Server-Sent Events

## Configuration Reference

```yaml
target:
  name: string              # Server name
  command: string           # Command (stdio transport)
  args: [string]           # Command arguments
  env: {key: value}        # Environment variables
  url: string              # URL (HTTP/SSE transport)
  transport: stdio|http|sse

thresholds:
  min_requests_per_second: float
  max_avg_latency_ms: float
  max_p99_latency_ms: float
  max_memory_mb: float
  max_critical_findings: int
  max_high_findings: int
  min_conformance_pass_rate: float

output_dir: string
report_formats: [html, json, markdown]
fuzzing_iterations: int
benchmark_duration_seconds: int
benchmark_concurrency: int
security_scan_enabled: bool
compliance_badge_enabled: bool
verbose: bool
```

## Compliance Scoring

The overall compliance score (0-100%) is the average of all enabled suite scores:

| Score | Rating | Badge |
|-------|--------|-------|
| 90-100% | Excellent | Green |
| 80-89% | Great | Lime |
| 60-79% | Good | Amber |
| 40-59% | Fair | Orange |
| 0-39% | Poor | Red |

A score >= 80% qualifies for the compliance badge.

## Client Configuration

Add MCPTest to your MCP client config:

### Claude Desktop / VS Code

```json
{
  "mcpServers": {
    "mcptest": {
      "command": "mcptest",
      "args": ["run", "--config", "mcptest.yaml"]
    }
  }
}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=mcptest --cov-report=html

# Lint
ruff check src/ tests/
mypy src/mcptest/
```

## License

MIT License — see [LICENSE](LICENSE) for details.
