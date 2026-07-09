"""Read-only Last.fm metadata provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from html import unescape
from pathlib import Path
from re import sub
from threading import Lock
from time import monotonic, sleep
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from plex_music_enhancer.constants import __version__
from plex_music_enhancer.enrichment.models import LastFMAlbumContext, LastFMArtistContext
from plex_music_enhancer.utils.files import write_text_atomic

LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0"
DEFAULT_CACHE_DIRECTORY = Path.home() / ".plex-enhancer" / "cache" / "lastfm"
DEFAULT_CACHE_TTL = timedelta(days=30)
DEFAULT_RATE_LIMIT_SECONDS = 0.25
DEFAULT_RETRIES = 2
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class LastFMProvider:
    """Optional read-only metadata provider backed by the Last.fm API."""

    name = "lastfm"

    def __init__(
        self,
        *,
        api_key: SecretStr | str | None = None,
        http_client: httpx.Client | None = None,
        base_url: str = LASTFM_BASE_URL,
        cache_directory: Path = DEFAULT_CACHE_DIRECTORY,
        cache_ttl: timedelta = DEFAULT_CACHE_TTL,
        timeout_seconds: float = 10.0,
        rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        user_agent: str | None = None,
    ) -> None:
        """Create a Last.fm provider.

        When no API key is configured, lookups return empty context objects.
        """
        self._api_key = _secret_value(api_key)
        self._base_url = base_url.rstrip("/")
        self._cache_directory = cache_directory
        self._cache_ttl = cache_ttl
        self._rate_limit_seconds = rate_limit_seconds
        self._retries = retries
        self._lock = Lock()
        self._last_request_at: float | None = None
        self._headers = {
            "Accept": "application/json",
            "User-Agent": user_agent or _default_user_agent(),
        }
        self._client = http_client or httpx.Client(timeout=timeout_seconds, headers=self._headers)

    @property
    def configured(self) -> bool:
        """Return whether the provider has credentials and may perform network lookups."""
        return bool(self._api_key)

    def lookup_artist(self, artist: str) -> LastFMArtistContext:
        """Lookup Last.fm artist biography, tags, and similar artists."""
        if not self.configured:
            return LastFMArtistContext()

        cached = self._read_cache(kind="artist", key=artist, model_type=LastFMArtistContext)
        if cached is not None:
            return cached

        try:
            payload = self._get_json("artist.getinfo", {"artist": artist, "autocorrect": 1})
            context = _artist_context(payload.get("artist"))
        except Exception:
            return LastFMArtistContext()

        if _artist_has_data(context):
            self._write_cache(kind="artist", key=artist, value=context)
        return context

    def lookup_album(self, artist: str, album: str) -> LastFMAlbumContext:
        """Lookup Last.fm album wiki, tags, and community statistics."""
        if not self.configured:
            return LastFMAlbumContext()

        key = f"{artist}|{album}"
        cached = self._read_cache(kind="album", key=key, model_type=LastFMAlbumContext)
        if cached is not None:
            return cached

        try:
            payload = self._get_json(
                "album.getinfo",
                {"artist": artist, "album": album, "autocorrect": 1},
            )
            context = _album_context(payload.get("album"))
        except Exception:
            return LastFMAlbumContext()

        if _album_has_data(context):
            self._write_cache(kind="album", key=key, value=context)
        return context

    def _get_json(self, method: str, params: dict[str, object]) -> dict[str, Any]:
        """Fetch JSON from Last.fm with retries and rate limiting."""
        if not self._api_key:
            return {}

        request_params = {
            **params,
            "method": method,
            "api_key": self._api_key,
            "format": "json",
        }
        with self._lock:
            self._wait_for_rate_limit()
            response = self._request_with_retries(params=request_params)
            self._last_request_at = monotonic()

        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "error" in payload:
            return {}
        return payload

    def _request_with_retries(self, *, params: dict[str, object]) -> httpx.Response:
        """Request Last.fm and retry transient failures."""
        last_error: httpx.RequestError | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(self._base_url, params=params, headers=self._headers)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == self._retries:
                    raise
                self._sleep_before_retry(attempt)
                continue

            if response.status_code not in TRANSIENT_STATUS_CODES:
                return response
            if attempt == self._retries:
                return response
            self._sleep_before_retry(attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Last.fm request retry loop exited unexpectedly.")

    def _wait_for_rate_limit(self) -> None:
        """Wait until the next Last.fm request is allowed."""
        if self._last_request_at is None or self._rate_limit_seconds <= 0:
            return

        wait_seconds = self._rate_limit_seconds - (monotonic() - self._last_request_at)
        if wait_seconds > 0:
            sleep(wait_seconds)

    def _sleep_before_retry(self, attempt: int) -> None:
        """Sleep before retrying a transient failure."""
        if self._rate_limit_seconds > 0:
            sleep(self._rate_limit_seconds * (attempt + 1))

    def _read_cache(
        self,
        *,
        kind: str,
        key: str,
        model_type: type[LastFMArtistContext] | type[LastFMAlbumContext],
    ) -> LastFMArtistContext | LastFMAlbumContext | None:
        """Read a fresh provider cache entry."""
        path = self._cache_path(kind=kind, key=key)
        if not path.exists():
            return None

        try:
            entry = _CacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
            if datetime.now(UTC) - entry.cached_at > self._cache_ttl:
                return None
            return model_type.model_validate(entry.payload)
        except ValueError:
            return None

    def _write_cache(
        self,
        *,
        kind: str,
        key: str,
        value: LastFMArtistContext | LastFMAlbumContext,
    ) -> None:
        """Persist a successful lookup."""
        entry = _CacheEntry(
            cached_at=datetime.now(UTC),
            payload=value.model_dump(mode="json", exclude_none=True),
        )
        write_text_atomic(self._cache_path(kind=kind, key=key), entry.model_dump_json(indent=2))

    def _cache_path(self, *, kind: str, key: str) -> Path:
        """Return the cache file for one lookup."""
        digest = sha256(f"{kind}:{key.strip().casefold()}".encode()).hexdigest()
        return self._cache_directory / f"{kind}-{digest}.json"


class _CacheEntry(BaseModel):
    """Serialized Last.fm provider cache entry."""

    model_config = ConfigDict(frozen=True)

    cached_at: datetime
    payload: dict[str, Any]


def normalize_tags(value: object) -> list[str]:
    """Normalize Last.fm community tags into a clean ordered list."""
    tags = value.get("tag") if isinstance(value, dict) else value
    if isinstance(tags, dict):
        tags = [tags]
    if not isinstance(tags, list):
        return []

    values: list[str] = []
    for item in tags:
        tag = item.get("name") if isinstance(item, dict) else item
        text = _string(tag)
        if text is not None:
            values.append(text)
    return _dedupe(values)


def normalize_biography(value: object) -> str | None:
    """Normalize Last.fm biography/wiki text while preserving paragraphs."""
    text = _string(value)
    if text is None:
        return None

    text = unescape(text)
    text = sub(r"<\s*br\s*/?\s*>", "\n", text, flags=2)
    text = sub(r"</\s*p\s*>", "\n\n", text, flags=2)
    text = sub(r"<[^>]+>", "", text)
    text = sub(r"\n{3,}", "\n\n", text)
    paragraphs = [" ".join(part.split()) for part in text.split("\n\n")]
    normalized = "\n\n".join(part for part in paragraphs if part)
    return normalized or None


def _artist_context(value: object) -> LastFMArtistContext:
    """Convert a Last.fm artist payload into artist context."""
    if not isinstance(value, dict):
        return LastFMArtistContext()

    bio = value.get("bio") if isinstance(value.get("bio"), dict) else {}
    stats = value.get("stats") if isinstance(value.get("stats"), dict) else {}
    similar = value.get("similar") if isinstance(value.get("similar"), dict) else {}
    return LastFMArtistContext(
        biography=normalize_biography(bio.get("content") if isinstance(bio, dict) else None),
        short_biography=normalize_biography(bio.get("summary") if isinstance(bio, dict) else None),
        tags=normalize_tags(value.get("tags")),
        similar_artists=_similar_artists(similar),
        listeners=_int(
            stats.get("listeners") if isinstance(stats, dict) else value.get("listeners")
        ),
        playcount=_int(
            stats.get("playcount") if isinstance(stats, dict) else value.get("playcount")
        ),
        url=_string(value.get("url")),
    )


def _album_context(value: object) -> LastFMAlbumContext:
    """Convert a Last.fm album payload into album context."""
    if not isinstance(value, dict):
        return LastFMAlbumContext()

    wiki = value.get("wiki") if isinstance(value.get("wiki"), dict) else {}
    return LastFMAlbumContext(
        summary=normalize_biography(wiki.get("summary") if isinstance(wiki, dict) else None),
        wiki=normalize_biography(wiki.get("content") if isinstance(wiki, dict) else None),
        tags=normalize_tags(value.get("tags")),
        listeners=_int(value.get("listeners")),
        playcount=_int(value.get("playcount")),
        url=_string(value.get("url")),
    )


def _similar_artists(value: object) -> list[str]:
    """Return normalized similar artist names."""
    artists = value.get("artist") if isinstance(value, dict) else value
    if isinstance(artists, dict):
        artists = [artists]
    if not isinstance(artists, list):
        return []
    return _dedupe(item.get("name") for item in artists if isinstance(item, dict))


def _artist_has_data(context: LastFMArtistContext) -> bool:
    """Return whether an artist context contains useful data."""
    return any(
        (
            context.biography,
            context.short_biography,
            context.tags,
            context.similar_artists,
            context.listeners,
            context.playcount,
            context.url,
        )
    )


def _album_has_data(context: LastFMAlbumContext) -> bool:
    """Return whether an album context contains useful data."""
    return any(
        (
            context.summary,
            context.wiki,
            context.tags,
            context.listeners,
            context.playcount,
            context.url,
        )
    )


def _dedupe(values: Any) -> list[str]:
    """Return populated strings with case-insensitive duplicates removed."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _string(value)
        if text is None:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _string(value: object) -> str | None:
    """Return a stripped string when populated."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: object) -> int | None:
    """Return an integer when one can be parsed."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _secret_value(value: SecretStr | str | None) -> str | None:
    """Return a plain API key value."""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return _string(value)


def _default_user_agent() -> str:
    """Return the default Last.fm User-Agent."""
    return (
        f"plex-music-enhancer/{__version__} ( https://github.com/amylasehai0z/plex-music-enhancer )"
    )
