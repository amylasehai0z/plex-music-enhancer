"""Read-only Discogs metadata provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from re import sub
from threading import Lock
from time import monotonic, sleep
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from plex_music_enhancer.constants import __version__
from plex_music_enhancer.enrichment.models import DiscogsAlbumContext, DiscogsArtistContext
from plex_music_enhancer.utils.files import write_text_atomic

DISCOGS_BASE_URL = "https://api.discogs.com"
DEFAULT_CACHE_DIRECTORY = Path.home() / ".plex-enhancer" / "cache" / "discogs"
DEFAULT_CACHE_TTL = timedelta(days=30)
DEFAULT_RATE_LIMIT_SECONDS = 1.0
DEFAULT_RETRIES = 2
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class DiscogsProvider:
    """Optional read-only metadata provider backed by the Discogs API."""

    name = "discogs"

    def __init__(
        self,
        *,
        token: SecretStr | str | None = None,
        http_client: httpx.Client | None = None,
        base_url: str = DISCOGS_BASE_URL,
        cache_directory: Path = DEFAULT_CACHE_DIRECTORY,
        cache_ttl: timedelta = DEFAULT_CACHE_TTL,
        timeout_seconds: float = 10.0,
        rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        user_agent: str | None = None,
    ) -> None:
        """Create a Discogs provider.

        When no token is configured, lookups return empty context objects without network access.
        """
        self._token = _secret_value(token)
        self._base_url = base_url.rstrip("/")
        self._cache_directory = cache_directory
        self._cache_ttl = cache_ttl
        self._rate_limit_seconds = rate_limit_seconds
        self._retries = retries
        self._lock = Lock()
        self._last_request_at: float | None = None
        self._headers = {
            "Accept": "application/vnd.discogs.v2.discogs+json",
            "User-Agent": user_agent or _default_user_agent(),
        }
        self._client = http_client or httpx.Client(timeout=timeout_seconds, headers=self._headers)

    @property
    def configured(self) -> bool:
        """Return whether the provider has credentials and may perform network lookups."""
        return bool(self._token)

    def lookup_artist(self, artist: str) -> DiscogsArtistContext:
        """Lookup Discogs artist metadata by name."""
        if not self.configured:
            return DiscogsArtistContext()

        cached = self._read_cache(kind="artist", key=artist, model_type=DiscogsArtistContext)
        if cached is not None:
            return cached

        try:
            artist_id = self._search_id(query=artist, search_type="artist")
            if artist_id is None:
                return DiscogsArtistContext()

            payload = self._get_json(f"/artists/{artist_id}", params={})
            context = _artist_context(payload)
        except Exception:
            return DiscogsArtistContext()

        if _artist_has_data(context):
            self._write_cache(kind="artist", key=artist, value=context)
        return context

    def lookup_album(self, artist: str, album: str) -> DiscogsAlbumContext:
        """Lookup Discogs release metadata by artist and album title."""
        if not self.configured:
            return DiscogsAlbumContext()

        key = f"{artist}|{album}"
        cached = self._read_cache(kind="album", key=key, model_type=DiscogsAlbumContext)
        if cached is not None:
            return cached

        try:
            release_id = self._search_id(
                query=f"{artist} {album}",
                search_type="release",
                params={"artist": artist, "release_title": album},
            )
            if release_id is None:
                return DiscogsAlbumContext()

            payload = self._get_json(f"/releases/{release_id}", params={})
            context = _album_context(payload)
        except Exception:
            return DiscogsAlbumContext()

        if _album_has_data(context):
            self._write_cache(kind="album", key=key, value=context)
        return context

    def _search_id(
        self,
        *,
        query: str,
        search_type: str,
        params: dict[str, object] | None = None,
    ) -> int | None:
        """Return the first Discogs search result ID."""
        payload = self._get_json(
            "/database/search",
            params={"q": query, "type": search_type, "per_page": 1, **(params or {})},
        )
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None

        first = results[0]
        return _int(first.get("id")) if isinstance(first, dict) else None

    def _get_json(self, endpoint: str, *, params: dict[str, object]) -> dict[str, Any]:
        """Fetch JSON from Discogs with retries and rate limiting."""
        if not self._token:
            return {}

        request_params = {**params, "token": self._token}
        with self._lock:
            self._wait_for_rate_limit()
            response = self._request_with_retries(endpoint, params=request_params)
            self._last_request_at = monotonic()

        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _request_with_retries(
        self,
        endpoint: str,
        *,
        params: dict[str, object],
    ) -> httpx.Response:
        """Request an endpoint and retry transient failures."""
        last_error: httpx.RequestError | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(
                    f"{self._base_url}/{endpoint.lstrip('/')}",
                    params=params,
                    headers=self._headers,
                )
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

        raise RuntimeError("Discogs request retry loop exited unexpectedly.")

    def _wait_for_rate_limit(self) -> None:
        """Wait until the next Discogs request is allowed."""
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
        model_type: type[DiscogsArtistContext] | type[DiscogsAlbumContext],
    ) -> DiscogsArtistContext | DiscogsAlbumContext | None:
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
        value: DiscogsArtistContext | DiscogsAlbumContext,
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
    """Serialized Discogs provider cache entry."""

    model_config = ConfigDict(frozen=True)

    cached_at: datetime
    payload: dict[str, Any]


def normalize_credit_role(role: str) -> str | None:
    """Normalize a Discogs free-form role into a structured credit field."""
    normalized = sub(r"[^a-z0-9]+", " ", role.casefold()).strip()
    if not normalized:
        return None

    if "master" in normalized:
        return "mastering"
    if "mix" in normalized:
        return "mixed_by"
    if "producer" in normalized or "produced by" in normalized:
        return "producer"
    if "engineer" in normalized:
        return "engineer"
    if "photograph" in normalized:
        return "photography"
    if "artwork" in normalized or "art work" in normalized:
        return "artwork"
    if "design" in normalized:
        return "design"
    if "recorded at" in normalized or "recorded in" in normalized:
        return "recording_location"
    if "guest" in normalized or "feat" in normalized:
        return "guest_musicians"
    if any(marker in normalized for marker in ("guitar", "bass", "drum", "piano", "vocal")):
        return "personnel"
    return None


def _album_context(payload: dict[str, Any]) -> DiscogsAlbumContext:
    """Convert a Discogs release payload into album context."""
    credits = _normalized_credits(_release_credits(payload))
    labels, catalog_numbers = _labels(payload.get("labels"))
    formats = _formats(payload.get("formats"))
    recording_locations = credits.pop("recording_location", [])

    return DiscogsAlbumContext(
        label=_first(labels),
        labels=labels,
        catalog_number=_first(catalog_numbers),
        catalog_numbers=catalog_numbers,
        country=_string(payload.get("country")),
        formats=formats,
        producer=credits.pop("producer", []),
        engineer=credits.pop("engineer", []),
        mastering=credits.pop("mastering", []),
        mixed_by=credits.pop("mixed_by", []),
        photography=credits.pop("photography", []),
        artwork=credits.pop("artwork", []),
        design=credits.pop("design", []),
        recording_location=_first(recording_locations),
        recording_locations=recording_locations,
        recording_dates=_string(payload.get("released")),
        personnel=credits.pop("personnel", []),
        guest_musicians=credits.pop("guest_musicians", []),
        credits=_generic_credits(credits),
        notes=_string(payload.get("notes")),
    )


def _artist_context(payload: dict[str, Any]) -> DiscogsArtistContext:
    """Convert a Discogs artist payload into artist context."""
    return DiscogsArtistContext(
        profile=_string(payload.get("profile")),
        members=_name_list(payload.get("members")),
        aliases=_name_list(payload.get("aliases")),
        name_variations=_string_list(payload.get("namevariations")),
        genres=_string_list(payload.get("genres")),
        styles=_string_list(payload.get("styles")),
        active_years=_string(payload.get("active_years")),
    )


def _release_credits(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Return all release-level and track-level Discogs credit pairs."""
    pairs = _credit_pairs(payload.get("extraartists"))
    tracklist = payload.get("tracklist")
    if isinstance(tracklist, list):
        for track in tracklist:
            if isinstance(track, dict):
                pairs.extend(_credit_pairs(track.get("extraartists")))
    return pairs


