"""Knowledge graph builder using NetworkX for industrial entities.

Builds a graph from extracted entities with typed nodes and relationships.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger
import networkx as nx

from src.config import settings


# Node type colors for visualization
NODE_COLORS = {
    "equipment": "#3b82f6",      # blue
    "regulation": "#ef4444",     # red
    "plant": "#10b981",          # green
    "permit": "#f59e0b",         # amber
    "work_order": "#8b5cf6",     # purple
    "incident": "#ec4899",       # pink
    "inspection": "#06b6d4",     # cyan
    "person": "#f97316",         # orange
    "hazard": "#dc2626",         # dark red
    "permit_type": "#d97706",    # dark amber
    "incident_type": "#db2777",  # dark pink
}


class IndustrialKnowledgeGraph:
    """NetworkX-based knowledge graph for industrial entities."""

    def __init__(self, load_from_disk: bool = True):
        self.graph = nx.Graph()
        self.graph_file = settings.data_dir / "knowledge_graph.json"
        if load_from_disk:
            self._load()

    def _load(self):
        """Load graph from disk if it exists."""
        if self.graph_file.exists():
            try:
                data = json.loads(self.graph_file.read_text(encoding="utf-8"))
                self.graph = nx.node_link_graph(data, edges="edges")
                logger.info(f"Loaded knowledge graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            except Exception as e:
                logger.warning(f"Could not load graph, starting fresh: {e}")
                self.graph = nx.Graph()
        else:
            logger.info("Starting with empty knowledge graph")

    def save(self):
        """Persist graph to disk."""
        try:
            self.graph_file.parent.mkdir(parents=True, exist_ok=True)
            data = nx.node_link_data(self.graph, edges="edges")
            self.graph_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Saved knowledge graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        except Exception as e:
            logger.error(f"Failed to save knowledge graph: {e}")

    def add_entity(self, entity_id: str, entity_type: str, **attrs):
        """Add an entity node to the graph."""
        if self.graph.has_node(entity_id):
            # Node may already exist (e.g. auto-created by add_edge before its
            # add_entity call); complete missing type/color attributes so it is
            # not rendered as 'unknown' in the UI.
            node = self.graph.nodes[entity_id]
            if "type" not in node:
                node["type"] = entity_type
                node.setdefault("color", NODE_COLORS.get(entity_type, "#6b7280"))
            for k, v in attrs.items():
                node.setdefault(k, v)
            return
        self.graph.add_node(
            entity_id,
            type=entity_type,
            color=NODE_COLORS.get(entity_type, "#6b7280"),
            **attrs,
        )

    def add_relationship(self, source: str, target: str, relation: str, **attrs):
        """Add a relationship edge between two entities."""
        if not self.graph.has_edge(source, target):
            self.graph.add_edge(source, target, relation=relation, **attrs)

    def add_document_entities(self, doc_id: str, text: str, entities: dict, metadata: Optional[dict] = None):
        """Add all entities from a document to the graph and create relationships.

        Args:
            doc_id: Document identifier.
            text: Full text content of the document.
            entities: Entity dict from EntityExtractor.extract_all().
            metadata: Optional metadata dict.
        """
        metadata = metadata or {}
        added_nodes = 0
        added_edges = 0

        # 1. Add equipment nodes and relationships
        for eq_tag in entities.get("equipment", []):
            self.add_entity(eq_tag, "equipment", doc_id=doc_id)
            added_nodes += 1

            # Equipment -> Regulation
            for reg in entities.get("regulations", []):
                self.add_relationship(eq_tag, reg, "subject_to")
                added_edges += 1

            # Equipment -> Plant
            for plant in entities.get("plants", []):
                self.add_relationship(eq_tag, plant, "located_at")
                added_edges += 1

            # Equipment -> Hazard
            for hazard in entities.get("hazards", []):
                self.add_relationship(eq_tag, hazard, "has_hazard")
                added_edges += 1

        # 2. Add regulation nodes and cross-relationships
        for reg in entities.get("regulations", []):
            self.add_entity(reg, "regulation", doc_id=doc_id)
            added_nodes += 1

            # Regulation -> Plant
            for plant in entities.get("plants", []):
                self.add_relationship(reg, plant, "applies_to")
                added_edges += 1

        # 3. Add plant nodes
        for plant in entities.get("plants", []):
            self.add_entity(plant, "plant", doc_id=doc_id)
            added_nodes += 1

        # 4. Add permit nodes and relationships
        for permit_id in entities.get("permits", []):
            self.add_entity(permit_id, "permit", doc_id=doc_id, permit_type=metadata.get("permit_type", ""))
            added_nodes += 1

            for eq_tag in entities.get("equipment", []):
                self.add_relationship(permit_id, eq_tag, "issued_for")
                added_edges += 1

            for pt in entities.get("permit_types", []):
                self.add_entity(pt, "permit_type", doc_id=doc_id)
                self.add_relationship(permit_id, pt, "is_type")
                added_edges += 1

        # 5. Add work order nodes and relationships
        for wo_id in entities.get("work_orders", []):
            self.add_entity(wo_id, "work_order", doc_id=doc_id)
            added_nodes += 1

            for eq_tag in entities.get("equipment", []):
                self.add_relationship(wo_id, eq_tag, "assigned_to")
                added_edges += 1

            for reg in entities.get("regulations", []):
                self.add_relationship(wo_id, reg, "references")
                added_edges += 1

        # 6. Add incident nodes and relationships
        for inc_id in entities.get("incidents", []):
            self.add_entity(inc_id, "incident", doc_id=doc_id)
            added_nodes += 1

            for eq_tag in entities.get("equipment", []):
                self.add_relationship(inc_id, eq_tag, "involved_equipment")
                added_edges += 1

            for it in entities.get("incident_types", []):
                self.add_entity(it, "incident_type", doc_id=doc_id)
                self.add_relationship(inc_id, it, "is_type")
                added_edges += 1

        # 7. Add inspection nodes and relationships
        for insp_id in entities.get("inspections", []):
            self.add_entity(insp_id, "inspection", doc_id=doc_id)
            added_nodes += 1

            for eq_tag in entities.get("equipment", []):
                self.add_relationship(insp_id, eq_tag, "inspected")
                added_edges += 1

        # 8. Add person nodes and relationships
        for person in entities.get("personnel", []):
            self.add_entity(person, "person", doc_id=doc_id)
            added_nodes += 1

            for eq_tag in entities.get("equipment", []):
                self.add_relationship(person, eq_tag, "works_with")
                added_edges += 1

        # 9. Hazard cross-relationships
        for hazard in entities.get("hazards", []):
            self.add_entity(hazard, "hazard", doc_id=doc_id)
            added_nodes += 1

            for reg in entities.get("regulations", []):
                self.add_relationship(hazard, reg, "regulated_by")
                added_edges += 1

        logger.info(f"Added {added_nodes} nodes, {added_edges} edges from document {doc_id}")

    def get_entity_neighbors(self, entity_id: str, depth: int = 1) -> dict:
        """Get neighbors of an entity up to a given depth.

        Returns:
            Dict with center entity and its neighbors with relationships.
        """
        if not self.graph.has_node(entity_id):
            return {"center": entity_id, "neighbors": [], "error": f"Entity '{entity_id}' not found"}

        center = {
            "id": entity_id,
            "type": self.graph.nodes[entity_id].get("type", "unknown"),
            "color": self.graph.nodes[entity_id].get("color", "#6b7280"),
        }

        neighbors = []
        visited = {entity_id}

        current_level = [entity_id]
        for _ in range(depth):
            next_level = []
            for node in current_level:
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        edge_data = self.graph.edges[node, neighbor]
                        neighbors.append({
                            "id": neighbor,
                            "type": self.graph.nodes[neighbor].get("type", "unknown"),
                            "color": self.graph.nodes[neighbor].get("color", "#6b7280"),
                            "relation": edge_data.get("relation", "related_to"),
                            "source": node,
                        })
                        next_level.append(neighbor)
            current_level = next_level

        return {"center": center, "neighbors": neighbors}

    def to_json(self, max_nodes: int = 500) -> dict:
        """Export graph as nodes/edges JSON for visualization.

        Args:
            max_nodes: Maximum number of nodes to return (for performance).

        Returns:
            Dict with nodes and edges arrays.
        """
        # Sort nodes by type for better visualization
        node_list = []
        for node_id, attrs in self.graph.nodes(data=True):
            node_list.append({
                "id": node_id,
                "label": node_id,
                "type": attrs.get("type", "unknown"),
                "color": attrs.get("color", "#6b7280"),
                "size": self.graph.degree(node_id) + 5,
            })

        # Limit nodes if graph is too large
        if len(node_list) > max_nodes:
            # Keep nodes with highest degree
            node_list.sort(key=lambda x: x["size"], reverse=True)
            kept_ids = {n["id"] for n in node_list[:max_nodes]}
            node_list = node_list[:max_nodes]
        else:
            kept_ids = {n["id"] for n in node_list}

        # Build edges (only include edges between kept nodes)
        edge_list = []
        for u, v, attrs in self.graph.edges(data=True):
            if u in kept_ids and v in kept_ids:
                edge_list.append({
                    "from": u,
                    "to": v,
                    "relation": attrs.get("relation", "related_to"),
                })

        return {"nodes": node_list, "edges": edge_list}

    def get_entities_by_type(self) -> dict:
        """Get all entities grouped by type.

        Returns:
            Dict mapping entity type -> list of entity IDs.
        """
        result = {}
        for node_id, attrs in self.graph.nodes(data=True):
            etype = attrs.get("type", "unknown")
            if etype not in result:
                result[etype] = []
            result[etype].append(node_id)
        # Sort each list
        for key in result:
            result[key].sort()
        return result

    def search_nodes(self, query: str, node_types: Optional[list] = None, limit: int = 50) -> list:
        """Search for nodes by name/label matching the query string.

        Args:
            query: Search term to match against node IDs.
            node_types: Optional list of node types to filter by.
            limit: Maximum number of results to return.

        Returns:
            List of matching node dicts with id, type, color, degree.
        """
        query_lower = query.lower()
        matches = []

        for node_id, attrs in self.graph.nodes(data=True):
            etype = attrs.get("type", "unknown")

            # Filter by type if specified
            if node_types and etype not in node_types:
                continue

            # Match query against node ID (case-insensitive)
            if query_lower in node_id.lower():
                matches.append({
                    "id": node_id,
                    "type": etype,
                    "color": attrs.get("color", "#6b7280"),
                    "degree": self.graph.degree(node_id),
                })

        # Sort by degree (most connected first)
        matches.sort(key=lambda x: x["degree"], reverse=True)
        return matches[:limit]

    def get_node_metadata(self, node_id: str) -> dict:
        """Get full metadata for a node including neighbors and linked resources.

        Returns:
            Dict with node info, neighbors, doc_id, and chunk references.
        """
        if not self.graph.has_node(node_id):
            return {"error": f"Node '{node_id}' not found"}

        attrs = self.graph.nodes[node_id]

        # Get immediate neighbors
        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]
            neighbors.append({
                "id": neighbor,
                "type": self.graph.nodes[neighbor].get("type", "unknown"),
                "color": self.graph.nodes[neighbor].get("color", "#6b7280"),
                "relation": edge_data.get("relation", "related_to"),
            })

        # Get connected entities by type
        neighbor_types = {}
        for n in neighbors:
            ntype = n["type"]
            if ntype not in neighbor_types:
                neighbor_types[ntype] = []
            neighbor_types[ntype].append(n["id"])

        return {
            "id": node_id,
            "type": attrs.get("type", "unknown"),
            "color": attrs.get("color", "#6b7280"),
            "doc_id": attrs.get("doc_id", None),
            "degree": self.graph.degree(node_id),
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "neighbor_types": neighbor_types,
        }

    def get_top_nodes(self, n: int = 30, node_types: Optional[list] = None) -> list:
        """Get top N most-connected nodes for initial graph loading.

        Args:
            n: Number of top nodes to return.
            node_types: Optional filter by node types.

        Returns:
            List of top node IDs sorted by degree.
        """
        # Compute degrees once (O(V)) instead of per-node (O(V * degree))
        all_degrees = dict(self.graph.degree())
        
        # Filter by type if specified
        if node_types:
            node_degrees = [
                (node_id, all_degrees[node_id])
                for node_id, attrs in self.graph.nodes(data=True)
                if attrs.get("type", "unknown") in node_types
            ]
        else:
            node_degrees = list(all_degrees.items())

        node_degrees.sort(key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in node_degrees[:n]]

    def get_subgraph_for_nodes(self, node_ids: list) -> dict:
        """Get a subgraph containing only the specified nodes and their internal edges.

        Args:
            node_ids: List of node IDs to include.

        Returns:
            Dict with nodes and edges for visualization.
        """
        id_set = set(node_ids)

        nodes = []
        for node_id in node_ids:
            if self.graph.has_node(node_id):
                attrs = self.graph.nodes[node_id]
                nodes.append({
                    "id": node_id,
                    "label": node_id,
                    "type": attrs.get("type", "unknown"),
                    "color": attrs.get("color", "#6b7280"),
                    "size": self.graph.degree(node_id) + 5,
                })

        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            if u in id_set and v in id_set:
                edges.append({
                    "from": u,
                    "to": v,
                    "relation": attrs.get("relation", "related_to"),
                })

        return {"nodes": nodes, "edges": edges}

    def find_path(self, source: str, target: str) -> dict:
        """Find shortest path between two entities.

        Returns:
            Dict with path (list of node IDs), edges (with relations), and metadata.
        """
        if not self.graph.has_node(source):
            return {"error": f"Source entity '{source}' not found", "path": [], "edges": []}
        if not self.graph.has_node(target):
            return {"error": f"Target entity '{target}' not found", "path": [], "edges": []}

        try:
            path = nx.shortest_path(self.graph, source=source, target=target)
        except nx.NetworkXNoPath:
            return {"error": f"No path found between '{source}' and '{target}'", "path": [], "edges": []}
        except Exception as e:
            return {"error": str(e), "path": [], "edges": []}

        # Build path nodes and edges with metadata
        path_nodes = []
        for node_id in path:
            attrs = self.graph.nodes[node_id]
            path_nodes.append({
                "id": node_id,
                "type": attrs.get("type", "unknown"),
                "color": attrs.get("color", "#6b7280"),
            })

        path_edges = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = self.graph.edges[u, v]
            path_edges.append({
                "from": u,
                "to": v,
                "relation": edge_data.get("relation", "related_to"),
            })

        return {
            "path": path,
            "path_nodes": path_nodes,
            "path_edges": path_edges,
            "length": len(path) - 1,
        }

    def get_stats(self) -> dict:
        """Get graph statistics."""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": dict(
                (t, sum(1 for _, a in self.graph.nodes(data=True) if a.get("type") == t))
                for t in set(a.get("type", "unknown") for _, a in self.graph.nodes(data=True))
            ),
            "density": round(nx.density(self.graph), 6) if self.graph.number_of_nodes() > 0 else 0,
        }

    def clear(self):
        """Clear the entire graph."""
        self.graph.clear()
        if self.graph_file.exists():
            self.graph_file.unlink()
        logger.warning("Knowledge graph cleared")


# Module-level singleton
_kg = None


def get_knowledge_graph() -> IndustrialKnowledgeGraph:
    """Get or create the singleton knowledge graph."""
    global _kg
    if _kg is None:
        _kg = IndustrialKnowledgeGraph()
    return _kg
