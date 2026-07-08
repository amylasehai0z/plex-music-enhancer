"""Read-only pipeline for collecting normalized album context."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, SecretStr

from plex_music_enhancer.enrichment.models import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.enrichment.validators import validate_album_context
from plex_music_enhancer.providers import ProviderManager, WikipediaProvider
from plex_music_enhancer.providers.base import AlbumMetadata
from plex_music_enhancer.providers.musicbrainz import MusicBrainzAlbumMetadata, MusicBrainzProvider
from plex_music_enhancer.providers.wikipedia import WikipediaSummary
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult, MusicBrainzMatcher


class EnrichmentPipelineError(Exception):
    """Raised when album context cannot be collected."""


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the context pipeline."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the context pipeline."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class _Matcher(Protocol):
    """MusicBrainz matcher interface used by the context pipeline."""

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        """Match one album to MusicBrainz."""


class _MusicBrainzProvider(Protocol):
    """MusicBrainz metadata provider interface used by the context pipeline."""

    def get_album_metadata(self, mbid: str) -> MusicBrainzAlbumMetadata:
        """Return release-group metadata."""


class _WikipediaLookupProvider(Protocol):
    """Wikipedia lookup provider interface used for detailed page fields."""

    name: str

    def lookup_album(self, artist: str, album: str) -> WikipediaSummary | None:
        """Return detailed Wikipedia summary data."""


class EnrichmentPipeline:
    """Collect normalized read-only context for one Plex album."""

    def __init__(
        self,
        base_url: AnyHttpUrl | str,
        token: SecretStr,
        *,
        matcher: _Matcher | None = None,
        musicbrainz_provider: _MusicBrainzProvider | None = None,
        provider_manager: ProviderManager | None = None,
        wikipedia_provider: _WikipediaLookupProvider | None = None,
        plex_server_factory: Callable[[str, str], Any] = PlexServer,
    ) -> None:
        """Create an enrichment pipeline."""
        self._base_url = str(base_url).rstrip("/")
        self._token = token
        self._plex_server_factory = plex_server_factory
        provider = musicbrainz_provider or MusicBrainzProvider()
        self._musicbrainz_provider = provider
        self._matcher = matcher or MusicBrainzMatcher(provider=provider)
        self._wikipedia_provider = wikipedia_provider or WikipediaProvider()
        self._provider_manager = provider_manager or ProviderManager([self._wikipedia_provider])

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Collect all available metadata for one Plex album without modifying Plex."""
        plex_album = self._read_plex_album(artist=artist, album=album)
        plex_context = _plex_context(plex_album, requested_artist=artist)
        warnings: list[str] = []
        collected_sources = ["plex"]

        match = self._match_musicbrainz(plex_context, warnings)
        musicbrainz_album = self._musicbrainz_album(match, warnings)
        musicbrainz_context = _musicbrainz_context(match, musicbrainz_album)
        if musicbrainz_context.release_group_mbid is not None:
            collected_sources.append("musicbrainz")

        wikipedia_context = self._wikipedia_context(plex_context, warnings)
        if wikipedia_context.extract is not None:
            collected_sources.append("wikipedia")

        pipeline_context = validate_album_context(
            plex=plex_context,
            musicbrainz=musicbrainz_context,
            wikipedia=wikipedia_context,
            collected_sources=collected_sources,
            warnings=warnings,
        )

        return AlbumContext(
            plex=plex_context,
            musicbrainz=musicbrainz_context,
            wikipedia=wikipedia_context,
            pipeline=pipeline_context,
        )

    def _read_plex_album(self, *, artist: str, album: str) -> Any:
        """Read exactly one album from Plex."""
        try:
            server = cast(
                _PlexServer,
                self._plex_server_factory(self._base_url, self._token.get_secret_value()),
            )
            return _find_album(server, artist=artist, album=album)
        except EnrichmentPipelineError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to read album from Plex."
            raise EnrichmentPipelineError(msg) from exc

    def _match_musicbrainz(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> MatchResult:
        """Resolve the Plex album against MusicBrainz."""
        try:
            match = self._matcher.match_album(
                artist_name=plex.artist,
                album_title=plex.album,
                release_year=plex.year,
            )
        except Exception as exc:
            warnings.append(f"MusicBrainz matching failed: {exc}")
            return MatchResult(matched=False, confidence=0, warnings=[str(exc)])

        warnings.extend(match.warnings)
        return match

    def _musicbrainz_album(
        self,
        match: MatchResult,
        warnings: list[str],
    ) -> MusicBrainzAlbumMetadata | None:
        """Retrieve MusicBrainz release-group metadata for a match."""
        if not match.matched or match.release_group_mbid is None:
            return None

        try:
            return self._musicbrainz_provider.get_album_metadata(match.release_group_mbid)
        except Exception as exc:
            warnings.append(f"MusicBrainz metadata lookup failed: {exc}")
            return None

    def _wikipedia_context(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> WikipediaAlbumContext:
        """Resolve Wikipedia summary data through the configured provider manager."""
        metadata = self._provider_manager_album_metadata(plex, warnings)
        summary = self._wikipedia_provider.lookup_album(plex.artist, plex.album)

        if summary is not None:
            return WikipediaAlbumContext(
                language=summary.language,
                title=summary.title,
                extract=summary.extract,
                page_url=summary.url,
                thumbnail_url=summary.thumbnail,
            )

        if metadata is not None:
            return WikipediaAlbumContext(
                language=metadata.language,
                title=metadata.title,
                extract=metadata.summary,
            )

        warnings.append("Wikipedia metadata was not available.")
        return WikipediaAlbumContext()

    def _provider_manager_album_metadata(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> AlbumMetadata | None:
        """Retrieve normalized album metadata through ProviderManager."""
        try:
            return self._provider_manager.get_album_metadata(plex.artist, plex.album)
        except Exception as exc:
            warnings.append(f"Provider metadata lookup failed: {exc}")
            return None


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
        raise EnrichmentPipelineError(
            f'No Plex album named "{album}" was found for artist "{artist}".'
        )

    if len(matches) > 1:
        raise EnrichmentPipelineError(
            f'Found {len(matches)} Plex albums named "{album}" for artist "{artist}".'
        )

    return matches[0]


def _plex_context(album: Any, *, requested_artist: str) -> PlexAlbumContext:
    """Convert a Plex album object to normalized context."""
    return PlexAlbumContext(
        rating_key=_string(getattr(album, "ratingKey", None)) or "",
        artist=_string(getattr(album, "parentTitle", None)) or requested_artist,
        album=_string(getattr(album, "title", None)) or "Untitled",
        year=_int(getattr(album, "year", None)),
        summary=_string(getattr(album, "summary", None)),
        genres=_tag_names(getattr(album, "genres", [])),
        styles=_tag_names(getattr(album, "styles", [])),
        moods=_tag_names(getattr(album, "moods", [])),
    )


def _musicbrainz_context(
    match: MatchResult,
    album: MusicBrainzAlbumMetadata | None,
) -> MusicBrainzAlbumContext:
    """Build MusicBrainz album context from match and metadata results."""
    return MusicBrainzAlbumContext(
        artist_mbid=match.artist_mbid,
        release_group_mbid=match.release_group_mbid if match.matched else None,
        release_mbid=match.release_mbid if match.matched else None,
        release_date=match.first_release_date,
        genres=album.genres if album is not None else [],
        tags=album.tags if album is not None else [],
        confidence=match.confidence,
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


def _tag_names(tags: object) -> list[str]:
    """Return names from Plex tag objects."""
    if not isinstance(tags, Iterable) or isinstance(tags, str):
        return []

    names: list[str] = []
    for tag in tags:
        name = _string(tag) if isinstance(tag, str) else None
        if name is None:
            name = _string(getattr(tag, "tag", None) or getattr(tag, "title", None))
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
