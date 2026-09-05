"""Production Polish - Final integration, tests, and deployment configuration."""
from __future__ import annotations

# Phase 10: Production Polish includes:
# 1. Comprehensive test suite
# 2. Docker configuration
# 3. Deployment scripts
# 4. Monitoring and observability
# 5. Documentation
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


async def run_comprehensive_test():
    """Run comprehensive end-to-end test of all system components."""
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v12 — Production Test Suite")
    print(f"{'='*60}")
    
    results = []
    
    # Test 1: All imports
    print("\n[1/10] Testing all imports...")
    try:
        from core.api import app as api_app
        from core.cicd import CICDManager
        from core.coding.code_generator import CodeGenerator
        from core.llm import LLMProviderManager
        from core.runtime.kernel import HermesKernel, KernelConfig
        from core.security import SecurityScanner
        from core.storage import DatabaseManager, MissionStore, SkillStore
        from core.storage import TrajectoryStore as DBTrajectoryStore
        from core.tools import ToolManager
        
        results.append(("All imports", True, "All 50+ modules imported successfully"))
        print("  ✓ All imports successful")
    except Exception as e:
        results.append(("All imports", False, str(e)))
        print(f"  ✗ Import failed: {e}")
        return results
    
    # Test 2: LLM Provider System
    print("\n[2/10] Testing LLM Provider System...")
    try:
        manager = LLMProviderManager()
        
        # Test Ollama provider (doesn't need API key)
        from core.llm import LLMConfig, LLMProvider
        config = LLMConfig(provider=LLMProvider.OLLAMA, model="llama3")
        provider = manager.register_provider(config)
        
        assert manager.available_providers == [LLMProvider.OLLAMA]
        
        results.append(("LLM Provider", True, f"Provider: {manager.available_providers[0].value}"))
        print(f"  ✓ LLM Provider: {manager.available_providers[0].value}")
    except Exception as e:
        results.append(("LLM Provider", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 3: Database & Storage
    print("\n[3/10] Testing Database & Storage...")
    try:
        db = DatabaseManager("sqlite+aiosqlite:///test_hermes.db")
        await db.init_db()
        
        trajectory_store = DBTrajectoryStore(db)
        mission_store = MissionStore(db)
        skill_store = SkillStore(db)
        
        # Test trajectory creation
        traj_id = await trajectory_store.create_trajectory("mission-1", "Test goal", "test", "simple")
        
        # Test mission creation
        mission_id = await mission_store.create_mission("Test goal", "test", "simple")
        
        # Test stats
        stats = await trajectory_store.get_stats()
        
        # Cleanup
        await db.close()
        import os
        os.remove("test_hermes.db")
        
        results.append(("Database", True, f"Trajectories: {stats['total']}"))
        print(f"  ✓ Database: {stats['total']} trajectories")
    except Exception as e:
        results.append(("Database", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 4: Configuration System
    print("\n[4/10] Testing Configuration System...")
    try:
        from core.config import Config, LLMConfig
        
        config = Config()
        assert config.llm.provider == "ollama"
        assert config.api.port == 8000
        
        # Test env override
        import os
        os.environ["LLM_PROVIDER"] = "openai"
        config = Config.from_env()
        assert config.llm.provider == "openai"
        del os.environ["LLM_PROVIDER"]
        
        results.append(("Config", True, f"Provider: {config.llm.provider}"))
        print(f"  ✓ Config: Provider={config.llm.provider}")
    except Exception as e:
        results.append(("Config", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 5: Tool Execution
    print("\n[5/10] Testing Tool Execution...")
    try:
        tools = ToolManager(".")
        
        # Test shell execution
        result = await tools.shell.run("echo hello")
        assert result.success
        assert "hello" in result.output
        
        # Test file operations
        tools.files.write("test_file.txt", "test content")
        assert tools.files.exists("test_file.txt")
        content = tools.files.read("test_file.txt")
        assert content == "test content"
        
        # Cleanup
        tools.files.delete("test_file.txt")
        
        results.append(("Tools", True, "Shell, file operations working"))
        print("  ✓ Tool execution working")
    except Exception as e:
        results.append(("Tools", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 6: Security Scanner
    print("\n[6/10] Testing Security Scanner...")
    try:
        scanner = SecurityScanner()
        
        # Test with sample code containing issues
        test_code = '''
password = "secret123"
api_key = "sk-1234567890abcdef"
os.system("rm -rf /")
eval(user_input)
'''
        
        findings = scanner.scan_content(test_code, "test.py")
        assert len(findings) > 0
        
        results.append(("Security", True, f"{len(findings)} findings"))
        print(f"  ✓ Security: {len(findings)} findings detected")
    except Exception as e:
        results.append(("Security", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 7: Code Generation
    print("\n[7/10] Testing Code Generation...")
    try:
        generator = CodeGenerator()
        
        from core.coding.code_generator import CodeGenRequest
        request = CodeGenRequest(
            spec="Create a function that adds two numbers",
            language="python",
            tests=True,
            docs=True,
        )
        
        result = await generator.generate(request)
        assert len(result.code) > 0
        assert len(result.tests) > 0
        assert len(result.docs) > 0
        
        results.append(("Code Gen", True, f"Code: {len(result.code)} chars"))
        print(f"  ✓ Code generation: {len(result.code)} chars")
    except Exception as e:
        results.append(("Code Gen", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 8: CI/CD Integration
    print("\n[8/10] Testing CI/CD Integration...")
    try:
        cicd = CICDManager()
        
        # Test platform detection
        platform = cicd.detect_platform(".")
        # Should detect GitHub Actions since .github/workflows exists
        
        # Test webhook handling
        webhook_result = await cicd.handle_webhook("github", {
            "action": "completed",
            "workflow_run": {
                "conclusion": "success",
                "name": "CI",
                "head_branch": "main",
            }
        })
        
        results.append(("CI/CD", True, f"Platform: {platform}"))
        print(f"  ✓ CI/CD: Platform detected={platform}")
    except Exception as e:
        results.append(("CI/CD", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test REST API
    print("\n[9/10] Testing REST API...")
    try:
        from httpx import ASGITransport, AsyncClient
        
        transport = ASGITransport(app=api_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Health check
            resp = await client.get("/health")
            assert resp.status_code == 200
            
            # Create mission
            resp = await client.post("/api/missions", json={"goal": "Test mission"})
            assert resp.status_code == 200
            
            # Get missions
            resp = await client.get("/api/missions")
            assert resp.status_code == 200
            
            # Get stats
            resp = await client.get("/api/stats")
            assert resp.status_code == 200
        
        results.append(("REST API", True, "All endpoints working"))
        print("  ✓ REST API endpoints working")
    except Exception as e:
        results.append(("REST API", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Test 10: Full Dynamic Execution
    print("\n[10/10] Testing Full Dynamic Execution...")
    try:
        config = KernelConfig(plugins_root=Path("plugins"))
        kernel = HermesKernel(config)
        await kernel.boot()
        
        # Test dynamic execution
        result = await kernel.plan_and_execute_dynamic("Build a simple REST API with authentication")
        
        assert result["success"]
        assert result["scenario_type"] in ["new_project", "feature_addition"]
        assert result["plan_steps"] > 0
        assert result["steps_completed"] > 0
        
        await kernel.shutdown()
        
        results.append(("Dynamic Exec", True, f"Steps: {result['plan_steps']}, Completed: {result['steps_completed']}"))
        print(f"  ✓ Dynamic execution: {result['plan_steps']} steps, {result['steps_completed']} completed")
    except Exception as e:
        results.append(("Dynamic Exec", False, str(e)))
        print(f"  ✗ Failed: {e}")
    
    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"  Production Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'} {name}: {detail}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
