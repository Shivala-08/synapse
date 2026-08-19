"""Unit tests for IndustrialKnowledgeGraph enhanced methods.

Tests cover:
- search_nodes: search by name/type filtering
- get_node_metadata: full metadata with neighbors
- get_top_nodes: top N by degree
- get_subgraph_for_nodes: subgraph extraction

Run: python -m tests.test_knowledge_graph
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.graph.knowledge_graph as kg_module
from src.graph.knowledge_graph import IndustrialKnowledgeGraph, get_knowledge_graph


def setup_graph():
    """Create a fresh graph with test data.
    
    Uses load_from_disk=False to avoid contamination from stale database/JSON files.
    """
    # Reset the singleton to get a clean instance
    kg_module._kg = None
    kg = IndustrialKnowledgeGraph(load_from_disk=False)
    kg.clear()

    # Add equipment nodes
    for i in range(1, 6):
        kg.add_entity(f"EQ-{i:04d}", "equipment", doc_id="test_doc")
    
    # Add regulation nodes
    kg.add_entity("OISD-116", "regulation", doc_id="test_doc")
    kg.add_entity("OISD-118", "regulation", doc_id="test_doc")
    kg.add_entity("OISD-130", "regulation", doc_id="test_doc")
    
    # Add plant node
    kg.add_entity("REFINERY-A", "plant", doc_id="test_doc")
    
    # Add permit nodes
    kg.add_entity("PERMIT-001", "permit", doc_id="test_doc")
    kg.add_entity("PERMIT-002", "permit", doc_id="test_doc")
    
    # Add incident nodes
    kg.add_entity("INC-2025-001", "incident", doc_id="test_doc")
    kg.add_entity("INC-2025-002", "incident", doc_id="test_doc")
    
    # Add relationships
    kg.add_relationship("EQ-0001", "OISD-116", "subject_to")
    kg.add_relationship("EQ-0001", "REFINERY-A", "located_at")
    kg.add_relationship("EQ-0002", "OISD-116", "subject_to")
    kg.add_relationship("EQ-0002", "REFINERY-A", "located_at")
    kg.add_relationship("EQ-0003", "OISD-118", "subject_to")
    kg.add_relationship("EQ-0003", "REFINERY-A", "located_at")
    kg.add_relationship("EQ-0004", "OISD-130", "subject_to")
    kg.add_relationship("EQ-0004", "REFINERY-A", "located_at")
    kg.add_relationship("EQ-0005", "OISD-116", "subject_to")
    kg.add_relationship("EQ-0005", "OISD-118", "subject_to")
    kg.add_relationship("EQ-0005", "REFINERY-A", "located_at")
    kg.add_relationship("PERMIT-001", "EQ-0001", "issued_for")
    kg.add_relationship("PERMIT-001", "EQ-0002", "issued_for")
    kg.add_relationship("PERMIT-002", "EQ-0003", "issued_for")
    kg.add_relationship("INC-2025-001", "EQ-0001", "involved_equipment")
    kg.add_relationship("INC-2025-002", "EQ-0004", "involved_equipment")
    kg.add_relationship("INC-2025-001", "OISD-116", "references")
    
    return kg


def test_search_nodes():
    """Test search_nodes with various queries and filters."""
    print("=" * 60)
    print("Test: search_nodes")
    print("=" * 60)
    
    kg = setup_graph()
    
    # Test basic search
    results = kg.search_nodes("EQ-")
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    print(f"  ✓ Search 'EQ-': found {len(results)} results")
    
    # Test search with type filter
    results = kg.search_nodes("EQ-", node_types=["equipment"])
    assert len(results) == 5, f"Expected 5 equipment results, got {len(results)}"
    print(f"  ✓ Search 'EQ-' (equipment only): found {len(results)} results")
    
    # Test search with non-matching type filter
    results = kg.search_nodes("EQ-", node_types=["regulation"])
    assert len(results) == 0, f"Expected 0 results, got {len(results)}"
    print(f"  ✓ Search 'EQ-' (regulation only): found {len(results)} results (correct)")
    
    # Test search for regulations
    results = kg.search_nodes("OISD")
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    print(f"  ✓ Search 'OISD': found {len(results)} results")
    
    # Test case-insensitive search
    results = kg.search_nodes("oisd")
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    print(f"  ✓ Search 'oisd' (case-insensitive): found {len(results)} results")
    
    # Test limit
    results = kg.search_nodes("EQ-", limit=2)
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    print(f"  ✓ Search 'EQ-' (limit=2): found {len(results)} results")
    
    # Test no matches
    results = kg.search_nodes("NONEXISTENT")
    assert len(results) == 0, f"Expected 0 results, got {len(results)}"
    print(f"  ✓ Search 'NONEXISTENT': found {len(results)} results (correct)")
    
    # Test sort by degree (most connected first)
    results = kg.search_nodes("EQ-")
    degrees = [r["degree"] for r in results]
    assert degrees == sorted(degrees, reverse=True), "Results should be sorted by degree descending"
    # Verify most-connected node is first (EQ-0001 has degree 4: OISD-116, REFINERY-A, PERMIT-001, INC-2025-001)
    assert results[0]["id"] == "EQ-0001", f"Expected EQ-0001 first (degree 4), got {results[0]['id']}"
    print(f"  ✓ Results sorted by degree: {degrees}")
    
    print("\n✓ ALL search_nodes TESTS PASSED\n")


def test_get_node_metadata():
    """Test get_node_metadata for various node types."""
    print("=" * 60)
    print("Test: get_node_metadata")
    print("=" * 60)
    
    kg = setup_graph()
    
    # Test metadata for a well-connected node (EQ-0005 has 3 connections: OISD-116, OISD-118, REFINERY-A)
    meta = kg.get_node_metadata("EQ-0005")
    assert meta["id"] == "EQ-0005", f"Expected id EQ-0005, got {meta['id']}"
    assert meta["type"] == "equipment", f"Expected type equipment, got {meta['type']}"
    assert meta["degree"] == 3, f"Expected degree 3, got {meta['degree']}"
    assert meta["neighbor_count"] == 3, f"Expected 3 neighbors, got {meta['neighbor_count']}"
    assert len(meta["neighbors"]) == 3, f"Expected 3 neighbors in list, got {len(meta['neighbors'])}"
    print(f"  ✓ EQ-0005: type={meta['type']}, degree={meta['degree']}, neighbors={meta['neighbor_count']}")
    
    # Test neighbor types grouping (EQ-0005 neighbors: OISD-116, OISD-118, REFINERY-A)
    neighbor_types = meta["neighbor_types"]
    assert "regulation" in neighbor_types, "Expected regulation in neighbor_types"
    assert "plant" in neighbor_types, "Expected plant in neighbor_types"
    assert len(neighbor_types["regulation"]) == 2, f"Expected 2 regulation neighbors, got {len(neighbor_types.get('regulation', []))}"
    assert len(neighbor_types["plant"]) == 1, f"Expected 1 plant neighbor, got {len(neighbor_types.get('plant', []))}"
    print(f"  ✓ EQ-0005 neighbor types: {list(neighbor_types.keys())}")
    
    # Test metadata for non-existent node
    meta = kg.get_node_metadata("NONEXISTENT")
    assert "error" in meta, "Expected error for non-existent node"
    print(f"  ✓ Non-existent node returns error: {meta['error']}")
    
    # Test metadata for permit node
    meta = kg.get_node_metadata("PERMIT-001")
    assert meta["type"] == "permit", f"Expected type permit, got {meta['type']}"
    assert meta["degree"] == 2, f"Expected degree 2, got {meta['degree']}"
    print(f"  ✓ PERMIT-001: type={meta['type']}, degree={meta['degree']}")
    
    # Test metadata includes doc_id
    meta = kg.get_node_metadata("EQ-0001")
    assert meta.get("doc_id") == "test_doc", f"Expected doc_id test_doc, got {meta.get('doc_id')}"
    print(f"  ✓ EQ-0001 doc_id: {meta.get('doc_id')}")
    
    print("\n✓ ALL get_node_metadata TESTS PASSED\n")


def test_get_top_nodes():
    """Test get_top_nodes returns most-connected nodes."""
    print("=" * 60)
    print("Test: get_top_nodes")
    print("=" * 60)
    
    kg = setup_graph()
    
    # Test top 7 nodes (REFINERY-A deg 5, EQ-0001 deg 4, OISD-116 deg 4, four equipment deg 3)
    top = kg.get_top_nodes(n=7)
    assert len(top) == 7, f"Expected 7 nodes, got {len(top)}"
    # REFINERY-A (degree 5) and EQ-0001 (degree 4) must be in top
    assert "REFINERY-A" in top, "REFINERY-A should be in top 7 (degree 5)"
    assert "EQ-0001" in top, "EQ-0001 should be in top 7 (degree 4)"
    # All 5 equipment nodes should be present (degree 3 each)
    for i in range(1, 6):
        assert f"EQ-{i:04d}" in top, f"EQ-{i:04d} should be in top 7 (degree 3)"
    print(f"  ✓ Top 7: {top}")
    
    # Test with type filter
    top_equipment = kg.get_top_nodes(n=5, node_types=["equipment"])
    assert len(top_equipment) == 5, f"Expected 5 equipment nodes, got {len(top_equipment)}"
    for nid in top_equipment:
        assert kg.graph.nodes[nid].get("type") == "equipment", f"Expected equipment type for {nid}"
    print(f"  ✓ Top 5 equipment: {top_equipment}")
    
    # Test with regulation filter
    top_regulations = kg.get_top_nodes(n=5, node_types=["regulation"])
    assert len(top_regulations) == 3, f"Expected 3 regulation nodes, got {len(top_regulations)}"
    print(f"  ✓ Top regulations: {top_regulations}")
    
    # Test requesting more nodes than exist
    top_all = kg.get_top_nodes(n=100)
    total_nodes = kg.graph.number_of_nodes()
    assert len(top_all) == total_nodes, f"Expected {total_nodes} nodes, got {len(top_all)}"
    print(f"  ✓ Request 100 (have {total_nodes}): returned {len(top_all)}")
    
    print("\n✓ ALL get_top_nodes TESTS PASSED\n")


def test_get_subgraph_for_nodes():
    """Test get_subgraph_for_nodes extracts correct subgraph."""
    print("=" * 60)
    print("Test: get_subgraph_for_nodes")
    print("=" * 60)
    
    kg = setup_graph()
    
    # Test subgraph with 3 nodes
    subgraph = kg.get_subgraph_for_nodes(["EQ-0001", "EQ-0002", "REFINERY-A"])
    assert len(subgraph["nodes"]) == 3, f"Expected 3 nodes, got {len(subgraph['nodes'])}"
    assert len(subgraph["edges"]) == 2, f"Expected 2 edges, got {len(subgraph['edges'])}"
    print(f"  ✓ 3-node subgraph: {len(subgraph['nodes'])} nodes, {len(subgraph['edges'])} edges")
    
    # Test subgraph with disconnected nodes
    subgraph = kg.get_subgraph_for_nodes(["EQ-0001", "OISD-130"])
    assert len(subgraph["nodes"]) == 2, f"Expected 2 nodes, got {len(subgraph['nodes'])}"
    assert len(subgraph["edges"]) == 0, f"Expected 0 edges, got {len(subgraph['edges'])}"
    print(f"  ✓ Disconnected subgraph: {len(subgraph['nodes'])} nodes, {len(subgraph['edges'])} edges")
    
    # Test subgraph with non-existent nodes
    subgraph = kg.get_subgraph_for_nodes(["NONEXISTENT"])
    assert len(subgraph["nodes"]) == 0, f"Expected 0 nodes, got {len(subgraph['nodes'])}"
    print(f"  ✓ Non-existent node subgraph: {len(subgraph['nodes'])} nodes")
    
    # Test subgraph includes correct edge relations
    subgraph = kg.get_subgraph_for_nodes(["PERMIT-001", "EQ-0001", "EQ-0002"])
    assert len(subgraph["nodes"]) == 3, f"Expected 3 nodes, got {len(subgraph['nodes'])}"
    # Should have 2 edges: PERMIT-001 -> EQ-0001, PERMIT-001 -> EQ-0002
    assert len(subgraph["edges"]) == 2, f"Expected 2 edges, got {len(subgraph['edges'])}"
    relations = {e["relation"] for e in subgraph["edges"]}
    assert "issued_for" in relations, f"Expected 'issued_for' relation, got {relations}"
    print(f"  ✓ Permit subgraph edges: {subgraph['edges']}")
    
    # Test subgraph node metadata
    subgraph = kg.get_subgraph_for_nodes(["EQ-0005", "OISD-116", "OISD-118"])
    node_types = {n["id"]: n["type"] for n in subgraph["nodes"]}
    assert node_types["EQ-0005"] == "equipment", f"Expected equipment type, got {node_types['EQ-0005']}"
    assert node_types["OISD-116"] == "regulation", f"Expected regulation type, got {node_types['OISD-116']}"
    print(f"  ✓ Node types in subgraph: {node_types}")
    
    print("\n✓ ALL get_subgraph_for_nodes TESTS PASSED\n")


def test_to_json():
    """Test to_json still works correctly."""
    print("=" * 60)
    print("Test: to_json")
    print("=" * 60)
    
    kg = setup_graph()
    
    # Test full export
    data = kg.to_json(max_nodes=100)
    assert "nodes" in data, "Expected nodes in output"
    assert "edges" in data, "Expected edges in output"
    assert len(data["nodes"]) == 13, f"Expected 13 nodes, got {len(data['nodes'])}"
    print(f"  ✓ Full export: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
    
    # Test with limit
    data = kg.to_json(max_nodes=3)
    assert len(data["nodes"]) <= 3, f"Expected <=3 nodes, got {len(data['nodes'])}"
    print(f"  ✓ Limited export: {len(data['nodes'])} nodes")
    
    # Verify node structure
    node = data["nodes"][0]
    assert "id" in node, "Expected 'id' in node"
    assert "type" in node, "Expected 'type' in node"
    assert "color" in node, "Expected 'color' in node"
    print(f"  ✓ Node structure: {list(node.keys())}")
    
    print("\n✓ ALL to_json TESTS PASSED\n")


def test_get_entities_by_type():
    """Test get_entities_by_type groups entities correctly."""
    print("=" * 60)
    print("Test: get_entities_by_type")
    print("=" * 60)
    
    kg = setup_graph()
    
    entities = kg.get_entities_by_type()
    assert "equipment" in entities, "Expected 'equipment' type"
    assert "regulation" in entities, "Expected 'regulation' type"
    assert "permit" in entities, "Expected 'permit' type"
    assert "incident" in entities, "Expected 'incident' type"
    assert "plant" in entities, "Expected 'plant' type"
    
    assert len(entities["equipment"]) == 5, f"Expected 5 equipment entities, got {len(entities['equipment'])}"
    assert len(entities["regulation"]) == 3, f"Expected 3 regulation entities, got {len(entities['regulation'])}"
    assert len(entities["permit"]) == 2, f"Expected 2 permit entities, got {len(entities['permit'])}"
    assert len(entities["incident"]) == 2, f"Expected 2 incident entities, got {len(entities['incident'])}"
    assert len(entities["plant"]) == 1, f"Expected 1 plant entity, got {len(entities['plant'])}"
    
    print(f"  ✓ Entity types: {list(entities.keys())}")
    for etype, elist in entities.items():
        print(f"    {etype}: {len(elist)} entities")
    
    print("\n✓ ALL get_entities_by_type TESTS PASSED\n")


def test_add_entity_completes_auto_created_node():
    """Regression: a node auto-created by add_edge must get typed when add_entity runs later."""
    print("=" * 60)
    print("Test: add_entity completes auto-created node")
    print("=" * 60)

    kg = setup_graph()

    # Simulate a relationship created before the regulation node was added
    kg.graph.add_edge("EQ-0001", "NEW-REG", relation="subject_to")
    assert "type" not in kg.graph.nodes["NEW-REG"]

    kg.add_entity("NEW-REG", "regulation", doc_id="test_doc")
    assert kg.graph.nodes["NEW-REG"]["type"] == "regulation"
    assert kg.graph.nodes["NEW-REG"]["color"] == kg_module.NODE_COLORS["regulation"]
    assert kg.graph.nodes["NEW-REG"].get("doc_id") == "test_doc"
    print(f"  ✓ NEW-REG completed: type={kg.graph.nodes['NEW-REG']['type']}, "
          f"color={kg.graph.nodes['NEW-REG']['color']}")

    print("\n✓ ALL add_entity completion TESTS PASSED\n")


def test_get_stats():
    """Test get_stats returns correct statistics."""
    print("=" * 60)
    print("Test: get_stats")
    print("=" * 60)
    
    kg = setup_graph()
    
    stats = kg.get_stats()
    assert stats["total_nodes"] == 13, f"Expected 13 nodes, got {stats['total_nodes']}"
    # Note: add_relationship deduplicates edges, so actual count may differ
    # from the number of add_relationship calls
    assert stats["total_edges"] >= 10, f"Expected >=10 edges, got {stats['total_edges']}"
    assert stats["density"] > 0, f"Expected positive density, got {stats['density']}"
    assert "equipment" in stats["node_types"], "Expected 'equipment' in node_types"
    assert stats["node_types"]["equipment"] == 5, f"Expected 5 equipment, got {stats['node_types']['equipment']}"
    
    print(f"  ✓ Nodes: {stats['total_nodes']}")
    print(f"  ✓ Edges: {stats['total_edges']}")
    print(f"  ✓ Density: {stats['density']}")
    print(f"  ✓ Node types: {stats['node_types']}")
    
    print("\n✓ ALL get_stats TESTS PASSED\n")


if __name__ == "__main__":
    test_search_nodes()
    test_get_node_metadata()
    test_get_top_nodes()
    test_get_subgraph_for_nodes()
    test_to_json()
    test_get_entities_by_type()
    test_add_entity_completes_auto_created_node()
    test_get_stats()
    
    print("=" * 60)
    print("✓ ALL KNOWLEDGE GRAPH TESTS PASSED")
    print("=" * 60)