def _credit_pairs(value: object) -> list[tuple[str, str]]:
    """Return ``(name, role)`` pairs from Discogs extraartist payloads."""
    if not isinstance(value, list):
        return []

    pairs: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _string(item.get("name"))
        role = _string(item.get("role"))
        if name is not None and role is not None:
            pairs.append((name, role))
    return pairs


def _normalized_credits(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Group Discogs credits by normalized role."""
    grouped: dict[str, list[str]] = {}
    for name, role in pairs:
        field = normalize_credit_role(role) or "credits"
        grouped.setdefault(field, []).append(f"{name} ({role})" if field == "credits" else name)
    return {key: _dedupe(values) for key, values in grouped.items()}


def _generic_credits(grouped: dict[str, list[str]]) -> list[str]:
    """Return uncategorized credits after structured fields were removed."""
    values: list[str] = []
    for items in grouped.values():
        values.extend(items)
    return _dedupe(values)


def _labels(value: object) -> tuple[list[str], list[str]]:
    """Return Discogs label names and catalog numbers."""
    if not isinstance(value, list):
        return [], []

    labels: list[str] = []
    catalog_numbers: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = _string(item.get("name"))
        catalog_number = _string(item.get("catno"))
        if label is not None:
            labels.append(label)
        if catalog_number is not None and catalog_number.casefold() != "none":
            catalog_numbers.append(catalog_number)
    return _dedupe(labels), _dedupe(catalog_numbers)


def _formats(value: object) -> list[str]:
    """Return normalized Discogs format names."""
    if not isinstance(value, list):
        return []

    formats: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        parts = [_string(item.get("name")), *_string_list(item.get("descriptions"))]
        formats.append(", ".join(part for part in parts if part))
    return _dedupe(formats)


def _name_list(value: object) -> list[str]:
    """Return names from Discogs list objects."""
    if not isinstance(value, list):
        return []
    return _dedupe(_string(item.get("name")) for item in value if isinstance(item, dict))


def _string_list(value: object) -> list[str]:
    """Return strings from a list payload."""
    if not isinstance(value, list):
        return []
    return _dedupe(_string(item) for item in value)


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


def _artist_has_data(context: DiscogsArtistContext) -> bool:
    """Return whether an artist context contains useful data."""
    return any(
        (
            context.profile,
            context.members,
            context.aliases,
            context.name_variations,
            context.genres,
            context.styles,
            context.active_years,
        )
    )


def _album_has_data(context: DiscogsAlbumContext) -> bool:
    """Return whether an album context contains useful data."""
    return any(
        (
            context.label,
            context.labels,
            context.catalog_number,
            context.catalog_numbers,
            context.country,
            context.formats,
            context.producer,
            context.engineer,
            context.mastering,
            context.mixed_by,
            context.recording_location,
            context.recording_dates,
            context.personnel,
            context.guest_musicians,
            context.credits,
            context.notes,
        )
    )


def _first(values: list[str]) -> str | None:
    """Return the first value from a list."""
    return values[0] if values else None


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
    """Return a plain token value."""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return _string(value)


def _default_user_agent() -> str:
    """Return the default Discogs User-Agent."""
    return f"plex-music-enhancer/{__version__} ( https://github.com/plex-music-enhancer )"
