"""Knowledge graph tests."""

from __future__ import annotations

from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.knowledge import KnowledgeNodeType, KnowledgeRelationType
from plex_music_enhancer.knowledge.builder import build_album_knowledge_graph


def test_album_knowledge_graph_creates_nodes_and_relations() -> None:
    """Album context should produce supported graph nodes and relations."""
    graph = build_album_knowledge_graph(_album_context())

    nodes = {(node.type, node.name) for node in graph.nodes}
    relations = {relation.type for relation in graph.relations}

    assert (KnowledgeNodeType.ARTIST, "Nina Simone") in nodes
    assert (KnowledgeNodeType.ALBUM, "Pastel Blues") in nodes
    assert (KnowledgeNodeType.PERSON, "Hal Mooney") in nodes
    assert (KnowledgeNodeType.PERSON, "Nina Simone") in nodes
    assert (KnowledgeNodeType.LABEL, "Philips Records") in nodes
    assert (KnowledgeNodeType.GENRE, "jazz") in nodes
    assert (KnowledgeNodeType.STUDIO, "RCA Studio B") in nodes
    assert KnowledgeRelationType.ARTIST_ALBUM in relations
    assert KnowledgeRelationType.ALBUM_PRODUCER in relations
    assert KnowledgeRelationType.ALBUM_SONGWRITER in relations
    assert KnowledgeRelationType.ALBUM_COMPOSER in relations
    assert KnowledgeRelationType.ALBUM_LABEL in relations
    assert KnowledgeRelationType.ALBUM_PREVIOUS_ALBUM in relations
    assert KnowledgeRelationType.ALBUM_NEXT_ALBUM in relations
    assert KnowledgeRelationType.ALBUM_GENRE in relations
    assert KnowledgeRelationType.ALBUM_STUDIO in relations


def test_album_knowledge_graph_serializes() -> None:
    """Knowledge graphs should serialize as part of context JSON."""
    graph = build_album_knowledge_graph(_album_context())
    payload = graph.model_dump(mode="json")

    assert payload["nodes"]
    assert payload["relations"]
    assert payload["summaries"]
    assert payload["relations"][0]["evidence"]


def test_album_knowledge_graph_does_not_invent_missing_relations() -> None:
    """Missing metadata should not create unsupported relations."""
    context = _album_context().model_copy(
        update={
            "producers": [],
            "labels": [],
            "studios": [],
            "previous_album": None,
            "next_album": None,
        }
    )
    graph = build_album_knowledge_graph(context)
    relations = {relation.type for relation in graph.relations}

    assert KnowledgeRelationType.ALBUM_PRODUCER not in relations
    assert KnowledgeRelationType.ALBUM_LABEL not in relations
    assert KnowledgeRelationType.ALBUM_STUDIO not in relations
    assert KnowledgeRelationType.ALBUM_PREVIOUS_ALBUM not in relations
    assert KnowledgeRelationType.ALBUM_NEXT_ALBUM not in relations


def _album_context() -> AlbumContext:
    """Return a context with graph-supported metadata."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Current Plex summary",
            genres=["Jazz"],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            release_date="1965-10",
            genres=["jazz"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(),
        pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        producers=["Hal Mooney"],
        composers=["Nina Simone"],
        lyricists=["Oscar Brown Jr."],
        labels=["Philips Records"],
        studios=["RCA Studio B"],
        genres=["jazz"],
        previous_album="I Put a Spell on You",
        next_album="Let It All Out",
        career_phase="mature phase",
        genre_evolution="Moved toward blues and soul.",
    )
