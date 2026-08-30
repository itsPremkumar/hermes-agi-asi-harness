# Harnix — Harness Runtime Kernel

LangGraph StateGraph + Agent Lifecycle for autonomous task execution.

## Architecture

```
init → plan → dispatch → monitor → (dispatch | adjust | evolve | complete)
```

- **init**: Initialize agent state, set phase to PLANNING
- **plan**: Rule-based task decomposition into ordered steps
- **dispatch**: Execute current plan step
- **monitor**: Check progress, detect stalls, update score
- **adjust**: Re-plan or change strategy when stalled
- **evolve**: Generate evolved approach when multiple stalls detected
- **complete**: Finalize the run

## Usage

```python
from harnix import HarnessRuntimeKernel

kernel = HarnessRuntimeKernel()
result = kernel.run("write file demo.txt containing HELLO")

print(result["status"])    # "completed"
print(result["score"])     # 1.0
print(result["messages"])  # execution log
```

## State

```python
from harnix import AgentState, AgentPhase, create_initial_state

state = create_initial_state("my task")
# state["phase"]     # current lifecycle phase
# state["status"]    # running | completed | failed
# state["score"]     # 0.0 - 1.0 progress
# state["plan"]      # list of plan steps
# state["results"]    # execution results
# state["memory"]    # accumulated memory
```

## Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
