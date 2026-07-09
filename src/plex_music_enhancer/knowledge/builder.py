"""Build knowledge graphs from enrichment context models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from plex_music_enhancer.knowledge.graph import KnowledgeGraphBuilder
from plex_music_enhancer.knowledge.models import (
    KnowledgeGraph,
    KnowledgeNodeType,
    KnowledgeRelationType,
)

if TYPE_CHECKING:
    from plex_music_enhancer.enrichment.models import AlbumContext


def build_album_knowledge_graph(context: AlbumContext) -> KnowledgeGraph:
    """Build a read-only graph from one album context."""
    builder = KnowledgeGraphBuilder()
    artist_id = builder.node(node_type=KnowledgeNodeType.ARTIST, name=context.plex.artist)
    album_id = builder.node(node_type=KnowledgeNodeType.ALBUM, name=context.plex.album)
    builder.relation(
        source_id=artist_id,
        target_id=album_id,
        relation_type=KnowledgeRelationType.ARTIST_ALBUM,
        evidence="plex.album",
    )

    _album_people(
        builder,
        album_id=album_id,
        values=context.producers,
        relation_type=KnowledgeRelationType.ALBUM_PRODUCER,
        evidence="album.producers",
    )
    _album_people(
        builder,
        album_id=album_id,
        values=context.lyricists,
        relation_type=KnowledgeRelationType.ALBUM_SONGWRITER,
        evidence="album.lyricists",
    )
    _album_people(
        builder,
        album_id=album_id,
        values=context.composers,
        relation_type=KnowledgeRelationType.ALBUM_COMPOSER,
        evidence="album.composers",
    )
    _album_values(
        builder,
        album_id=album_id,
        values=context.labels,
        node_type=KnowledgeNodeType.LABEL,
        relation_type=KnowledgeRelationType.ALBUM_LABEL,
        evidence="album.labels",
    )
    _album_values(
        builder,
        album_id=album_id,
        values=context.genres or context.musicbrainz.genres or context.plex.genres,
        node_type=KnowledgeNodeType.GENRE,
        relation_type=KnowledgeRelationType.ALBUM_GENRE,
        evidence="album.genres",
    )
    _album_values(
        builder,
        album_id=album_id,
        values=context.studios,
        node_type=KnowledgeNodeType.STUDIO,
        relation_type=KnowledgeRelationType.ALBUM_STUDIO,
        evidence="album.studios",
    )
    _neighbor_album(
        builder,
        album_id=album_id,
        title=context.previous_album,
        relation_type=KnowledgeRelationType.ALBUM_PREVIOUS_ALBUM,
        evidence="album.previous_album",
    )
    _neighbor_album(
        builder,
        album_id=album_id,
        title=context.next_album,
        relation_type=KnowledgeRelationType.ALBUM_NEXT_ALBUM,
        evidence="album.next_album",
    )

    builder.summary(_recurring_producer_summary(context))
    builder.summary(_label_history_summary(context))
    builder.summary(_career_phase_summary(context))
    builder.summary(_genre_evolution_summary(context))
    return builder.build()


def _album_people(
    builder: KnowledgeGraphBuilder,
    *,
    album_id: str,
    values: list[str],
    relation_type: KnowledgeRelationType,
    evidence: str,
) -> None:
    """Add person nodes connected to an album."""
    _album_values(
        builder,
        album_id=album_id,
        values=values,
        node_type=KnowledgeNodeType.PERSON,
        relation_type=relation_type,
        evidence=evidence,
    )


def _album_values(
    builder: KnowledgeGraphBuilder,
    *,
    album_id: str,
    values: list[str],
    node_type: KnowledgeNodeType,
    relation_type: KnowledgeRelationType,
    evidence: str,
) -> None:
    """Add value nodes connected to an album."""
    for value in values:
        node_id = builder.node(node_type=node_type, name=value)
        builder.relation(
            source_id=album_id,
            target_id=node_id,
            relation_type=relation_type,
            evidence=evidence,
        )


def _neighbor_album(
    builder: KnowledgeGraphBuilder,
    *,
    album_id: str,
    title: str | None,
    relation_type: KnowledgeRelationType,
    evidence: str,
) -> None:
    """Add a previous or next album relation when present."""
    if title is None:
        return
    neighbor_id = builder.node(node_type=KnowledgeNodeType.ALBUM, name=title)
    builder.relation(
        source_id=album_id,
        target_id=neighbor_id,
        relation_type=relation_type,
        evidence=evidence,
    )


def _recurring_producer_summary(context: AlbumContext) -> str | None:
    """Return producer summary context."""
    if not context.producers:
        return None
    return f"Producer relationship: {', '.join(context.producers)}."


def _label_history_summary(context: AlbumContext) -> str | None:
    """Return label history summary context."""
    if not context.labels:
        return None
    return f"Label history: released through {', '.join(context.labels)}."


def _career_phase_summary(context: AlbumContext) -> str | None:
    """Return career phase summary context."""
    if context.career_phase is None and context.discography_position is None:
        return None
    parts = [part for part in [context.career_phase, context.discography_position] if part]
    return f"Career phase: {'; '.join(parts)}."


def _genre_evolution_summary(context: AlbumContext) -> str | None:
    """Return genre evolution summary context."""
    if context.genre_evolution is None:
        return None
    return f"Genre evolution: {context.genre_evolution}"
