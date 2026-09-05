"""Knowledge graph builder using NetworkX.

Backed by relational database tables in PostgreSQL/SQLite for persistence.
Supports domain-namespaced graphs via DomainProfile.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger
import networkx as nx

from src.config import settings, DomainProfile
from src.database.connection import get_db_session
from src.database.models import GraphNode as DbNode, GraphEdge as DbEdge

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
    "note": "#a78bfa",           # lavender (wikilink targets)
}


class IndustrialKnowledgeGraph:
    """NetworkX-based knowledge graph backed by database tables.

    When a DomainProfile is provided, all reads and writes are scoped to
    that domain via a domain_id column. When no profile is given, the graph
    operates on all data (backward-compatible default).
    """

    def __init__(self, domain_profile: Optional[DomainProfile] = None, load_from_disk: bool = True):
        self.domain_id: Optional[str] = domain_profile.domain_id if domain_profile else None
        self.graph_file: Optional[str] = domain_profile.graph_file if domain_profile else None
        self.graph = nx.Graph()
        if load_from_disk:
            self._sync_from_db()

    def _sync_from_db(self):
        """Load node and edge records from database into the in-memory NetworkX index.

        If domain_id is set, only load records tagged with that domain.
        """
        try:
            self.graph.clear()
            with get_db_session() as db:
                if self.domain_id:
                    nodes = db.query(DbNode).filter(DbNode.domain_id == self.domain_id).all()
                    edges = db.query(DbEdge).filter(DbEdge.domain_id == self.domain_id).all()
                else:
                    nodes = db.query(DbNode).all()
                    edges = db.query(DbEdge).all()

                for node in nodes:
                    attrs = node.attributes
                    attrs["type"] = node.node_type
                    attrs["color"] = NODE_COLORS.get(node.node_type, "#6b7280")
                    attrs["doc_id"] = node.doc_id
                    self.graph.add_node(node.node_id, **attrs)

                for edge in edges:
                    attrs = edge.attributes
                    attrs["relation"] = edge.relation
                    self.graph.add_edge(edge.source_id, edge.target_id, **attrs)

            logger.info(
                f"Knowledge Graph synced from DB (domain={self.domain_id}): "
                f"{self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges"
            )
        except Exception as e:
            logger.error(f"Failed to sync Knowledge Graph from DB: {e}")

    def save(self):
        """Persist graph to database. (Already committed via relational writes, log only)."""
        logger.info(
            f"Relational Graph persistent status: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges in DB."
        )

    def add_entity(self, entity_id: str, entity_type: str, **attrs):
        """Add an entity node to the database and in-memory index."""
        try:
            doc_id = attrs.pop("doc_id", None)
            
            # Sync to in-memory graph
            mem_attrs = dict(attrs)
            mem_attrs["type"] = entity_type
            mem_attrs["color"] = NODE_COLORS.get(entity_type, "#6b7280")
            if doc_id:
                mem_attrs["doc_id"] = doc_id
            
            if self.graph.has_node(entity_id):
                for k, v in mem_attrs.items():
                    self.graph.nodes[entity_id][k] = v
            else:
                self.graph.add_node(entity_id, **mem_attrs)

            # Sync to DB
            with get_db_session() as db:
                db_node = db.query(DbNode).filter(DbNode.node_id == entity_id).first()
                if not db_node:
                    db_node = DbNode(
                        node_id=entity_id,
                        node_type=entity_type,
                        doc_id=doc_id,
                        domain_id=self.domain_id,
                    )
                    db_node.attributes = attrs
                    db.add(db_node)
                else:
                    db_node.node_type = entity_type
                    if doc_id:
                        db_node.doc_id = doc_id
                    if self.domain_id:
                        db_node.domain_id = self.domain_id
                    curr_attrs = db_node.attributes
                    curr_attrs.update(attrs)
                    db_node.attributes = curr_attrs
        except Exception as e:
            logger.error(f"Failed to add entity node {entity_id} to DB: {e}")

    def add_relationship(self, source: str, target: str, relation: str, **attrs):
        """Add a relationship edge between two entities in DB and in-memory index."""
        try:
            # Sync to in-memory graph
            mem_attrs = dict(attrs)
            mem_attrs["relation"] = relation
            self.graph.add_edge(source, target, **mem_attrs)

            # Sync to DB
            with get_db_session() as db:
                # Ensure source and target nodes exist in DB
                src_node = db.query(DbNode).filter(DbNode.node_id == source).first()
                if not src_node:
                    src_node = DbNode(node_id=source, node_type="unknown")
                    db.add(src_node)
                    self.graph.add_node(source, type="unknown", color="#6b7280")

                tgt_node = db.query(DbNode).filter(DbNode.node_id == target).first()
                if not tgt_node:
                    tgt_node = DbNode(node_id=target, node_type="unknown")
                    db.add(tgt_node)
                    self.graph.add_node(target, type="unknown", color="#6b7280")

                db_edge = db.query(DbEdge).filter(
                    DbEdge.source_id == source,
                    DbEdge.target_id == target,
                    DbEdge.relation == relation
                ).first()
                if not db_edge:
                    db_edge = DbEdge(
                        source_id=source,
                        target_id=target,
                        relation=relation,
                        domain_id=self.domain_id,
                    )
                    db_edge.attributes = attrs
                    db.add(db_edge)
                else:
                    curr_attrs = db_edge.attributes
                    curr_attrs.update(attrs)
                    db_edge.attributes = curr_attrs
        except Exception as e:
            logger.error(f"Failed to add relationship edge {source}->{target} to DB: {e}")

    def add_document_entities(self, doc_id: str, text: str, entities: dict, metadata: Optional[dict] = None):
        """Add all entities from a document to the graph and create relationships."""
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

        # 10. Generic domain entity types (e.g. DatabaseConcept, SQLCommand).
        #     Any category not handled above becomes a node of its own type;
        #     entities that co-occur in the same document get a "co_occurs_with"
        #     edge so mastery sees them as connected.
        handled = {"equipment", "permits", "work_orders", "incidents", "inspections",
                   "regulations", "plants", "hazards", "incident_types",
                   "permit_types", "personnel", "wikilinks"}
        domain_cats = [k for k in entities if k not in handled and entities[k]]
        for cat in domain_cats:
            ids = entities[cat]
            for eid in ids:
                self.add_entity(eid, cat, doc_id=doc_id)
                added_nodes += 1
            # Connect co-occurring entities in this document
            if len(ids) > 1:
                for i in range(len(ids) - 1):
                    self.add_relationship(ids[i], ids[i + 1], "co_occurs_with")
                    added_edges += 1

        logger.info(f"Added {added_nodes} nodes, {added_edges} edges from document {doc_id}")

    def add_wikilink_entities(self, source_note: str, target_notes: list[str], doc_id: str = ""):
        """Add wikilink nodes and LINKS_TO edges to the graph.

        Called when link_syntax == "wikilink". Each target note becomes a node
        (type: Note) with a LINKS_TO edge from the source note.
        """
        if not target_notes:
            return

        # Add the source note as a node
        self.add_entity(source_note, "note", doc_id=doc_id)

        for target in target_notes:
            # Add the target note as a node
            self.add_entity(target, "note", doc_id=doc_id)
            # Add the LINKS_TO edge
            self.add_relationship(source_note, target, "LINKS_TO")

        logger.debug(
            f"Wikilinks: {source_note} -> {len(target_notes)} targets"
        )

    def get_entity_neighbors(self, entity_id: str, depth: int = 1) -> dict:
        """Get neighbors of an entity up to a given depth."""
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
        """Export graph as nodes/edges JSON for visualization."""
        node_list = []
        for node_id, attrs in self.graph.nodes(data=True):
            node_list.append({
                "id": node_id,
                "label": node_id,
                "type": attrs.get("type", "unknown"),
                "color": attrs.get("color", "#6b7280"),
                "size": self.graph.degree(node_id) + 5,
            })

        if len(node_list) > max_nodes:
            node_list.sort(key=lambda x: x["size"], reverse=True)
            kept_ids = {n["id"] for n in node_list[:max_nodes]}
            node_list = node_list[:max_nodes]
        else:
            kept_ids = {n["id"] for n in node_list}

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
        """Get all entities grouped by type."""
        result = {}
        for node_id, attrs in self.graph.nodes(data=True):
            etype = attrs.get("type", "unknown")
            if etype not in result:
                result[etype] = []
            result[etype].append(node_id)
        for key in result:
            result[key].sort()
        return result

    def search_nodes(self, query: str, node_types: Optional[list] = None, limit: int = 50) -> list:
        """Search for nodes by name/label matching the query string."""
        query_lower = query.lower()
        matches = []

        for node_id, attrs in self.graph.nodes(data=True):
            etype = attrs.get("type", "unknown")

            if node_types and etype not in node_types:
                continue

            if query_lower in node_id.lower():
                matches.append({
                    "id": node_id,
                    "type": etype,
                    "color": attrs.get("color", "#6b7280"),
                    "degree": self.graph.degree(node_id),
                })

        matches.sort(key=lambda x: x["degree"], reverse=True)
        return matches[:limit]

    def get_node_metadata(self, node_id: str) -> dict:
        """Get full metadata for a node including neighbors and linked resources."""
        if not self.graph.has_node(node_id):
            return {"error": f"Node '{node_id}' not found"}

        attrs = self.graph.nodes[node_id]

        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]
            neighbors.append({
                "id": neighbor,
                "type": self.graph.nodes[neighbor].get("type", "unknown"),
                "color": self.graph.nodes[neighbor].get("color", "#6b7280"),
                "relation": edge_data.get("relation", "related_to"),
            })

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
        """Get top N most-connected nodes for initial graph loading."""
        all_degrees = dict(self.graph.degree())
        
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
        """Get a subgraph containing only the specified nodes and their internal edges."""
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
        """Find shortest path between two entities."""
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
        """Clear graph from DB and memory index.

        If domain_id is set, only clear records for that domain.
        """
        try:
            self.graph.clear()
            with get_db_session() as db:
                if self.domain_id:
                    db.query(DbEdge).filter(DbEdge.domain_id == self.domain_id).delete()
                    db.query(DbNode).filter(DbNode.domain_id == self.domain_id).delete()
                else:
                    db.query(DbEdge).delete()
                    db.query(DbNode).delete()
            logger.warning(f"Knowledge Graph cleared (domain={self.domain_id}).")
        except Exception as e:
            logger.error(f"Failed to clear graph in DB: {e}")


# Module-level singletons, keyed by domain_id
_kg_singletons: dict[str, IndustrialKnowledgeGraph] = {}


def get_knowledge_graph(domain_profile: Optional[DomainProfile] = None) -> IndustrialKnowledgeGraph:
    """Get or create a domain-scoped knowledge graph singleton.

    When no profile is given, returns the legacy global graph (no domain filter).
    """
    key = domain_profile.domain_id if domain_profile else "__global__"
    if key not in _kg_singletons:
        _kg_singletons[key] = IndustrialKnowledgeGraph(domain_profile=domain_profile)
    return _kg_singletons[key]
