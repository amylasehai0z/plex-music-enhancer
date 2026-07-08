"""Read-only album metadata enrichment pipeline."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.providers.musicbrainz import MusicBrainzAlbumMetadata, MusicBrainzProvider
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult, MusicBrainzMatcher


class PlexAlbumMetadata(BaseModel):
    """Input metadata from a Plex album."""

    model_config = ConfigDict(frozen=True)

    artist: str
    album: str
    year: int | None = None
    summary: str | None = None


class MusicBrainzEnrichmentMetadata(BaseModel):
    """MusicBrainz metadata gathered for an album."""

    model_config = ConfigDict(frozen=True)

    matched: bool
    confidence: int = Field(ge=0, le=100)
    artist_mbid: str | None = None
    release_group_mbid: str | None = None
    release_mbid: str | None = None
    release_date: str | None = None
    primary_type: str | None = None
    secondary_types: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AlbumMetadata(BaseModel):
    """Normalized album metadata document produced by enrichment."""

    model_config = ConfigDict(frozen=True)

    artist: str
    album: str
    year: int | None = None
    genres: list[str] = Field(default_factory=list)
    summary: str | None = None
    sources: list[str] = Field(default_factory=list)
    confidence: int = Field(ge=0, le=100)


class AlbumMetadataDocument(BaseModel):
    """Complete album enrichment document."""

    model_config = ConfigDict(frozen=True)

    plex: PlexAlbumMetadata
    musicbrainz: MusicBrainzEnrichmentMetadata
    metadata: AlbumMetadata


class _Matcher(Protocol):
    """Matcher interface used by the enrichment pipeline."""

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        """Match a Plex album to MusicBrainz."""


class _MusicBrainzProvider(Protocol):
    """MusicBrainz provider interface used by enrichment."""

    def get_album_metadata(self, mbid: str) -> MusicBrainzAlbumMetadata:
        """Return MusicBrainz album metadata."""


class MetadataEnrichmentPipeline:
    """Collect provider metadata and produce one normalized album document."""

    def __init__(
        self,
        *,
        matcher: _Matcher | None = None,
        musicbrainz_provider: _MusicBrainzProvider | None = None,
    ) -> None:
        """Create the enrichment pipeline."""
        provider = musicbrainz_provider or MusicBrainzProvider()
        self._musicbrainz_provider = provider
        self._matcher = matcher or MusicBrainzMatcher(provider=provider)

    def enrich_album(
        self,
        *,
        artist: str,
        album: str,
        year: int | None = None,
        summary: str | None = None,
    ) -> AlbumMetadataDocument:
        """Enrich one Plex album without modifying Plex."""
        plex = PlexAlbumMetadata(artist=artist, album=album, year=year, summary=summary)
        match = self._matcher.match_album(
            artist_name=artist,
            album_title=album,
            release_year=year,
        )

        musicbrainz_album = (
            self._musicbrainz_provider.get_album_metadata(match.release_group_mbid)
            if match.matched and match.release_group_mbid is not None
            else None
        )
        musicbrainz = _musicbrainz_metadata(match, musicbrainz_album)
        normalized = _normalized_metadata(plex, musicbrainz, musicbrainz_album)

        return AlbumMetadataDocument(
            plex=plex,
            musicbrainz=musicbrainz,
            metadata=normalized,
        )


def _musicbrainz_metadata(
    match: MatchResult,
    album: MusicBrainzAlbumMetadata | None,
) -> MusicBrainzEnrichmentMetadata:
    """Build MusicBrainz metadata for the enrichment document."""
    return MusicBrainzEnrichmentMetadata(
        matched=match.matched,
        confidence=match.confidence,
        artist_mbid=match.artist_mbid,
        release_group_mbid=match.release_group_mbid,
        release_mbid=match.release_mbid,
        release_date=match.first_release_date,
        primary_type=match.primary_type,
        secondary_types=match.secondary_types,
        genres=album.genres if album is not None else [],
        tags=album.tags if album is not None else [],
        warnings=match.warnings,
    )


def _normalized_metadata(
    plex: PlexAlbumMetadata,
    musicbrainz: MusicBrainzEnrichmentMetadata,
    album: MusicBrainzAlbumMetadata | None,
) -> AlbumMetadata:
    """Return normalized album metadata."""
    sources = ["plex"]
    if musicbrainz.matched:
        sources.append("musicbrainz")

    return AlbumMetadata(
        artist=album.artist or plex.artist if album is not None else plex.artist,
        album=album.title or plex.album if album is not None else plex.album,
        year=album.year or plex.year if album is not None else plex.year,
        genres=album.genres if album is not None else [],
        summary=None,
        sources=sources,
        confidence=musicbrainz.confidence,
    )
