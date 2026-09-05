#!/usr/bin/env python3
"""
HERMES AGI/ASI HARNESS v7.0 — FINAL TEST SUITE
================================================
Tests all components to verify functionality.

Includes:
- Core modules (reasoning, swarm, protocol, metacognition, causal, genetic, sandbox, secrets)
- New search plugins (AgentEye, Deep Research Agent, LangGraph Orchestration)
"""

import asyncio
import sys

# Add project to path
sys.path.insert(0, '.')

async def test_all():
    """Test all components."""
    results = []
    
    # Test core components
    print("Testing core components...")
    
    try:
        from core.reasoning import ReasoningEngine, ReasoningMode
        engine = ReasoningEngine()
        result = await engine.reason("What is AI?", ReasoningMode.COT)
        results.append(("ReasoningEngine", True, result.confidence))
    except Exception as e:
        results.append(("ReasoningEngine", False, str(e)))
    
    try:
        from core.swarm import SwarmOrchestrator
        swarm = SwarmOrchestrator()
        agent_ids = await swarm.spawn_swarm("test task", 3)
        results.append(("SwarmOrchestrator", True, len(agent_ids)))
    except Exception as e:
        results.append(("SwarmOrchestrator", False, str(e)))
    
    try:
        from core.protocol import CommunicationProtocol
        protocol = CommunicationProtocol()
        await protocol.send("agent1", "agent2", "test message")
        results.append(("CommunicationProtocol", True, "sent"))
    except Exception as e:
        results.append(("CommunicationProtocol", False, str(e)))
    
    try:
        from core.metacognition import CognitiveMode, MetacognitiveMonitor
        monitor = MetacognitiveMonitor()
        assessment = await monitor.assess(CognitiveMode.FAST)
        results.append(("MetacognitiveMonitor", True, len(assessment.issues)))
    except Exception as e:
        results.append(("MetacognitiveMonitor", False, str(e)))
    
    try:
        from core.causal import CausalEngine
        causal = CausalEngine()
        graph = causal.build_graph("test")
        results.append(("CausalEngine", True, len(graph.nodes)))
    except Exception as e:
        results.append(("CausalEngine", False, str(e)))
    
    try:
        from core.genetic import GeneticEvolution
        genetic = GeneticEvolution()
        results.append(("GeneticEvolution", True, "initialized"))
    except Exception as e:
        results.append(("GeneticEvolution", False, str(e)))
    
    try:
        from core.sandbox import SandboxedExecution
        sandbox = SandboxedExecution()
        results.append(("SandboxedExecution", True, "ready"))
    except Exception as e:
        results.append(("SandboxedExecution", False, str(e)))
    
    try:
        from core.secrets import SecretManager
        secrets = SecretManager()
        secrets.store_secret("test", "value")
        results.append(("SecretManager", True, secrets.get_secret("test")))
    except Exception as e:
        results.append(("SecretManager", False, str(e)))
    
    # Test new search plugins
    print("Testing search plugins...")
    
    try:
        from plugins.agent_eye_search import Plugin as AgentEyePlugin
        plugin = AgentEyePlugin()
        await plugin.load()
        await plugin.start()
        results.append(("AgentEyeSearch", True, f"capabilities: {plugin.get_capabilities()}"))
        await plugin.stop()
    except Exception as e:
        results.append(("AgentEyeSearch", False, str(e)))
    
    try:
        from plugins.deep_research_agent import Plugin as DeepResearchPlugin
        plugin = DeepResearchPlugin()
        await plugin.load()
        await plugin.start()
        results.append(("DeepResearchAgent", True, f"capabilities: {plugin.get_capabilities()}"))
        await plugin.stop()
    except Exception as e:
        results.append(("DeepResearchAgent", False, str(e)))
    
    try:
        from plugins.langgraph_orchestration import Plugin as LangGraphPlugin
        plugin = LangGraphPlugin()
        await plugin.load()
        await plugin.start()
        results.append(("LangGraphOrchestration", True, f"capabilities: {plugin.get_capabilities()}"))
        await plugin.stop()
    except Exception as e:
        results.append(("LangGraphOrchestration", False, str(e)))
    
    # Test existing research plugin
    try:
        from plugins.research import Plugin as ResearchPlugin
        plugin = ResearchPlugin()
        results.append(("ResearchPlugin", True, f"capabilities: {plugin.capabilities()}"))
    except Exception as e:
        results.append(("ResearchPlugin", False, str(e)))
    
    # Print results
    print("\n" + "=" * 70)
    print("  HERMES AGI/ASI HARNESS v7.0 — TEST RESULTS")
    print("=" * 70 + "\n")
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    for name, success, detail in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {name}: {detail}")
    
    print(f"\n  Total: {passed}/{len(results)} passed")
    print("=" * 70)
    
    return passed == len(results)

if __name__ == "__main__":
    success = asyncio.run(test_all())
    sys.exit(0 if success else 1)
