"""Typed models for normalized album enrichment context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlexAlbumContext(BaseModel):
    """Metadata read directly from one Plex album."""

    model_config = ConfigDict(frozen=True)

    rating_key: str
    artist: str
    album: str
    year: int | None = None
    summary: str | None = None
    genres: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)


class MusicBrainzAlbumContext(BaseModel):
    """MusicBrainz identity and metadata for one album."""

    model_config = ConfigDict(frozen=True)

    artist_mbid: str | None = None
    release_group_mbid: str | None = None
    release_mbid: str | None = None
    release_date: str | None = None
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)


class WikipediaAlbumContext(BaseModel):
    """Wikipedia summary metadata for one album."""

    model_config = ConfigDict(frozen=True)

    language: str | None = None
    title: str | None = None
    extract: str | None = None
    page_url: str | None = None
    thumbnail_url: str | None = None


class PipelineContext(BaseModel):
    """Pipeline status after collecting and validating album context."""

    model_config = ConfigDict(frozen=True)

    collected_sources: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ready_for_generation: bool = False


class AlbumContext(BaseModel):
    """Normalized context document for preview, AI generation, apply, and rollback."""

    model_config = ConfigDict(frozen=True)

    plex: PlexAlbumContext
    musicbrainz: MusicBrainzAlbumContext
    wikipedia: WikipediaAlbumContext
    pipeline: PipelineContext
