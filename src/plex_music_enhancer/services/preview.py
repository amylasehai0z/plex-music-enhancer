"""Read-only album enrichment preview service."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

from plex_music_enhancer.services.enrichment import (
    AlbumMetadataDocument,
    MetadataEnrichmentPipeline,
)


class PlexAlbumPreview(BaseModel):
    """Plex album metadata displayed by preview."""

    model_config = ConfigDict(frozen=True)

    title: str
    artist: str
    current_summary: str | None = None
    year: int | None = None
    genres: list[str] = Field(default_factory=list)


class ProviderPreviewStatus(BaseModel):
    """Provider readiness status for an enrichment preview."""

    model_config = ConfigDict(frozen=True)

    name: str
    reachable: bool
    match_found: bool
    metadata_available: bool
    error: str | None = None


class EnrichmentPreviewDocument(BaseModel):
    """Complete enrichment preview document."""

    model_config = ConfigDict(frozen=True)

    plex: PlexAlbumPreview
    provider: ProviderPreviewStatus
    metadata: AlbumMetadataDocument | None = None
    ready_for_ai_enrichment: bool


class PreviewError(Exception):
    """Raised when an enrichment preview cannot be prepared."""


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by preview."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by preview."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class EnrichmentPreviewService:
    """Prepare a read-only enrichment preview for one Plex album."""

    def __init__(
        self,
        base_url: AnyHttpUrl,
        token: SecretStr,
        *,
        pipeline: MetadataEnrichmentPipeline | None = None,
    ) -> None:
        """Create an enrichment preview service."""
        self._base_url = str(base_url).rstrip("/")
        self._token = token
        self._pipeline = pipeline or MetadataEnrichmentPipeline()

    def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
        """Read one Plex album and preview enrichment readiness."""
        try:
            server = cast(_PlexServer, PlexServer(self._base_url, self._token.get_secret_value()))
            plex_album = _find_album(server, artist=artist, album=album)
            plex_preview = _plex_album_preview(plex_album, requested_artist=artist)
        except PreviewError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to read album from Plex."
            raise PreviewError(msg) from exc

        try:
            metadata = self._pipeline.enrich_album(
                artist=plex_preview.artist,
                album=plex_preview.title,
                year=plex_preview.year,
                summary=plex_preview.current_summary,
            )
        except Exception as exc:
            provider = ProviderPreviewStatus(
                name="MusicBrainz",
                reachable=False,
                match_found=False,
                metadata_available=False,
                error=str(exc) or "MusicBrainz provider failed.",
            )
            return EnrichmentPreviewDocument(
                plex=plex_preview,
                provider=provider,
                metadata=None,
                ready_for_ai_enrichment=False,
            )

        metadata_available = _metadata_available(metadata)
        provider = ProviderPreviewStatus(
            name="MusicBrainz",
            reachable=True,
            match_found=metadata.musicbrainz.matched,
            metadata_available=metadata_available,
        )
        ready = provider.reachable and provider.match_found and provider.metadata_available
        return EnrichmentPreviewDocument(
            plex=plex_preview,
            provider=provider,
            metadata=metadata,
            ready_for_ai_enrichment=ready,
        )


def _find_album(server: _PlexServer, *, artist: str, album: str) -> Any:
    """Find exactly one Plex album by artist and album title."""
    matches: list[Any] = []
    artist_query = _normalize(artist)
    album_query = _normalize(album)

    for section in _music_sections(server.library.sections()):
        for plex_artist in _safe_items(getattr(section, "all", None)):
            if _normalize(getattr(plex_artist, "title", None)) != artist_query:
                continue

            for plex_album in _safe_items(getattr(plex_artist, "albums", None)):
                if _normalize(getattr(plex_album, "title", None)) == album_query:
                    matches.append(plex_album)

    if not matches:
        raise PreviewError(f'No Plex album named "{album}" was found for artist "{artist}".')

    if len(matches) > 1:
        raise PreviewError(
            f'Found {len(matches)} Plex albums named "{album}" for artist "{artist}".'
        )

    return matches[0]


def _plex_album_preview(album: Any, *, requested_artist: str) -> PlexAlbumPreview:
    """Convert a Plex album object into preview metadata."""
    title = _string(getattr(album, "title", None)) or "Untitled"
    artist = _string(getattr(album, "parentTitle", None)) or requested_artist
    return PlexAlbumPreview(
        title=title,
        artist=artist,
        current_summary=_string(getattr(album, "summary", None)),
        year=_int(getattr(album, "year", None)),
        genres=_tag_names(getattr(album, "genres", [])),
    )


def _music_sections(sections: Iterable[Any]) -> list[Any]:
    """Return music library sections."""
    return [
        section
        for section in sections
        if (getattr(section, "type", None) or getattr(section, "TYPE", None)) == "artist"
    ]


def _safe_items(method: Any) -> list[Any]:
    """Call a Plex method and return a list."""
    if not callable(method):
        return []

    result = method()
    return list(result) if result is not None else []


def _metadata_available(document: AlbumMetadataDocument) -> bool:
    """Return whether provider metadata is available for enrichment."""
    return bool(
        document.musicbrainz.release_group_mbid
        and (
            document.musicbrainz.release_date
            or document.musicbrainz.primary_type
            or document.musicbrainz.genres
            or document.musicbrainz.tags
        )
    )


def _tag_names(tags: object) -> list[str]:
    """Return names from Plex tag objects."""
    if not isinstance(tags, Iterable) or isinstance(tags, str):
        return []

    names: list[str] = []
    for tag in tags:
        name = _string(getattr(tag, "tag", None) or getattr(tag, "title", None) or tag)
        if name is not None:
            names.append(name)

    return names


def _normalize(value: object) -> str:
    """Normalize a Plex title for exact matching."""
    return str(value or "").strip().casefold()


def _string(value: object) -> str | None:
    """Return a populated string."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _int(value: object) -> int | None:
    """Return an int if possible."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
