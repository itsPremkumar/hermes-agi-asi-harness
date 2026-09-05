# 🔧 Hermes AGI/ASI Master — Setup & Integration Guide

**Complete setup guide for installing and integrating with Hermes AI Agent.**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Hermes Agent Integration](#hermes-agent-integration)
4. [Quick Start](#quick-start)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## 🔍 Prerequisites

### System Requirements
- **Python**: 3.10 or higher
- **Git**: For cloning the repository
- **RAM**: 4GB minimum (8GB recommended)
- **OS**: Windows, macOS, or Linux

### Verify Python Installation
```bash
python --version  # Should be 3.10 or higher
```

---

## 💻 Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/itsPremkumar/hermes-agi-asi-harness.git
cd hermes-agi-asi-harness
```

### Step 2: Install Dependencies

#### Option A: Using pip
```bash
pip install -r requirements.txt
```

#### Option B: Using uv (faster)
```bash
uv pip install -r requirements.txt
```

#### Option C: Development mode
```bash
pip install -e .
```

### Step 3: Verify Installation
```bash
python -m hermes_agi health
```

Expected output:
```
Health Check:
  status: healthy
  kernel_id: <uuid>
  state: running
  plugins: { ... 82 plugins ... }
  active_tasks: 0
```

---

## 🤖 Hermes Agent Integration

### Method 1: Direct Integration

```python
from core.runtime.kernel import HermesKernel, KernelConfig
from pathlib import Path

# Initialize kernel
config = KernelConfig(plugins_root=Path('plugins'))
kernel = HermesKernel(config)

# Boot the kernel
await kernel.boot()

# Execute a goal
result = await kernel.plan_and_execute("Build a REST API")

# Shutdown
await kernel.shutdown()
```

### Method 2: CLI Integration

```bash
# Simple goal execution
python -m hermes_agi run "Build a REST API with authentication"

# Interactive mode
python -m hermes_agi interactive

# 24/7 daemon mode
python -m hermes_agi daemon
```

### Method 3: Skill Integration

```python
# Use specific modules
from core.coding import RepositoryDigitalTwin, RequirementsCompiler
from core.dynamic import DynamicScenarioAnalyzer, AdvancedPlanningEngine

# Analyze a scenario
analyzer = DynamicScenarioAnalyzer()
profile = analyzer.analyze("Fix the login bug")

# Generate a plan
engine = AdvancedPlanningEngine()
plan = engine.generate_plan(profile)

# Execute the plan
for step in plan.steps:
    print(f"Step: {step.name}")
    print(f"Modules: {step.required_modules}")
```

---

## 🚀 Quick Start

### 1. Run Health Check
```bash
python -m hermes_agi health
```

### 2. Execute Your First Goal
```bash
python -m hermes_agi run "Create a Python function that calculates fibonacci numbers"
```

### 3. Interactive Mode
```bash
python -m hermes_agi interactive
```

### 4. Run Tests
```bash
PYTHONPATH=. python tests/test_v11_coding.py
PYTHONPATH=. python tests/test_v11_dynamic.py
```

---

## 📝 Usage Examples

### Example 1: Build a New Project
```python
from core.coding import RequirementsCompiler, ArchitectureSynthesizer

# Compile requirements
compiler = RequirementsCompiler()
requirements = compiler.compile("""
    Build a REST API with:
    - User authentication
    - Database integration
    - Unit tests
    - Documentation
""")

# Synthesize architectures
synth = ArchitectureSynthesizer()
candidates = synth.generate_candidates({"scale": 0.5})
best = synth.select_best()
print(f"Best architecture: {best.style.value}")
```

### Example 2: Analyze a Scenario
```python
from core.dynamic import DynamicScenarioAnalyzer

analyzer = DynamicScenarioAnalyzer()
profile = analyzer.analyze("Fix the login bug where users can't authenticate")

print(f"Scenario: {profile.scenario_type.value}")
print(f"Complexity: {profile.complexity.value}")
print(f"Required modules: {profile.required_modules}")
print(f"Estimated time: {profile.estimated_time_minutes} minutes")
```

### Example 3: Generate a Dynamic Plan
```python
from core.dynamic import DynamicScenarioAnalyzer, AdvancedPlanningEngine

analyzer = DynamicScenarioAnalyzer()
engine = AdvancedPlanningEngine()

profile = analyzer.analyze("Deploy to production AWS with CI/CD")
plan = engine.generate_plan(profile)

print(f"Plan: {len(plan.steps)} steps")
print(f"Topology: {plan.topology}")
for step in plan.steps:
    print(f"  - {step.name} ({step.step_type.value})")
```

### Example 4: Repository Analysis
```python
from core.coding import RepositoryDigitalTwin

twin = RepositoryDigitalTwin("/path/to/your/project")
twin.discover()

stats = twin.get_stats()
print(f"Files: {stats['total_files']}")
print(f"Symbols: {stats['total_symbols']}")
print(f"Lines: {stats['total_lines']}")
print(f"Languages: {stats['languages']}")
```

### Example 5: Code Graph Analysis
```python
from core.coding import CodeGraph, NodeType, RelationType

graph = CodeGraph()
n1 = graph.add_node("module_a", NodeType.MODULE, "a.py")
n2 = graph.add_node("module_b", NodeType.MODULE, "b.py")
graph.add_edge(n1.id, n2.id, RelationType.IMPORTS)

blast = graph.compute_blast_radius(n1.id)
print(f"Blast radius: {len(blast.affected_nodes)} nodes affected")
```

### Example 6: Quality Gates
```python
from core.coding import QualityGates, Gate

qg = QualityGates()
qg.pass_gate(Gate.REQUIREMENT)
qg.pass_gate(Gate.ARCHITECTURE)
qg.pass_gate(Gate.IMPLEMENTATION)
qg.pass_gate(Gate.TEST)
qg.pass_gate(Gate.SECURITY)
qg.pass_gate(Gate.DEPLOYMENT)
qg.pass_gate(Gate.PRODUCTION)

if qg.all_passed():
    print("All quality gates passed!")
else:
    print(f"Pending: {qg.get_pending()}")
```

---

## ⚙️ Configuration

### Kernel Configuration
```python
from core.runtime.kernel import KernelConfig, HermesKernel

config = KernelConfig(
    plugins_root=Path('plugins'),
    max_parallel_tasks=4,
    max_subagents=8,
    max_retries=3,
)

kernel = HermesKernel(config)
```

### Environment Variables
```bash
# Set Python path for imports
export PYTHONPATH=/path/to/hermes-agi-asi-harness

# On Windows
set PYTHONPATH=C:\path\to\hermes-agi-asi-harness
```

---

## 🧪 Running Tests

### All Tests
```bash
PYTHONPATH=. python -m pytest tests/ -v
```

### Specific Test Suites
```bash
# v9 core tests
PYTHONPATH=. python tests/test_v9_core.py

# v9 full tests
PYTHONPATH=. python tests/test_v9_full.py

# v10 tests
PYTHONPATH=. python tests/test_v10_full.py

# v11 coding tests
PYTHONPATH=. python tests/test_v11_coding.py

# v11 dynamic tests
PYTHONPATH=. python tests/test_v11_dynamic.py
```

---

## 🐛 Troubleshooting

### Issue: "No module named 'core'"
**Solution**: Set PYTHONPATH
```bash
export PYTHONPATH=/path/to/hermes-agi-asi-harness
```

### Issue: "Python version too low"
**Solution**: Upgrade Python to 3.10+
```bash
python --version  # Check version
# If < 3.10, download from python.org
```

### Issue: "Permission denied" on Windows
**Solution**: Run as Administrator or use `--user` flag
```bash
pip install --user -r requirements.txt
```

### Issue: Plugins not loading
**Solution**: Verify plugins directory exists
```bash
ls plugins/  # Should show plugin directories
```

---

## 📚 API Reference

### Core Modules

| Module | Import Path | Purpose |
|--------|-------------|---------|
| Repository Twin | `core.coding.RepositoryDigitalTwin` | Parse and model codebases |
| Code Graph | `core.coding.CodeGraph` | Dependency graph analysis |
| Semantic Index | `core.coding.SemanticCodeIndex` | Multi-level code indexing |
| Requirements | `core.coding.RequirementsCompiler` | Compile natural language requirements |
| Architecture | `core.coding.ArchitectureSynthesizer` | Generate architecture candidates |
| Task Graph | `core.coding.TaskGraph` | Dependency-aware task DAG |
| Quality Gates | `core.coding.QualityGates` | 7-gate quality pipeline |
| Merge Controller | `core.coding.MergeController` | Pre-merge checks |
| Evaluation Pyramid | `core.coding.EvaluationPyramid` | 10-level evaluation |

### Dynamic Modules

| Module | Import Path | Purpose |
|--------|-------------|---------|
| Scenario Analyzer | `core.dynamic.DynamicScenarioAnalyzer` | Classify scenarios |
| Planning Engine | `core.dynamic.AdvancedPlanningEngine` | Generate dynamic plans |
| Decision Engine | `core.dynamic.DynamicDecisionEngine` | Real-time decisions |

### Learning Modules

| Module | Import Path | Purpose |
|--------|-------------|---------|
| Trajectory Store | `core.learning.TrajectoryStore` | Store action sequences |
| Policy Learner | `core.learning.PolicyLearner` | Learn action policies |
| Counterfactual | `core.learning.CounterfactualEvaluator` | What-if analysis |

---

## 🎯 Best Practices

### 1. Always Set PYTHONPATH
```bash
export PYTHONPATH=/path/to/hermes-agi-asi-harness
```

### 2. Use Scenario Analysis First
```python
# Analyze before planning
profile = analyzer.analyze(goal)
plan = engine.generate_plan(profile)
```

### 3. Leverage Quality Gates
```python
# Always use quality gates for important changes
qg = QualityGates()
# ... pass gates ...
if qg.all_passed():
    proceed_with_merge()
```

### 4. Monitor Blast Radius
```python
# Check impact before changing files
blast = graph.compute_blast_radius(file_id)
if len(blast.affected_nodes) > 10:
    print("High impact change - review carefully")
```

### 5. Use Dynamic Planning
```python
# Let the system choose the best workflow
profile = analyzer.analyze(goal)
plan = engine.generate_plan(profile)
# Execute steps according to plan
```

---

## 📞 Support

- **GitHub Issues**: https://github.com/itsPremkumar/hermes-agi-asi-harness/issues
- **Documentation**: See `docs/` directory
- **Examples**: See `tests/` directory

---

*Built with ❤️ by itsPremkumar — Pushing the boundaries of autonomous agent architecture.*
