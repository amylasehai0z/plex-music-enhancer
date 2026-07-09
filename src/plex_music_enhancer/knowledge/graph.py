"""Small mutable helper for building knowledge graphs."""

from __future__ import annotations

from plex_music_enhancer.knowledge.models import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelation,
    KnowledgeRelationType,
)


class KnowledgeGraphBuilder:
    """Build a deduplicated knowledge graph."""

    def __init__(self) -> None:
        """Create an empty graph builder."""
        self._nodes: dict[str, KnowledgeNode] = {}
        self._relations: dict[tuple[str, str, KnowledgeRelationType], KnowledgeRelation] = {}
        self._summaries: list[str] = []

    def node(self, *, node_type: KnowledgeNodeType, name: str) -> str:
        """Add a node and return its stable ID."""
        node_id = _node_id(node_type=node_type, name=name)
        self._nodes.setdefault(
            node_id,
            KnowledgeNode(id=node_id, type=node_type, name=name.strip()),
        )
        return node_id

    def relation(
        self,
        *,
        source_id: str,
        target_id: str,
        relation_type: KnowledgeRelationType,
        evidence: str,
    ) -> None:
        """Add a directed relation."""
        key = (source_id, target_id, relation_type)
        self._relations.setdefault(
            key,
            KnowledgeRelation(
                source_id=source_id,
                target_id=target_id,
                type=relation_type,
                evidence=evidence,
            ),
        )

    def summary(self, value: str | None) -> None:
        """Add a graph summary line."""
        if value is None:
            return
        text = value.strip()
        if text and text not in self._summaries:
            self._summaries.append(text)

    def build(self) -> KnowledgeGraph:
        """Return an immutable knowledge graph."""
        return KnowledgeGraph(
            nodes=sorted(self._nodes.values(), key=lambda node: node.id),
            relations=sorted(
                self._relations.values(),
                key=lambda relation: (relation.source_id, relation.type.value, relation.target_id),
            ),
            summaries=self._summaries,
        )


def _node_id(*, node_type: KnowledgeNodeType, name: str) -> str:
    """Return a stable local node ID."""
    normalized = "-".join(name.strip().casefold().split())
    return f"{node_type.value}:{normalized}"
