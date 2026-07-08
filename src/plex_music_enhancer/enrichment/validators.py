"""Validation helpers for album enrichment context."""

from __future__ import annotations

from plex_music_enhancer.enrichment.models import (
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)


def validate_album_context(
    *,
    plex: PlexAlbumContext,
    musicbrainz: MusicBrainzAlbumContext,
    wikipedia: WikipediaAlbumContext,
    collected_sources: list[str],
    warnings: list[str],
) -> PipelineContext:
    """Validate album context completeness for future generation steps."""
    missing_fields = _missing_fields(plex=plex, musicbrainz=musicbrainz, wikipedia=wikipedia)
    ready = not _critical_missing(missing_fields)

    return PipelineContext(
        collected_sources=collected_sources,
        missing_fields=missing_fields,
        warnings=_deduplicate(warnings),
        ready_for_generation=ready,
    )


def validate_artist_context(
    *,
    plex: PlexArtistContext,
    musicbrainz: MusicBrainzArtistContext,
    wikipedia: WikipediaArtistContext,
    collected_sources: list[str],
    warnings: list[str],
) -> PipelineContext:
    """Validate artist context completeness for generation."""
    missing_fields: list[str] = []
    if not plex.rating_key:
        missing_fields.append("plex.rating_key")
    if not plex.artist:
        missing_fields.append("plex.artist")
    if not plex.summary:
        missing_fields.append("plex.summary")
    if not plex.genres:
        missing_fields.append("plex.genres")
    if musicbrainz.artist_mbid is None:
        missing_fields.append("musicbrainz.artist_mbid")
    if not musicbrainz.genres:
        missing_fields.append("musicbrainz.genres")
    if wikipedia.extract is None:
        missing_fields.append("wikipedia.extract")
    if wikipedia.page_url is None:
        missing_fields.append("wikipedia.page_url")

    critical = {"plex.rating_key", "plex.artist", "wikipedia.extract"}
    return PipelineContext(
        collected_sources=collected_sources,
        missing_fields=missing_fields,
        warnings=_deduplicate(warnings),
        ready_for_generation=not bool(critical.intersection(missing_fields)),
    )


def _missing_fields(
    *,
    plex: PlexAlbumContext,
    musicbrainz: MusicBrainzAlbumContext,
    wikipedia: WikipediaAlbumContext,
) -> list[str]:
    """Return missing context fields."""
    missing: list[str] = []
    if not plex.rating_key:
        missing.append("plex.rating_key")
    if not plex.artist:
        missing.append("plex.artist")
    if not plex.album:
        missing.append("plex.album")
    if plex.year is None:
        missing.append("plex.year")
    if not plex.summary:
        missing.append("plex.summary")
    if not plex.genres:
        missing.append("plex.genres")
    if musicbrainz.artist_mbid is None:
        missing.append("musicbrainz.artist_mbid")
    if musicbrainz.release_group_mbid is None:
        missing.append("musicbrainz.release_group_mbid")
    if musicbrainz.release_mbid is None:
        missing.append("musicbrainz.release_mbid")
    if musicbrainz.release_date is None:
        missing.append("musicbrainz.release_date")
    if not musicbrainz.genres:
        missing.append("musicbrainz.genres")
    if wikipedia.extract is None:
        missing.append("wikipedia.extract")
    if wikipedia.page_url is None:
        missing.append("wikipedia.page_url")

    return missing


def _critical_missing(missing_fields: list[str]) -> bool:
    """Return whether missing fields block generation readiness."""
    critical_fields = {
        "plex.rating_key",
        "plex.artist",
        "plex.album",
        "musicbrainz.release_group_mbid",
        "wikipedia.extract",
    }
    return bool(critical_fields.intersection(missing_fields))


def _deduplicate(values: list[str]) -> list[str]:
    """Return values without duplicates while preserving order."""
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)

    return result
