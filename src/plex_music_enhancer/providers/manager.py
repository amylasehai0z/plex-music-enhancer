"""Provider orchestration and metadata merging."""

from __future__ import annotations

from collections.abc import Iterable

from plex_music_enhancer.providers.base import AlbumMetadata, ArtistMetadata, MetadataProvider


class ProviderManager:
    """Query metadata providers in order and merge their results."""

    def __init__(self, providers: Iterable[MetadataProvider]) -> None:
        """Create a provider manager."""
        self._providers = list(providers)

    def get_artist_metadata(self, artist: str, *, language: str = "en") -> ArtistMetadata:
        """Return unified artist metadata from configured providers."""
        results: list[ArtistMetadata] = []
        for provider in self._providers:
            result = provider.get_artist_summary(artist, language=language)
            if result is None:
                candidates = provider.search_artist(artist, limit=1)
                result = candidates[0] if candidates else None

            if result is not None:
                results.append(result)

        return _merge_artist_metadata(artist, results)

    def get_album_metadata(
        self,
        artist: str,
        album: str,
        *,
        language: str = "en",
    ) -> AlbumMetadata:
        """Return unified album metadata from configured providers."""
        results: list[AlbumMetadata] = []
        for provider in self._providers:
            result = provider.get_album_summary(artist, album, language=language)
            if result is None:
                candidates = provider.search_album(artist, album, limit=1)
                result = candidates[0] if candidates else None

            if result is not None:
                results.append(result)

        return _merge_album_metadata(artist, album, results)


def _merge_artist_metadata(artist: str, results: list[ArtistMetadata]) -> ArtistMetadata:
    """Merge artist metadata while preserving provider order."""
    title = _first_text(result.title for result in results) or artist
    summary = _first_text(result.summary for result in results)
    language = _first_text(result.language for result in results)

    return ArtistMetadata(
        title=title,
        artist=artist,
        summary=summary,
        language=language,
        source=_merge_sources(result.source for result in results),
        confidence=_merge_confidence([result.confidence for result in results]),
    )


def _merge_album_metadata(artist: str, album: str, results: list[AlbumMetadata]) -> AlbumMetadata:
    """Merge album metadata while preserving provider order."""
    title = _first_text(result.title for result in results) or album
    summary = _first_text(result.summary for result in results)
    language = _first_text(result.language for result in results)

    return AlbumMetadata(
        title=title,
        artist=artist,
        summary=summary,
        language=language,
        source=_merge_sources(result.source for result in results),
        confidence=_merge_confidence([result.confidence for result in results]),
    )


def _first_text(values: Iterable[str | None]) -> str | None:
    """Return the first populated text value."""
    for value in values:
        if value:
            return value

    return None


def _merge_sources(source_groups: Iterable[list[str]]) -> list[str]:
    """Merge provider source attribution without duplicates."""
    merged: list[str] = []
    for sources in source_groups:
        for source in sources:
            if source not in merged:
                merged.append(source)

    return merged


def _merge_confidence(values: list[float]) -> float:
    """Merge confidence scores conservatively."""
    if not values:
        return 0.0

    return round(max(values), 3)
