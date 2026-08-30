"""Test Repository Intelligence Layer."""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print("\n=== Phase 1: Repository Intelligence Tests ===\n")
    results = []
    
    # Test Repository Twin
    print("[1/4] Repository Digital Twin...")
    try:
        from core.coding.repository_twin import RepositoryDigitalTwin, SymbolType
        
        twin = RepositoryDigitalTwin(".")
        twin.discover()
        
        stats = twin.get_stats()
        assert stats["total_files"] > 0
        assert stats["total_symbols"] > 0
        
        results.append(("Repository Twin", True, f"files={stats['total_files']}, symbols={stats['total_symbols']}"))
        print(f"  ✓ Twin: {stats['total_files']} files, {stats['total_symbols']} symbols")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Repository Twin", False, str(e)[:80]))
        print(f"  ✗ {e}")
    
    # Test Code Graph
    print("\n[2/4] Code Graph...")
    try:
        from core.coding.code_graph import CodeGraph, NodeType, RelationType
        
        graph = CodeGraph()
        n1 = graph.add_node("module_a", NodeType.MODULE, "a.py")
        n2 = graph.add_node("module_b", NodeType.MODULE, "b.py")
        n3 = graph.add_node("ClassA", NodeType.CLASS, "a.py")
        
        graph.add_edge(n1.id, n2.id, RelationType.IMPORTS)
        graph.add_edge(n3.id, n1.id, RelationType.DEPENDS_ON)
        
        blast = graph.compute_blast_radius(n1.id)
        assert len(blast.affected_nodes) > 0
        
        state = graph.get_state()
        results.append(("Code Graph", True, f"nodes={state['nodes']}, edges={state['edges']}"))
        print(f"  ✓ Graph: {state['nodes']} nodes, blast_radius={len(blast.affected_nodes)}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Code Graph", False, str(e)[:80]))
        print(f"  ✗ {e}")
    
    # Test Semantic Index
    print("\n[3/4] Semantic Index...")
    try:
        from core.coding.semantic_index import SemanticCodeIndex, IndexLevel, SearchQuery
        
        idx = SemanticCodeIndex()
        
        sample_code = """
class MyClass:
    def my_method(self):
        pass

def my_function():
    return 42
"""
        chunks = idx.index_file("test.py", sample_code)
        assert len(chunks) > 0
        
        query = SearchQuery(text="my_method")
        search_results = idx.search(query)
        assert len(search_results) > 0
        assert hasattr(search_results[0], 'chunk')
        
        state = idx.get_state()
        results.append(("Semantic Index", True, f"chunks={state['chunks']}, symbols={state['symbols']}"))
        print(f"  ✓ Index: {state['chunks']} chunks, {state['symbols']} symbols")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Semantic Index", False, str(e)[:80]))
        print(f"  ✗ {e}")
    
    # Test Recon
    print("\n[4/4] Repository Recon...")
    try:
        from core.coding.recon import RepositoryRecon, ReconStage
        
        recon = RepositoryRecon()
        result = recon.run(".")
        
        assert result.stage == ReconStage.COMPLETED
        assert len(result.files) > 0
        assert result.build_system != ""
        
        results.append(("Recon", True, f"build={result.build_system}, files={len(result.files)}"))
        print(f"  ✓ Recon: {result.build_system}, {result.test_framework}, {len(result.files)} files")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Recon", False, str(e)[:80]))
        print(f"  ✗ {e}")
    
    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n=== Phase 1: {passed}/{total} passed ===")
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'}: {name}: {detail}")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
