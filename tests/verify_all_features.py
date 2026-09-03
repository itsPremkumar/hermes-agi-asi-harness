"""Comprehensive feature verification test."""

import asyncio
import sys

print('=' * 60)
print('COMPREHENSIVE FEATURE VERIFICATION')
print('=' * 60)
print()

# 1. Planning & Thinking Engine
print('1. PLANNING & THINKING ENGINE')
print('-' * 40)
try:
    from hermes_agi.planning import Planner, get_all_features, get_all_capabilities
    
    features = get_all_features()
    print(f'   Features loaded: {len(features)}')
    
    capabilities = get_all_capabilities()
    print(f'   Capabilities: {len(capabilities)}')
    
    planner = Planner()
    plan = asyncio.run(planner.think_and_plan('Research AI agent architectures and implement a prototype'))
    print(f'   Plan ID: {plan.plan_id}')
    print(f'   Thoughts: {len(plan.thoughts)}')
    print(f'   Decisions: {len(plan.decisions)}')
    print(f'   Steps: {len(plan.steps)}')
    print(f'   Est. time: {plan.estimated_total_time}s')
    print(f'   Est. cost: ${plan.estimated_total_cost}')
    print(f'   Risk: {plan.risk_assessment["overall_risk_level"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 2. Feature Registry
print('2. FEATURE REGISTRY')
print('-' * 40)
try:
    from hermes_agi.planning import FeatureRegistry, FeatureCategory
    
    registry = FeatureRegistry()
    slash = registry.find_by_category(FeatureCategory.SLASH_COMMAND)
    tools = registry.find_by_category(FeatureCategory.TOOL)
    plugins = registry.find_by_category(FeatureCategory.PLUGIN)
    bots = registry.find_by_category(FeatureCategory.BOT)
    workflows = registry.find_by_category(FeatureCategory.WORKFLOW)
    mcp = registry.find_by_category(FeatureCategory.MCP_SERVER)
    skills = registry.find_by_category(FeatureCategory.SKILL)
    
    print(f'   Slash commands: {len(slash)}')
    print(f'   Tools: {len(tools)}')
    print(f'   Plugins: {len(plugins)}')
    print(f'   Bots: {len(bots)}')
    print(f'   Workflows: {len(workflows)}')
    print(f'   MCP servers: {len(mcp)}')
    print(f'   Skills: {len(skills)}')
    
    results = registry.search('research')
    print(f'   Search "research": {len(results)} results')
    
    results = registry.find_by_capability('code')
    print(f'   Find "code": {len(results)} results')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 3. Safety Governor
print('3. SAFETY GOVERNOR')
print('-' * 40)
try:
    from hermes_agi.safety import SafetyGovernor, RiskLevel
    
    governor = SafetyGovernor()
    profile = governor.assess('Test risk', 0.8, 0.9)
    print(f'   Risk ID: {profile.risk_id}')
    print(f'   Score: {profile.score}')
    print(f'   Level: {profile.level.value}')
    print(f'   Acceptable: {governor.is_acceptable(profile)}')
    print(f'   Invariants: {len(governor.INVARIANTS)}')
    print(f'   Risk levels: {len(governor.RISK_LEVELS)}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 4. Kernel Controller
print('4. KERNEL CONTROLLER')
print('-' * 40)
try:
    from hermes_agi.kernel import KernelController, KernelState, KernelPhase
    
    config = type('Config', (), {'project_path': '.', 'state_dir': '/tmp/test'})()
    kernel = KernelController(config)
    asyncio.run(kernel.initialize())
    result = asyncio.run(kernel.run('Test task'))
    print(f'   Task state: {result["state"]}')
    print(f'   Task phase: {result["phase"]}')
    print(f'   Task score: {result["score"]}')
    status = asyncio.run(kernel.status())
    print(f'   Kernel state: {status["state"]}')
    health = asyncio.run(kernel.health())
    print(f'   Health: {health["status"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 5. Bot Swarm
print('5. BOT SWARM')
print('-' * 40)
try:
    from hermes_agi.agents import BotSwarm, BOT_PROFILES
    
    swarm = BotSwarm()
    bots = swarm.list_bots()
    print(f'   Bot profiles: {len(bots)}')
    
    result = asyncio.run(swarm.spawn('harness-coder', 'implement feature'))
    print(f'   Spawn status: {result["status"]}')
    print(f'   Bot model: {result["model"]}')
    
    profile = swarm.create_profile('test-bot', 'Test role', 'meituan/longcat-2.0:free')
    print(f'   Dynamic profile: {profile.name} ({profile.role})')
    
    status = asyncio.run(swarm.status())
    print(f'   Total profiles: {status["profiles"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 6. Benchmark Runner
print('6. BENCHMARK RUNNER')
print('-' * 40)
try:
    from hermes_agi.benchmarks import BenchmarkRunner, BENCHMARK_REGISTRY
    
    runner = BenchmarkRunner()
    print(f'   Benchmarks: {len(BENCHMARK_REGISTRY)}')
    
    result = asyncio.run(runner.run('mmlu'))
    print(f'   MMLU status: {result["status"]}')
    
    result = asyncio.run(runner.run('all'))
    print(f'   All benchmarks: {len(result)} completed')
    
    status = asyncio.run(runner.status())
    print(f'   Available: {len(status["available"])}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 7. Meta Discovery
print('7. META DISCOVERY')
print('-' * 40)
try:
    from hermes_agi.discovery import MetaDiscovery, DiscoveredFeature
    
    discovery = asyncio.run(MetaDiscovery.create())
    print(f'   Features discovered: {len(discovery.features)}')
    
    results = discovery.find_by_capability('research')
    print(f'   Research capabilities: {len(results)}')
    
    results = discovery.search('kernel')
    print(f'   Search "kernel": {len(results)} results')
    
    all_features = discovery.get_all_features()
    print(f'   Categories: {list(all_features.keys())}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 8. Hermes Bridge
print('8. HERMES BRIDGE')
print('-' * 40)
try:
    from hermes_agi.bridge import HermesBridge
    
    config = type('Config', (), {'project_path': '.', 'state_dir': '/tmp/test', 'plugins_dir': 'plugins', 'profiles_dir': '~/.hermes/profiles'})()
    bridge = asyncio.run(HermesBridge.create(config))
    
    result = asyncio.run(bridge.run('test task'))
    print(f'   Run result: {result["status"]}')
    
    result = asyncio.run(bridge.benchmark('mmlu'))
    print(f'   Benchmark: {result["status"]}')
    
    result = asyncio.run(bridge.spawn_bot('harness-coder', 'test'))
    print(f'   Spawn: {result["status"]}')
    
    status = asyncio.run(bridge.status())
    print(f'   Status: {list(status.keys())}')
    
    health = asyncio.run(bridge.health())
    print(f'   Health: {health["status"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 9. Plugin Manager
print('9. PLUGIN MANAGER')
print('-' * 40)
try:
    from hermes_agi.plugins import PluginManager, PluginBase, PluginState
    
    manager = PluginManager()
    
    class TestPlugin(PluginBase):
        PLUGIN_CONFIG = {
            "name": "test_plugin",
            "description": "Test plugin",
            "version": "1.0.0",
            "capabilities": ["test"],
        }
    
    plugin = TestPlugin()
    manager.register(plugin)
    
    status = asyncio.run(manager.status())
    print(f'   Plugins registered: {status["total"]}')
    print(f'   Plugin state: {status["plugins"]["test_plugin"]}')
    
    health = asyncio.run(plugin.health())
    print(f'   Plugin health: {health["state"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 10. Config
print('10. CONFIGURATION')
print('-' * 40)
try:
    from hermes_agi.config import Config, load_config
    
    config = load_config()
    print(f'   Project path: {config.project_path}')
    print(f'   Plugins dir: {config.plugins_dir}')
    print(f'   Profiles dir: {config.profiles_dir}')
    print(f'   State dir: {config.state_dir}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 11. Exceptions
print('11. EXCEPTIONS')
print('-' * 40)
try:
    from hermes_agi.exceptions import (
        HarnessError, KernelError, PluginError, SafetyError, BenchmarkError
    )
    
    assert issubclass(KernelError, HarnessError)
    assert issubclass(PluginError, HarnessError)
    assert issubclass(SafetyError, HarnessError)
    assert issubclass(BenchmarkError, HarnessError)
    print('   Exception hierarchy: correct')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 12. Utils
print('12. UTILITIES')
print('-' * 40)
try:
    from hermes_agi.utils import setup_logging, get_logger, gather_limited
    
    setup_logging('INFO')
    logger = get_logger('test')
    logger.info('Test log message')
    print('   Logging: works')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 13. Cognitive
print('13. COGNITIVE ARCHITECTURE')
print('-' * 40)
try:
    from hermes_agi.cognitive import WorldModel, SelfModel
    
    world = WorldModel()
    world.update('test_entity', {'name': 'test', 'value': 42})
    status = world.status()
    print(f'   World entities: {status["entities"]}')
    
    self_model = SelfModel()
    self_model.update('python', True, 10)
    self_model.update('python', False, 2)
    status = self_model.status()
    print(f'   Self model domains: {status["domains"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

# 14. Research
print('14. RESEARCH ENGINE')
print('-' * 40)
try:
    from hermes_agi.research import ResearchEngine
    
    engine = ResearchEngine()
    report = asyncio.run(engine.research('AI agent architectures'))
    print(f'   Report ID: {report.report_id}')
    print(f'   Findings: {len(report.findings)}')
    status = engine.status()
    print(f'   Total reports: {status["total_reports"]}')
    print('   PASSED')
except Exception as e:
    print(f'   FAILED: {e}')
print()

print()
print('=' * 60)
print('ALL TESTS COMPLETED')
print('=' * 60)
