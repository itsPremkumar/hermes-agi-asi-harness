"""Test v11 Coding Intelligence — Full Integration."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v11 — Coding Intelligence Tests")
    print(f"{'='*60}")

    results = []

    # Test 1: Repository Twin
    print("\n[1/12] Repository Digital Twin...")
    try:
        from core.coding import RepositoryDigitalTwin
        twin = RepositoryDigitalTwin(".")
        twin.discover()
        stats = twin.get_stats()
        assert stats["total_files"] > 0
        assert stats["total_symbols"] > 0
        results.append(("Repository Twin", True, f"files={stats['total_files']}, symbols={stats['total_symbols']}"))
        print(f"  ✓ {stats['total_files']} files, {stats['total_symbols']} symbols")
    except Exception as e:
        results.append(("Repository Twin", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 2: Code Graph
    print("\n[2/12] Code Graph...")
    try:
        from core.coding import CodeGraph, NodeType, RelationType
        graph = CodeGraph()
        n1 = graph.add_node("module_a", NodeType.MODULE, "a.py")
        n2 = graph.add_node("module_b", NodeType.MODULE, "b.py")
        graph.add_edge(n1.id, n2.id, RelationType.IMPORTS)
        blast = graph.compute_blast_radius(n1.id)
        assert len(blast.affected_nodes) > 0
        results.append(("Code Graph", True, f"nodes={len(graph.nodes)}, blast={len(blast.affected_nodes)}"))
        print(f"  ✓ {len(graph.nodes)} nodes, blast_radius={len(blast.affected_nodes)}")
    except Exception as e:
        results.append(("Code Graph", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 3: Semantic Index
    print("\n[3/12] Semantic Index...")
    try:
        from core.coding import SearchQuery, SemanticCodeIndex
        idx = SemanticCodeIndex()
        chunks = idx.index_file("test.py", "class Foo:\n    def bar(self):\n        pass\n")
        results_foo = idx.search(SearchQuery(text="Foo"))
        assert len(chunks) > 0
        assert len(results_foo) > 0
        results.append(("Semantic Index", True, f"chunks={len(chunks)}, results={len(results_foo)}"))
        print(f"  ✓ {len(chunks)} chunks, {len(results_foo)} search results")
    except Exception as e:
        results.append(("Semantic Index", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 4: Recon
    print("\n[4/12] Repository Recon...")
    try:
        from core.coding import ReconStage, RepositoryRecon
        recon = RepositoryRecon()
        result = recon.run(".")
        assert result.stage == ReconStage.COMPLETED
        assert len(result.files) > 0
        results.append(("Recon", True, f"build={result.build_system}, ci={len(result.ci_platform)}"))
        print(f"  ✓ {result.build_system}, {result.test_framework}, {len(result.files)} files")
    except Exception as e:
        results.append(("Recon", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 5: Requirements Compiler
    print("\n[5/12] Requirements Compiler...")
    try:
        from core.coding import RequirementsCompiler
        compiler = RequirementsCompiler()
        compiled = compiler.compile("The system must handle 1000 requests per second. It should be secure against SQL injection.")
        assert len(compiled.functional) > 0 or len(compiled.all_requirements) > 0
        results.append(("Requirements", True, f"total={len(compiled.all_requirements)}"))
        print(f"  ✓ {len(compiled.all_requirements)} requirements compiled")
    except Exception as e:
        results.append(("Requirements", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 6: Architecture Synthesizer
    print("\n[6/12] Architecture Synthesis...")
    try:
        from core.coding import ArchitectureSynthesizer
        synth = ArchitectureSynthesizer()
        candidates = synth.generate_candidates({"scale": 0.8, "event_driven": True})
        best = synth.select_best()
        assert len(candidates) > 0
        assert best is not None
        results.append(("Architecture", True, f"candidates={len(candidates)}, best={best.style.value}"))
        print(f"  ✓ {len(candidates)} candidates, best={best.style.value}")
    except Exception as e:
        results.append(("Architecture", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 7: ADR Registry
    print("\n[7/12] ADR Registry...")
    try:
        from core.coding import ADRRegistry
        reg = ADRRegistry()
        adr = reg.create(
            title="Use PostgreSQL",
            problem="Need a relational database",
            constraints=["Must be ACID compliant"],
            alternatives=[{"name": "PostgreSQL"}, {"name": "MySQL"}],
            chosen="PostgreSQL",
            rejected=["MySQL"],
            evidence="Best JSONB support",
            consequences=["Single database to manage"],
        )
        reg.accept(adr.id)
        assert len(reg.get_accepted()) == 1
        results.append(("ADR Registry", True, f"total={len(reg.get_all())}"))
        print(f"  ✓ ADR created: {adr.title}")
    except Exception as e:
        results.append(("ADR Registry", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 8: Task Graph
    print("\n[8/12] Task Graph...")
    try:
        from core.coding import TaskGraph
        tg = TaskGraph()
        t1 = tg.add_task("Design", "Design the system", priority=10)
        t2 = tg.add_task("Implement", "Implement the system", dependencies=[t1.id], priority=5)
        tg.add_task("Test", "Test the system", dependencies=[t2.id], priority=3)
        ready = tg.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == t1.id
        results.append(("Task Graph", True, f"tasks={len(tg.tasks)}, ready={len(ready)}"))
        print(f"  ✓ {len(tg.tasks)} tasks, {len(ready)} ready")
    except Exception as e:
        results.append(("Task Graph", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 9: Quality Gates
    print("\n[9/12] Quality Gates...")
    try:
        from core.coding import Gate, QualityGates
        qg = QualityGates()
        qg.pass_gate(Gate.REQUIREMENT)
        qg.pass_gate(Gate.ARCHITECTURE)
        qg.pass_gate(Gate.IMPLEMENTATION)
        qg.pass_gate(Gate.TEST)
        qg.pass_gate(Gate.SECURITY)
        qg.pass_gate(Gate.DEPLOYMENT)
        qg.pass_gate(Gate.PRODUCTION)
        assert qg.all_passed()
        results.append(("Quality Gates", True, "passed=7/7"))
        print("  ✓ All gates passed")
    except Exception as e:
        results.append(("Quality Gates", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 10: Merge Controller
    print("\n[10/12] Merge Controller...")
    try:
        from core.coding import MergeController
        mc = MergeController()
        mc.set_check("tests_passed", True)
        mc.set_check("security_passed", True)
        mc.set_check("review_passed", True)
        mc.set_check("conflicts_resolved", True)
        mc.set_check("architecture_approved", True)
        mc.set_check("rollback_known", True)
        mc.set_check("requirements_satisfied", True)
        assert mc.can_merge()
        results.append(("Merge Controller", True, f"can_merge={mc.can_merge()}"))
        print(f"  ✓ Merge controller: can_merge={mc.can_merge()}")
    except Exception as e:
        results.append(("Merge Controller", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 11: Evaluation Pyramid
    print("\n[11/12] Evaluation Pyramid...")
    try:
        from core.coding import EvalLevel, EvaluationPyramid
        ep = EvaluationPyramid()
        ep.evaluate_level(EvalLevel.UNIT, 0.9)
        ep.evaluate_level(EvalLevel.INTEGRATION, 0.8)
        ep.evaluate_level(EvalLevel.REPOSITORY, 0.7)
        ep.evaluate_level(EvalLevel.LONG_HORIZON, 0.5)
        weakest = ep.get_weakest_level()
        assert weakest == "long_horizon"
        results.append(("Eval Pyramid", True, f"weakest={weakest}"))
        print(f"  ✓ Weakest level: {weakest}")
    except Exception as e:
        results.append(("Eval Pyramid", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Test 12: Full Integration
    print("\n[12/12] Full v11 Integration...")
    try:
        from core.coding import (
            ArchitectureSynthesizer,
            CodeGraph,
            Gate,
            QualityGates,
            RepositoryRecon,
            RequirementsCompiler,
            SemanticCodeIndex,
            TaskGraph,
        )
        
        # Full workflow
        recon = RepositoryRecon()
        recon_result = recon.run(".")
        
        compiler = RequirementsCompiler()
        compiled = compiler.compile("Build a REST API with authentication")
        
        synth = ArchitectureSynthesizer()
        candidates = synth.generate_candidates({"scale": 0.5})
        best_arch = synth.select_best()
        
        tg = TaskGraph()
        design_task = tg.add_task("Design", "Design architecture", priority=10)
        tg.add_task("Implement", "Write code", dependencies=[design_task.id])
        
        graph = CodeGraph()
        idx = SemanticCodeIndex()
        
        qg = QualityGates()
        
        assert recon_result.stage.value == "completed"
        assert len(compiled.all_requirements) > 0
        assert best_arch is not None
        assert len(tg.tasks) == 2
        
        results.append(("Full Integration", True, "all modules wired"))
        print("  ✓ Full v11 workflow completed successfully")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Full Integration", False, str(e)[:80]))
        print(f"  ✗ {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  v11 Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
