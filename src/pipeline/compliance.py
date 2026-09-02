"""Compliance checker for requirements against ingested documents.

Analyzes a requirement against the document corpus to identify
compliance status and gaps.
"""

import re
from typing import Optional
from loguru import logger

from src.pipeline.embedder import TextEmbedder
from src.storage.chroma_store import VectorStore
from src.graph.knowledge_graph import get_knowledge_graph
from src.pipeline.extractor import extract_entities


class ComplianceChecker:
    """Checks regulatory requirements against ingested procedures for gaps."""

    def __init__(self):
        self.embedder = TextEmbedder()
        self.store = VectorStore()
        self.kg = get_knowledge_graph()

    def check_compliance(self, requirement: str, top_k: int = 10) -> dict:
        """Check a regulatory requirement against ingested documents.

        Args:
            requirement: The regulatory requirement text to check.
            top_k: Number of similar documents to retrieve.

        Returns:
            Dict with requirement, compliant status, gaps, and supporting evidence.
        """
        logger.info(f"Checking compliance for requirement: {requirement[:100]}...")

        # 1. Extract entities from the requirement
        try:
            req_entities = extract_entities(requirement)
        except Exception as e:
            logger.error(f"Entity extraction failed for requirement '{requirement[:100]}': {e}. Continuing without entities.")
            req_entities = {}
        entities_found = []
        for entity_list in req_entities.values():
            entities_found.extend(entity_list)

        # 2. Vector search for relevant procedures
        query_embedding = self.embedder.embed_query(requirement)
        search_results = self.store.query(query_embedding, n_results=top_k)

        # 3. Process search results to find supporting evidence
        supporting_evidence = []
        relevant_chunks = []

        if search_results and search_results["documents"] and len(search_results["documents"][0]) > 0:
            for i in range(len(search_results["documents"][0])):
                doc_text = search_results["documents"][0][i]
                metadata = search_results["metadatas"][0][i]
                distance = search_results["distances"][0][i]

                src_doc = metadata.get("doc_id", "unknown")
                record_id = metadata.get("record_id", "")

                # Calculate relevance score (lower distance = more relevant)
                relevance_score = max(0, 1 - distance)

                supporting_evidence.append({
                    "doc_id": src_doc,
                    "record_id": record_id,
                    "excerpt": doc_text[:500],
                    "relevance_score": round(relevance_score, 4),
                    "citation": f"{src_doc} ({record_id})" if record_id else src_doc,
                })
                relevant_chunks.append(doc_text)

        # 4. Graph-based analysis: find related entities and their connections
        graph_analysis = self._analyze_graph_relationships(req_entities)

        # 5. Determine compliance status and identify gaps
        compliance_result = self._analyze_compliance(
            requirement=requirement,
            supporting_evidence=supporting_evidence,
            relevant_chunks=relevant_chunks,
            graph_analysis=graph_analysis,
            entities_found=entities_found,
        )

        return compliance_result

    def _analyze_graph_relationships(self, req_entities: dict) -> dict:
        """Analyze knowledge graph relationships for entities in the requirement."""
        analysis = {
            "related_equipment": [],
            "related_regulations": [],
            "related_procedures": [],
            "entity_connections": {},
        }

        # Check equipment entities
        for eq in req_entities.get("equipment", []):
            neighbors = self.kg.get_entity_neighbors(eq, depth=1)
            if neighbors.get("neighbors"):
                analysis["related_equipment"].append({
                    "entity": eq,
                    "connections": len(neighbors["neighbors"]),
                    "related_entities": [n["id"] for n in neighbors["neighbors"][:5]],
                })
                analysis["entity_connections"][eq] = neighbors["neighbors"]

        # Check regulation entities
        for reg in req_entities.get("regulations", []):
            neighbors = self.kg.get_entity_neighbors(reg, depth=1)
            if neighbors.get("neighbors"):
                analysis["related_regulations"].append({
                    "entity": reg,
                    "connections": len(neighbors["neighbors"]),
                    "related_entities": [n["id"] for n in neighbors["neighbors"][:5]],
                })

        return analysis

    def _analyze_compliance(
        self,
        requirement: str,
        supporting_evidence: list,
        relevant_chunks: list,
        graph_analysis: dict,
        entities_found: list,
    ) -> dict:
        """Analyze compliance based on evidence and identify gaps."""

        # Combine all relevant text for analysis
        all_relevant_text = " ".join(relevant_chunks).lower()
        requirement_lower = requirement.lower()

        # Extract key requirements from the text
        key_requirements = self._extract_key_requirements(requirement)

        # Check which requirements are addressed
        addressed_requirements = []
        gaps = []

        for req in key_requirements:
            req_keywords = self._extract_keywords(req)
            # Check if any keywords are found in relevant documents
            found_keywords = [kw for kw in req_keywords if kw in all_relevant_text]

            if len(found_keywords) >= len(req_keywords) * 0.5:  # 50% keyword match threshold
                addressed_requirements.append({
                    "requirement": req,
                    "status": "addressed",
                    "confidence": min(1.0, len(found_keywords) / max(1, len(req_keywords))),
                })
            else:
                gaps.append({
                    "requirement": req,
                    "status": "gap",
                    "missing_keywords": [kw for kw in req_keywords if kw not in all_relevant_text],
                    "severity": self._assess_gap_severity(req, all_relevant_text),
                })

        # Determine overall compliance
        total_requirements = len(key_requirements)
        addressed_count = len(addressed_requirements)
        compliance_percentage = (addressed_count / total_requirements * 100) if total_requirements > 0 else 0

        # Overall compliance status
        if compliance_percentage >= 80:
            compliance_status = "compliant"
        elif compliance_percentage >= 50:
            compliance_status = "partial"
        else:
            compliance_status = "non_compliant"

        # Build response
        result = {
            "requirement": requirement,
            "compliant": compliance_status == "compliant",
            "compliance_status": compliance_status,
            "compliance_percentage": round(compliance_percentage, 1),
            "total_requirements": total_requirements,
            "addressed_count": addressed_count,
            "gaps_count": len(gaps),
            "gaps": gaps,
            "addressed_requirements": addressed_requirements,
            "supporting_evidence": supporting_evidence[:5],  # Top 5 evidence pieces
            "entities_analyzed": entities_found[:10],
            "graph_analysis": {
                "related_equipment_count": len(graph_analysis.get("related_equipment", [])),
                "related_regulations_count": len(graph_analysis.get("related_regulations", [])),
            },
        }

        logger.info(
            f"Compliance check complete: {compliance_status} "
            f"({compliance_percentage:.1f}% addressed, {len(gaps)} gaps found)"
        )
        return result

    def _extract_key_requirements(self, requirement: str) -> list[str]:
        """Extract individual requirements from the requirement text."""
        # Split by common delimiters
        requirements = []

        # Split by semicolons, periods, or numbered lists
        parts = re.split(r'[;.\n]', requirement)

        for part in parts:
            part = part.strip()
            if len(part) > 10:  # Minimum length for a meaningful requirement
                # Remove numbering if present
                part = re.sub(r'^\d+[\.\)]\s*', '', part)
                if part:
                    requirements.append(part)

        # If no clear delimiters, treat as single requirement
        if not requirements:
            requirements = [requirement]

        return requirements

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        # Common stop words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'must',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'whom', 'where', 'when', 'why',
            'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'because', 'if', 'then', 'else',
            'until', 'while', 'about', 'between', 'through', 'during', 'before',
            'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there',
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter out stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords

    def _assess_gap_severity(self, requirement: str, relevant_text: str) -> str:
        """Assess the severity of a compliance gap."""
        req_lower = requirement.lower()

        # Check for critical safety terms
        critical_terms = ['safety', 'danger', 'hazard', 'emergency', 'critical', 'urgent']
        has_critical = any(term in req_lower for term in critical_terms)

        # Check for regulatory references
        has_regulation = bool(re.search(r'(section \d+|part \d+|regulation|standard|code)', req_lower))

        if has_critical and has_regulation:
            return "critical"
        elif has_critical or has_regulation:
            return "high"
        else:
            return "medium"


# Module-level singleton
_checker = None


def get_compliance_checker() -> ComplianceChecker:
    """Get or create the singleton compliance checker."""
    global _checker
    if _checker is None:
        _checker = ComplianceChecker()
    return _checker


def check_compliance(requirement: str, top_k: int = 10) -> dict:
    """Convenience function to check compliance."""
    return get_compliance_checker().check_compliance(requirement, top_k)
