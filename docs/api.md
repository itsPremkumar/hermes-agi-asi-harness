# API Reference

## Core

### `Harness`

```python
from harness import Harness

h = Harness()
h.load_plugin("safety")
h.load_plugin("reasoning")
h.run()
```

### `PluginBase`

```python
from harness.plugin_base import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"

    def setup(self):
        ...

    def run(self, input_data):
        ...

    def teardown(self):
        ...
```

## Configuration

### `DynamicConfig`

```python
from harness.core.dynamic_config import DynamicConfig

config = DynamicConfig()
config.set("key", "value")
value = config.get("key")
```

## Health

### `health_check()`

```python
from harness.health import health_check

status = health_check()
# {"status": "healthy", "checks": {...}}
```

## Versioning

### `Version`

```python
from harness.versioning import Version

v = Version("1.0.0")
v.bump_major()
```

## Plugin Registry

```python
from harness.registry import Registry

registry = Registry()
registry.load("safety")
registry.get("safety")
```

## Lifecycle

```python
from harness.lifecycle import Lifecycle

lc = Lifecycle()
lc.start()
lc.stop()
lc.restart()
```
