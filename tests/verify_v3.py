"""Verify the new LLM-powered planning and real plugins."""

import asyncio
import sys

print('=' * 70)
print('VERIFYING LLM-POWERED PLANNING & REAL PLUGINS')
print('=' * 70)
print()

# 1. LLM Client
print('1. LLM CLIENT')
print('-' * 50)
try:
    from hermes_agi.llm_planning import LLMClient
    
    client = LLMClient()
    print(f'   Model: {client.model}')
    print(f'   Base URL: {client.base_url}')
    print(f'   API Key set: {"Yes" if client.api_key else "No (will use mock)"}')
    
    # Test a simple call
    result = asyncio.run(client.chat([
        {"role": "user", "content": "Say hello in one word"}
    ]))
    print(f'   Test call result: {result[:50]}...')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 2. Knowledge Base
print('2. KNOWLEDGE BASE')
print('-' * 50)
try:
    from hermes_agi.llm_planning import KnowledgeBase
    
    kb = KnowledgeBase()
    print(f'   Entries loaded: {len(kb._entries)}')
    
    results = kb.search("planning")
    print(f'   Search "planning": {len(results)} results')
    
    results = kb.search("safety")
    print(f'   Search "safety": {len(results)} results')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 3. Evaluation Utility
print('3. EVALUATION UTILITY')
print('-' * 50)
try:
    from hermes_agi.llm_planning import EvaluationUtility
    
    evaluator = EvaluationUtility()
    
    # Test text evaluation
    result = evaluator.evaluate("test1", "This is a good output with structure and reasoning.")
    print(f'   Text score: {result["score"]}')
    print(f'   Feedback: {result["feedback"]}')
    
    # Test structured evaluation
    result = evaluator.evaluate("test2", {"status": "completed", "result": "success"})
    print(f'   Structured score: {result["score"]}')
    
    avg = evaluator.get_average_score()
    print(f'   Average score: {avg}')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 4. Real Planner
print('4. REAL PLANNER')
print('-' * 50)
try:
    from hermes_agi.llm_planning import RealPlanner, LLMClient, KnowledgeBase
    
    planner = RealPlanner()
    result = asyncio.run(planner.think_and_plan("Create a Python web API"))
    
    print(f'   Plan ID: {result.get("plan_id")}')
    print(f'   Thoughts: {len(result.get("thoughts", []))}')
    print(f'   Knowledge used: {len(result.get("knowledge_used", []))}')
    print(f'   Evaluation score: {result.get("evaluation", {}).get("score", 0)}')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 5. Real Plugins
print('5. REAL PLUGINS')
print('-' * 50)
try:
    from hermes_agi.plugins.real_plugins import (
        RealPlanningPlugin, RealResearchPlugin, RealCodingPlugin,
        RealTestingPlugin, RealBenchmarkPlugin, RealDiscoveryPlugin,
        ALL_REAL_PLUGINS,
    )
    
    print(f'   Real plugins available: {len(ALL_REAL_PLUGINS)}')
    
    # Test each plugin
    for plugin_cls in ALL_REAL_PLUGINS:
        plugin = plugin_cls()
        print(f'   - {plugin.name}: {len(plugin.get_capabilities())} capabilities')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 6. Full Harness with Real Plugins
print('6. FULL HARNESS WITH REAL PLUGINS')
print('-' * 50)
try:
    from hermes_agi import Harness
    
    harness = asyncio.run(Harness.create(use_real_plugins=True))
    print(f'   Initialized: {harness._initialized}')
    print(f'   Plugins: {len(harness.plugin_manager.plugins)}')
    print(f'   Running: {len(harness.plugin_manager.running_plugins)}')
    
    # Run a task
    result = asyncio.run(harness.run("Test task"))
    print(f'   Task result: {result["status"]}')
    
    # Get status
    status = asyncio.run(harness.status())
    print(f'   Status keys: {list(status.keys())}')
    
    # Get health
    health = asyncio.run(harness.health())
    print(f'   Health: {health["status"]}')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 7. Hermes Integration
print('7. HERMES INTEGRATION')
print('-' * 50)
try:
    from hermes_agi import HermesDetector
    
    config = HermesDetector.detect()
    if config:
        print(f'   Hermes detected: {config.hermes_dir}')
        print(f'   Version: {config.version}')
    else:
        print('   Hermes not detected')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 8. Workflow Engine
print('8. WORKFLOW ENGINE')
print('-' * 50)
try:
    from hermes_agi import WorkflowEngine, Task
    
    engine = WorkflowEngine()
    
    async def sample_task():
        await asyncio.sleep(0.01)
        return "done"
    
    tasks = [
        Task(task_id="t1", name="Task 1", coro=sample_task),
        Task(task_id="t2", name="Task 2", coro=sample_task, dependencies=["t1"]),
    ]
    
    result = asyncio.run(engine.execute(tasks))
    print(f'   Workflow ID: {result.workflow_id}')
    print(f'   State: {result.state.value}')
    print(f'   Duration: {result.duration:.3f}s')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 9. Self-Recovery
print('9. SELF-RECOVERY SYSTEM')
print('-' * 50)
try:
    from hermes_agi import SelfRecoverySystem
    
    recovery = SelfRecoverySystem()
    
    async def health_check():
        return {"healthy": True}
    
    recovery.register_component("test", health_check)
    
    asyncio.run(recovery.report_success("test"))
    health = asyncio.run(recovery.check_health("test"))
    print(f'   Health: {health.value}')
    
    cp_id = asyncio.run(recovery.create_checkpoint("test", {"key": "value"}))
    restored = asyncio.run(recovery.restore_checkpoint(cp_id))
    print(f'   Checkpoint: {restored}')
    
    summary = recovery.get_health_summary()
    print(f'   Summary: {summary["total_failures"]} failures')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 10. Feature Registry
print('10. FEATURE REGISTRY')
print('-' * 50)
try:
    from hermes_agi import get_all_features, get_all_capabilities
    
    features = get_all_features()
    print(f'   Features: {len(features)}')
    
    capabilities = get_all_capabilities()
    print(f'   Capabilities: {len(capabilities)}')
    
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

print()
print('=' * 70)
print('ALL VERIFICATIONS COMPLETED')
print('=' * 70)
