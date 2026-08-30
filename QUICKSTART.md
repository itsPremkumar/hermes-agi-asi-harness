# 🚀 Hermes AGI/ASI Harness — Quick Start

## 1. Install (30 seconds)

```bash
cd ~/Downloads/HERMES-AGI-ASI-HARNESS-ULTIMATE-BUILD
pip install -e .
```

## 2. Run Health Check

```bash
python hermes_agi.py --health
```

Expected output:
```
🏥 Health Check:
  status: healthy
  kernel_id: <uuid>
  state: running
  plugins: {...}
  active_tasks: 0
```

## 3. List Plugins

```bash
python hermes_agi.py --list-plugins
```

## 4. Execute a Goal

```bash
python hermes_agi.py --goal "Research the latest AI agent frameworks"
```

## 5. Interactive Mode

```bash
python hermes_agi.py
```

Then type goals at the `🎯 Goal>` prompt.

## 6. Use the Memory System

```python
from plugins.memory.hybrid_memory import HybridMemoryStore, MemoryType

# Create memory store
memory = HybridMemoryStore("state/memory.db")

# Store a memory
entry = memory.remember(
    memory_type=MemoryType.SEMANTIC,
    title="AI Agent Frameworks",
    content="DeerFlow 2.0 is a super-agent harness by ByteDance.",
    tags=["ai", "agents", "frameworks"],
    confidence=0.95
)

# Search memories
results = memory.search("AI agent frameworks")
for r in results:
    print(f"{r.title}: {r.content}")
```

## 7. Create a Plugin

```python
# plugins/my_plugin/plugin.yaml
"""
name: my_plugin
version: 1.0.0
description: "My custom plugin"
license: MIT
source: internal
capabilities:
  - my_capability
cost:
  default: free
permissions:
  filesystem:
    read: project
    write: project
  network:
    allowed: []
  shell:
    allowed: []
  secrets:
    access: none
"""

# plugins/my_plugin/__init__.py
"""My custom plugin."""

from core.runtime.plugin_base import PluginBase

class Plugin(PluginBase):
    def __init__(self):
        self.manifest = None  # Loaded from plugin.yaml
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        return True
    
    async def stop(self) -> bool:
        return True
```

## 8. Configure

Edit `config/config.yaml`:

```yaml
zero_cost: true      # Free-first mode
offline: false       # Offline mode
max_parallel_tasks: 4
max_subagents: 8

model:
  preferred: llama3.2:3b
  allow_paid: false
```

## 9. Run with Ollama (Local Models)

```bash
# Install Ollama
# https://ollama.com

# Pull a model
ollama pull llama3.2:3b

# Run Hermes
HARNESS_MODEL_NAME=llama3.2:3b python hermes_agi.py
```

## 10. Run Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

---

## 🎯 Next Steps

1. **Read the architecture**: `docs/ARCHITECTURE.md`
2. **Explore plugins**: Each plugin has a `plugin.yaml` and `__init__.py`
3. **Create your own plugin**: Follow the plugin contract
4. **Join the community**: Share your plugins and improvements

---

**Welcome to the Hermes AGI/ASI Harness! 🚀**
