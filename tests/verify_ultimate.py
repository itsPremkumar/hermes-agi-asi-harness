"""Comprehensive verification of all new features."""

import asyncio

print('=' * 70)
print('ULTIMATE HARNESS VERIFICATION — ALL FEATURES')
print('=' * 70)
print()

# 1. Plugin System
print('1. PLUGIN SYSTEM')
print('-' * 50)
try:
    from hermes_agi import (
        PluginManager,
        register_all_plugins,
    )
    
    manager = PluginManager()
    register_all_plugins(manager)
    print(f'   Plugins registered: {len(manager.plugins)}')
    
    # Load all
    load_results = asyncio.run(manager.load_all())
    loaded = sum(1 for v in load_results.values() if v)
    print(f'   Plugins loaded: {loaded}/{len(load_results)}')
    
    # Start all
    start_results = asyncio.run(manager.start_all())
    started = sum(1 for v in start_results.values() if v)
    print(f'   Plugins started: {started}/{len(start_results)}')
    
    # Check capabilities
    caps = manager.get_capabilities()
    print(f'   Total capabilities: {len(caps)}')
    
    # Execute a plugin action
    result = asyncio.run(manager.execute('planning', 'plan', goal='Test goal'))
    print(f'   Plan result: {result.get("plan_id", "N/A")}')
    
    # Parallel execution
    results = asyncio.run(manager.execute_parallel('research', 'search', query='test'))
    print(f'   Parallel results: {len(results)} plugins responded')
    
    # Health check
    health = asyncio.run(manager.health_check_all())
    healthy = sum(1 for h in health.values() if h.get('healthy', False))
    print(f'   Healthy plugins: {healthy}/{len(health)}')
    
    # Status
    status = manager.status()
    print(f'   Running: {status["running"]}/{status["total_plugins"]}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 2. Workflow Engine
print('2. WORKFLOW ENGINE')
print('-' * 50)
try:
    from hermes_agi import Task, WorkflowBuilder, WorkflowEngine
    
    engine = WorkflowEngine(max_parallel=4)
    
    # Create a simple workflow
    async def task1():
        await asyncio.sleep(0.01)
        return 'task1_done'
    
    async def task2():
        await asyncio.sleep(0.01)
        return 'task2_done'
    
    async def task3():
        await asyncio.sleep(0.01)
        return 'task3_done'
    
    tasks = [
        Task(task_id='t1', name='Task 1', coro=task1),
        Task(task_id='t2', name='Task 2', coro=task2, dependencies=['t1']),
        Task(task_id='t3', name='Task 3', coro=task3, dependencies=['t1']),
    ]
    
    result = asyncio.run(engine.execute(tasks))
    print(f'   Workflow ID: {result.workflow_id}')
    print(f'   State: {result.state.value}')
    print(f'   Duration: {result.duration:.3f}s')
    print(f'   Tasks completed: {sum(1 for r in result.results.values() if r.state.value == "completed")}')
    
    # Test workflow builder
    builder = WorkflowBuilder('test')
    builder.add_task('a', 'Task A', task1)
    builder.add_task('b', 'Task B', task2, dependencies=['a'])
    built = builder.build()
    print(f'   Builder tasks: {len(built)}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 3. Self-Recovery System
print('3. SELF-RECOVERY SYSTEM')
print('-' * 50)
try:
    from hermes_agi import DegradationManager, SelfRecoverySystem, with_fallback, with_retry
    
    recovery = SelfRecoverySystem()
    
    # Register a component
    async def health_check():
        return {'healthy': True}
    
    recovery.register_component('test_component', health_check)
    print(f'   Components registered: {len(recovery._health_records)}')
    
    # Report success/failure
    asyncio.run(recovery.report_success('test_component', 'All good'))
    health = asyncio.run(recovery.check_health('test_component'))
    print(f'   Health status: {health.value}')
    
    # Checkpoint
    cp_id = asyncio.run(recovery.create_checkpoint('test_component', {'key': 'value'}))
    print(f'   Checkpoint created: {cp_id}')
    
    restored = asyncio.run(recovery.restore_checkpoint(cp_id))
    print(f'   Checkpoint restored: {restored}')
    
    # Health summary
    summary = recovery.get_health_summary()
    print(f'   Health summary: {summary["total_failures"]} failures, {summary["total_checkpoints"]} checkpoints')
    
    # Degradation manager
    deg_mgr = DegradationManager()
    deg_mgr.register_service('api', max_level=3)
    print(f'   Service level: {deg_mgr.get_level("api")}')
    deg_mgr.degrade('api')
    print(f'   After degrade: {deg_mgr.get_level("api")}')
    deg_mgr.restore('api')
    print(f'   After restore: {deg_mgr.get_level("api")}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 4. Hermes Integration
print('4. HERMES INTEGRATION')
print('-' * 50)
try:
    from hermes_agi import HermesDetector
    
    # Detect Hermes
    config = HermesDetector.detect()
    if config:
        print(f'   Hermes detected: {config.hermes_dir}')
        print(f'   Version: {config.version}')
        print(f'   Profiles: {config.profiles_dir}')
    else:
        print('   Hermes not detected (expected in some environments)')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 5. Full Harness
print('5. FULL HARNESS')
print('-' * 50)
try:
    from hermes_agi import Harness
    
    harness = asyncio.run(Harness.create())
    print(f'   Harness initialized: {harness._initialized}')
    print(f'   Plugins: {len(harness.plugin_manager.plugins)}')
    print(f'   Running: {len(harness.plugin_manager.running_plugins)}')
    
    # Run a task
    result = asyncio.run(harness.run('Test task'))
    print(f'   Task result: {result["status"]}')
    
    # Get status
    status = asyncio.run(harness.status())
    print(f'   Status keys: {list(status.keys())}')
    
    # Get health
    health = asyncio.run(harness.health())
    print(f'   Health: {health["status"]}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 6. Decorators
print('6. DECORATORS (retry, fallback, circuit_breaker)')
print('-' * 50)
try:
    from hermes_agi import with_fallback, with_retry
    
    # Test retry
    call_count = [0]
    
    @with_retry(max_retries=2, delay=0.01)
    async def flaky_function():
        call_count[0] += 1
        if call_count[0] < 2:
            raise RuntimeError('Temporary error')
        return 'success'
    
    result = asyncio.run(flaky_function())
    print(f'   Retry result: {result} (attempts: {call_count[0]})')
    
    # Test fallback
    @with_fallback(lambda: 'fallback_value')
    async def failing_function():
        raise RuntimeError('Always fails')
    
    result = asyncio.run(failing_function())
    print(f'   Fallback result: {result}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 7. Feature Registry
print('7. FEATURE REGISTRY')
print('-' * 50)
try:
    from hermes_agi import (
        find_by_capability,
        get_all_capabilities,
        get_all_features,
        search_features,
    )
    
    features = get_all_features()
    print(f'   Total features: {len(features)}')
    
    capabilities = get_all_capabilities()
    print(f'   Total capabilities: {len(capabilities)}')
    
    results = search_features('research')
    print(f'   Search "research": {len(results)} results')
    
    results = find_by_capability('code')
    print(f'   Find "code": {len(results)} results')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 8. Safety Governor
print('8. SAFETY GOVERNOR')
print('-' * 50)
try:
    from hermes_agi.safety import SafetyGovernor
    
    governor = SafetyGovernor()
    profile = governor.assess('Test action', 0.8, 0.9)
    print(f'   Risk ID: {profile.risk_id}')
    print(f'   Score: {profile.score}')
    print(f'   Level: {profile.level.value}')
    print(f'   Acceptable: {governor.is_acceptable(profile)}')
    print(f'   Invariants: {len(governor.INVARIANTS)}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 9. Bot Swarm
print('9. BOT SWARM')
print('-' * 50)
try:
    from hermes_agi.agents import BotSwarm
    
    swarm = BotSwarm()
    bots = swarm.list_bots()
    print(f'   Bot profiles: {len(bots)}')
    
    result = asyncio.run(swarm.spawn('harness-coder', 'implement feature'))
    print(f'   Spawn status: {result["status"]}')
    
    profile = swarm.create_profile('test-bot', 'Test role', 'meituan/longcat-2.0:free')
    print(f'   Dynamic profile: {profile.name} ({profile.role})')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 10. Benchmark Runner
print('10. BENCHMARK RUNNER')
print('-' * 50)
try:
    from hermes_agi.benchmarks import BENCHMARK_REGISTRY, BenchmarkRunner
    
    runner = BenchmarkRunner()
    print(f'   Benchmarks: {len(BENCHMARK_REGISTRY)}')
    
    result = asyncio.run(runner.run('mmlu'))
    print(f'   MMLU status: {result["status"]}')
    
    result = asyncio.run(runner.run('all'))
    print(f'   All benchmarks: {len(result)} completed')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 11. Cognitive Architecture
print('11. COGNITIVE ARCHITECTURE')
print('-' * 50)
try:
    from hermes_agi.cognitive import SelfModel, WorldModel
    
    world = WorldModel()
    world.update('entity1', {'name': 'test', 'value': 42})
    status = world.status()
    print(f'   World entities: {status["entities"]}')
    
    self_model = SelfModel()
    self_model.update('python', True, 10)
    self_model.update('python', False, 2)
    status = self_model.status()
    print(f'   Self model domains: {status["domains"]}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 12. Research Engine
print('12. RESEARCH ENGINE')
print('-' * 50)
try:
    from hermes_agi.research import ResearchEngine
    
    engine = ResearchEngine()
    report = asyncio.run(engine.research('AI agents'))
    print(f'   Report ID: {report.report_id}')
    print(f'   Findings: {len(report.findings)}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 13. Kernel Controller
print('13. KERNEL CONTROLLER')
print('-' * 50)
try:
    from hermes_agi.kernel import KernelController
    
    config = type('Config', (), {'project_path': '.', 'state_dir': '/tmp/test'})()
    kernel = KernelController(config)
    asyncio.run(kernel.initialize())
    result = asyncio.run(kernel.run('Test task'))
    print(f'   Task state: {result["state"]}')
    print(f'   Task phase: {result["phase"]}')
    
    status = asyncio.run(kernel.status())
    print(f'   Kernel state: {status["state"]}')
    
    health = asyncio.run(kernel.health())
    print(f'   Health: {health["status"]}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 14. Meta Discovery
print('14. META DISCOVERY')
print('-' * 50)
try:
    from hermes_agi.discovery import MetaDiscovery
    
    discovery = asyncio.run(MetaDiscovery.create())
    print(f'   Features discovered: {len(discovery.features)}')
    
    results = discovery.search('kernel')
    print(f'   Search "kernel": {len(results)} results')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 15. Configuration
print('15. CONFIGURATION')
print('-' * 50)
try:
    from hermes_agi.config import load_config
    
    config = load_config()
    print(f'   Project path: {config.project_path}')
    print(f'   Plugins dir: {config.plugins_dir}')
    print(f'   Profiles dir: {config.profiles_dir}')
    print(f'   State dir: {config.state_dir}')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 16. Exceptions
print('16. EXCEPTIONS')
print('-' * 50)
try:
    from hermes_agi.exceptions import (
        BenchmarkError,
        HarnessError,
        KernelError,
        PluginError,
        SafetyError,
    )
    
    assert issubclass(KernelError, HarnessError)
    assert issubclass(PluginError, HarnessError)
    assert issubclass(SafetyError, HarnessError)
    assert issubclass(BenchmarkError, HarnessError)
    print('   Exception hierarchy: correct')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

# 17. Utils
print('17. UTILITIES')
print('-' * 50)
try:
    from hermes_agi.utils import get_logger, setup_logging
    
    setup_logging('INFO')
    logger = get_logger('test')
    logger.info('Test log message')
    print('   Logging: works')
    
    print('   PASSED')
except Exception as e:
    import traceback
    print(f'   FAILED: {e}')
    traceback.print_exc()
print()

print()
print('=' * 70)
print('ALL VERIFICATIONS COMPLETED')
print('=' * 70)
