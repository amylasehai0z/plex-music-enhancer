"""Wikipedia metadata provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from plex_music_enhancer.providers.base import AlbumMetadata, ArtistMetadata
from plex_music_enhancer.providers.wikipedia.client import WikipediaClient

DEFAULT_CACHE_DIRECTORY = Path("cache/wikipedia")
DEFAULT_CACHE_TTL = timedelta(days=30)
DEFAULT_LANGUAGES = ("de", "en")
SOURCE_NAME = "wikipedia"


class WikipediaSummary(BaseModel):
    """Wikipedia page summary normalized for provider consumers."""

    model_config = ConfigDict(frozen=True)

    title: str
    page_id: int | None = None
    language: str
    extract: str | None = None
    url: str | None = None
    thumbnail: str | None = None


class _CacheEntry(BaseModel):
    """Cached Wikipedia summary with creation timestamp."""

    cached_at: datetime
    summary: WikipediaSummary


class WikipediaProvider:
    """Read-only provider backed by the official Wikipedia REST API."""

    name = SOURCE_NAME

    def __init__(
        self,
        *,
        client: WikipediaClient | httpx.Client | None = None,
        cache_directory: Path = DEFAULT_CACHE_DIRECTORY,
        cache_ttl: timedelta = DEFAULT_CACHE_TTL,
        languages: tuple[str, ...] = DEFAULT_LANGUAGES,
    ) -> None:
        """Create a Wikipedia provider."""
        if isinstance(client, httpx.Client):
            self._client = WikipediaClient(http_client=client)
        else:
            self._client = client or WikipediaClient()
        self._cache_directory = cache_directory
        self._cache_ttl = cache_ttl
        self._languages = languages

    def lookup_artist(self, artist: str) -> WikipediaSummary | None:
        """Return the best Wikipedia summary for an artist."""
        return self._lookup(kind="artist", query=artist)

    def lookup_album(self, artist: str, album: str) -> WikipediaSummary | None:
        """Return the best Wikipedia summary for an album."""
        return self._lookup(kind="album", query=f"{album} {artist}")

    def search_artist(self, artist: str, *, limit: int = 5) -> list[ArtistMetadata]:
        """Search Wikipedia title candidates for an artist."""
        del limit
        summary = self.lookup_artist(artist)
        if summary is None:
            return []

        return [self._artist_metadata(artist, summary)]

    def search_album(self, artist: str, album: str, *, limit: int = 5) -> list[AlbumMetadata]:
        """Search Wikipedia title candidates for an album."""
        del limit
        summary = self.lookup_album(artist, album)
        if summary is None:
            return []

        return [self._album_metadata(artist, album, summary)]

    def get_artist_summary(
        self,
        artist: str,
        *,
        language: str = "en",
    ) -> ArtistMetadata | None:
        """Return the best Wikipedia artist summary."""
        del language
        summary = self.lookup_artist(artist)
        return self._artist_metadata(artist, summary) if summary is not None else None

    def get_album_summary(
        self,
        artist: str,
        album: str,
        *,
        language: str = "en",
    ) -> AlbumMetadata | None:
        """Return the best Wikipedia album summary."""
        del language
        summary = self.lookup_album(artist, album)
        return self._album_metadata(artist, album, summary) if summary is not None else None

    def _lookup(self, *, kind: str, query: str) -> WikipediaSummary | None:
        """Lookup a Wikipedia summary using preferred language fallback."""
        for language in self._languages:
            cached = self._read_cache(kind=kind, language=language, query=query)
            if cached is not None:
                return cached

            title = self._first_title(query, language=language)
            if title is None:
                continue

            payload = self._client.get_summary(title, language=language)
            if payload is None:
                continue

            summary = _summary_from_payload(payload, language=language, fallback_title=title)
            self._write_cache(kind=kind, language=language, query=query, summary=summary)
            return summary

        return None

    def _first_title(self, query: str, *, language: str) -> str | None:
        """Return the first title search result for a language edition."""
        pages = self._client.search_titles(query, language=language, limit=1)
        if not pages:
            return None

        return _string(pages[0].get("title"))

    def _read_cache(self, *, kind: str, language: str, query: str) -> WikipediaSummary | None:
        """Read a fresh cached summary when present."""
        cache_file = self._cache_file(kind=kind, language=language, query=query)
        if not cache_file.exists():
            return None

        try:
            entry = _CacheEntry.model_validate_json(cache_file.read_text(encoding="utf-8"))
        except ValueError:
            return None

        age = datetime.now(UTC) - entry.cached_at
        if age > self._cache_ttl:
            return None

        return entry.summary

    def _write_cache(
        self,
        *,
        kind: str,
        language: str,
        query: str,
        summary: WikipediaSummary,
    ) -> None:
        """Persist a summary cache entry."""
        self._cache_directory.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_file(kind=kind, language=language, query=query)
        entry = _CacheEntry(cached_at=datetime.now(UTC), summary=summary)
        cache_file.write_text(entry.model_dump_json(indent=2), encoding="utf-8")

    def _cache_file(self, *, kind: str, language: str, query: str) -> Path:
        """Return the cache file for a lookup."""
        normalized = f"{kind}:{language}:{query.strip().casefold()}"
        digest = sha256(normalized.encode("utf-8")).hexdigest()
        return self._cache_directory / f"{digest}.json"

    def _artist_metadata(self, artist: str, summary: WikipediaSummary) -> ArtistMetadata:
        """Convert a Wikipedia summary to normalized artist metadata."""
        return ArtistMetadata(
            title=summary.title,
            artist=artist,
            summary=summary.extract,
            language=summary.language,
            source=[self.name],
            confidence=0.85,
        )

    def _album_metadata(
        self,
        artist: str,
        album: str,
        summary: WikipediaSummary,
    ) -> AlbumMetadata:
        """Convert a Wikipedia summary to normalized album metadata."""
        return AlbumMetadata(
            title=album,
            artist=artist,
            summary=summary.extract,
            language=summary.language,
            source=[self.name],
            confidence=0.85,
        )


def _summary_from_payload(
    payload: dict[str, Any],
    *,
    language: str,
    fallback_title: str,
) -> WikipediaSummary:
    """Build a Wikipedia summary model from REST response JSON."""
    return WikipediaSummary(
        title=_string(payload.get("title")) or fallback_title,
        page_id=_int(payload.get("pageid")),
        language=_string(payload.get("lang")) or language,
        extract=_string(payload.get("extract")),
        url=_content_url(payload),
        thumbnail=_thumbnail_url(payload),
    )


def _content_url(payload: dict[str, Any]) -> str | None:
    """Return the canonical page URL from a summary payload."""
    content_urls = payload.get("content_urls")
    if not isinstance(content_urls, dict):
        return None

    for platform in ("desktop", "mobile"):
        platform_urls = content_urls.get(platform)
        if isinstance(platform_urls, dict):
            page_url = _string(platform_urls.get("page"))
            if page_url is not None:
                return page_url

    return None


def _thumbnail_url(payload: dict[str, Any]) -> str | None:
    """Return the thumbnail URL from a summary payload."""
    thumbnail = payload.get("thumbnail")
    if isinstance(thumbnail, dict):
        return _string(thumbnail.get("source"))

    return None


def _int(value: object) -> int | None:
    """Return an integer when a payload value can be parsed."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None

    return None


def _string(value: object) -> str | None:
    """Return a non-empty string."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None
