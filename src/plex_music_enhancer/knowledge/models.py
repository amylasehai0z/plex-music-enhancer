"""Typed knowledge graph models for enrichment context."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeNodeType(StrEnum):
    """Supported knowledge graph node types."""

    ARTIST = "artist"
    ALBUM = "album"
    PERSON = "person"
    LABEL = "label"
    GENRE = "genre"
    STUDIO = "studio"


class KnowledgeRelationType(StrEnum):
    """Supported knowledge graph relation types."""

    ARTIST_ALBUM = "artist_album"
    ALBUM_PRODUCER = "album_producer"
    ALBUM_SONGWRITER = "album_songwriter"
    ALBUM_COMPOSER = "album_composer"
    ALBUM_LABEL = "album_label"
    ALBUM_PREVIOUS_ALBUM = "album_previous_album"
    ALBUM_NEXT_ALBUM = "album_next_album"
    ALBUM_GENRE = "album_genre"
    ALBUM_STUDIO = "album_studio"


class KnowledgeNode(BaseModel):
    """One graph node."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: KnowledgeNodeType
    name: str


class KnowledgeRelation(BaseModel):
    """One directed graph relation backed by collected metadata."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    type: KnowledgeRelationType
    evidence: str


class KnowledgeGraph(BaseModel):
    """Lightweight internal graph used to enrich prompts."""

    model_config = ConfigDict(frozen=True)

    nodes: list[KnowledgeNode] = Field(default_factory=list)
    relations: list[KnowledgeRelation] = Field(default_factory=list)
    summaries: list[str] = Field(default_factory=list)
