# Hermes AGI/ASI Harness

A unified AI agent runtime combining kernel lifecycle, plugin system, bot swarms, benchmarks, safety governance, and self-improvement.

## Architecture

```
hermes_agi/
├── __init__.py          # Top-level Harness class
├── __main__.py          # CLI entry point
├── config.py            # Configuration management
├── exceptions.py        # Core exceptions
├── kernel/              # harnix kernel lifecycle
│   ├── __init__.py
│   └── controller.py    # KernelController, KernelState, KernelPhase
├── bridge/              # Hermes Agent integration
│   ├── __init__.py
│   └── hermes_bridge.py # HermesBridge, BotSwarm, BenchmarkRunner
├── plugins/             # Plugin system
│   ├── __init__.py
│   └── manager.py       # PluginManager, PluginBase, PluginState
├── safety/              # R0-R6 safety governance
│   ├── __init__.py
│   └── governor.py      # SafetyGovernor, RiskLevel, RiskProfile
├── agents/              # Bot swarm (26+ profiles)
│   ├── __init__.py
│   └── swarm.py         # BotSwarm, BotProfile, BOT_PROFILES
├── benchmarks/          # Evaluation suite (13 benchmarks)
│   ├── __init__.py
│   └── runner.py        # BenchmarkRunner, BENCHMARK_REGISTRY
├── discovery/           # Feature discovery engine
│   ├── __init__.py
│   └── engine.py        # MetaDiscovery, DiscoveredFeature
├── cognitive/           # Cognitive architecture
│   ├── __init__.py
│   ├── world_model.py   # World state management
│   └── self_model.py    # Empirical capability tracking
├── research/            # Deep research engine
│   ├── __init__.py
│   └── engine.py        # ResearchEngine, ResearchReport
└── utils/               # Shared utilities
    ├── __init__.py
    ├── logging.py       # Logging setup
    └── async_utils.py   # Async helpers
```

## Quick Start

```python
import asyncio
from hermes_agi import Harness

async def main():
    harness = await Harness.create()
    
    # Run a task
    result = await harness.run("implement feature X")
    
    # Run benchmarks
    result = await harness.benchmark("mmlu")
    
    # Spawn a bot
    result = await harness.spawn("coder", "implement Y")
    
    # Get status
    status = await harness.status()

asyncio.run(main())
```

## CLI Usage

```bash
# Run a task
python -m hermes_agi run "your task"

# Run benchmarks
python -m hermes_agi benchmark --name mmlu

# Spawn a bot
python -m hermes_agi spawn coder "implement feature"

# Check status
python -m hermes_agi status

# Health check
python -m hermes_agi health

# Discover features
python -m hermes_agi discover research
```

## Installation

```bash
pip install -e .
# or with dev dependencies
pip install -e ".[dev]"
```

## License

MIT
