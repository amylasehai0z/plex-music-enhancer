"""High-level MusicBrainz metadata provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from plex_music_enhancer.providers.musicbrainz.client import MusicBrainzClient
from plex_music_enhancer.providers.musicbrainz.models import (
    MusicBrainzAlbumMetadata,
    MusicBrainzAlbumSearchResult,
    MusicBrainzAlias,
    MusicBrainzArtistMetadata,
    MusicBrainzArtistSearchResult,
    MusicBrainzLifeSpan,
)
from plex_music_enhancer.utils.files import write_text_atomic

CACHE_DIRECTORY = Path.home() / ".plex-enhancer" / "cache" / "musicbrainz"
CACHE_TTL = timedelta(days=30)


class MusicBrainzProvider:
    """Read-only metadata provider backed by the official MusicBrainz API."""

    name = "musicbrainz"

    def __init__(
        self,
        *,
        client: MusicBrainzClient | None = None,
        cache_directory: Path = CACHE_DIRECTORY,
        cache_ttl: timedelta = CACHE_TTL,
    ) -> None:
        """Create a MusicBrainz metadata provider."""
        self._client = client or MusicBrainzClient()
        self._cache_directory = cache_directory
        self._cache_ttl = cache_ttl

    def search_artist(
        self,
        name: str,
        *,
        limit: int = 5,
    ) -> list[MusicBrainzArtistSearchResult]:
        """Search artists by name."""
        payload = self._client.get_json(
            "/artist",
            params={"query": f'artist:"{name}"', "limit": limit},
        )
        artists = payload.get("artists")
        if not isinstance(artists, list):
            return []

        return [
            _artist_search_result(item)
            for item in artists
            if isinstance(item, dict) and _string(item.get("id")) and _string(item.get("name"))
        ]

    def search_album(
        self,
        artist: str,
        album: str,
        *,
        limit: int = 5,
    ) -> list[MusicBrainzAlbumSearchResult]:
        """Search album release-groups and enrich results with release MBIDs."""
        payload = self._client.get_json(
            "/release-group",
            params={
                "query": f'artist:"{artist}" AND releasegroup:"{album}"',
                "limit": limit,
                "type": "album",
            },
        )
        groups = payload.get("release-groups")
        if not isinstance(groups, list):
            return []

        results: list[MusicBrainzAlbumSearchResult] = []
        for item in groups:
            if not isinstance(item, dict):
                continue

            release_group_mbid = _string(item.get("id"))
            title = _string(item.get("title"))
            if release_group_mbid is None or title is None:
                continue

            results.append(
                MusicBrainzAlbumSearchResult(
                    release_group_mbid=release_group_mbid,
                    release_mbid=self._first_release_mbid(release_group_mbid),
                    title=title,
                    artist_name=_artist_credit(item),
                    first_release_date=_string(item.get("first-release-date")),
                    primary_type=_string(item.get("primary-type")),
                    secondary_types=_string_list(item.get("secondary-types")),
                    score=_int(item.get("score")),
                )
            )

        return results

    def get_artist_metadata(self, mbid: str) -> MusicBrainzArtistMetadata:
        """Return detailed artist metadata for an MBID."""
        cached = self._read_cache(mbid)
        if cached is None:
            cached = self._client.get_json(
                f"/artist/{mbid}",
                params={"inc": "aliases+tags+genres"},
            )
            self._write_cache(mbid, cached)

        life_span = _life_span(cached.get("life-span"))
        return MusicBrainzArtistMetadata(
            mbid=mbid,
            name=_string(cached.get("name")) or "",
            biography=None,
            country=_string(cached.get("country")),
            genres=_tags(cached),
            begin_date=life_span.begin if life_span else None,
            end_date=life_span.end if life_span else None,
            aliases=_aliases(cached.get("aliases")),
        )

    def get_album_metadata(self, mbid: str) -> MusicBrainzAlbumMetadata:
        """Return detailed album metadata for a release-group MBID."""
        cached = self._read_cache(mbid)
        if cached is None:
            cached = self._client.get_json(
                f"/release-group/{mbid}",
                params={
                    "inc": (
                        "artist-credits+tags+genres+artist-rels+label-rels+url-rels+"
                        "work-rels+place-rels+recording-rels"
                    )
                },
            )
            self._write_cache(mbid, cached)

        first_release_date = _string(cached.get("first-release-date"))
        return MusicBrainzAlbumMetadata(
            mbid=mbid,
            title=_string(cached.get("title")) or "",
            artist=_artist_credit(cached),
            year=_year(first_release_date),
            genres=_tag_names(cached.get("genres")),
            tags=_tag_names(cached.get("tags")),
            release_type=_release_type(cached),
            catalog_number=_catalog_number(cached),
            barcode=_string(cached.get("barcode")),
            release_country=_string(cached.get("country")),
            first_release_date=first_release_date,
            producers=_relation_names(cached, {"producer"}),
            executive_producers=_relation_names(cached, {"executive producer"}),
            composers=_relation_names(cached, {"composer"}),
            lyricists=_relation_names(cached, {"lyricist"}),
            arrangers=_relation_names(cached, {"arranger"}),
            orchestrators=_relation_names(cached, {"orchestrator"}),
            conductors=_relation_names(cached, {"conductor"}),
            mixing_engineers=_relation_names(cached, {"mix", "mixing", "mixing engineer"}),
            mastering_engineers=_relation_names(cached, {"mastering", "mastering engineer"}),
            sound_engineers=_relation_names(cached, {"engineer", "sound engineer"}),
            labels=_labels(cached),
            recording_locations=_relation_names(
                cached,
                {"recording location", "recorded at", "recorded in"},
            ),
            studios=_relation_names(cached, {"recording studio", "studio"}),
            guest_musicians=_relation_names(cached, {"guest musician", "instrument"}),
            featured_artists=_featured_artists(cached),
            orchestras=_relation_names(cached, {"orchestra"}),
            choir=_first(_relation_names(cached, {"choir"})),
            choirs=_relation_names(cached, {"choir"}),
            publisher=_first(_relation_names(cached, {"publisher"})),
            publishers=_relation_names(cached, {"publisher"}),
            secondary_genres=_tag_names(cached.get("secondary-genres")),
            certifications=_relation_names(cached, {"certification"}),
            chart_positions=_relation_names(cached, {"chart position"}),
        )

    def _first_release_mbid(self, release_group_mbid: str) -> str | None:
        """Return the first release MBID for a release-group."""
        payload = self._client.get_json(
            "/release",
            params={"release-group": release_group_mbid, "limit": 1},
        )
        releases = payload.get("releases")
        if not isinstance(releases, list) or not releases:
            return None

        first_release = releases[0]
        return _string(first_release.get("id")) if isinstance(first_release, dict) else None

    def _read_cache(self, mbid: str) -> dict[str, Any] | None:
        """Read a non-expired MBID cache entry."""
        path = self._cache_path(mbid)
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
            payload = MusicBrainzCacheEntry.model_validate_json(raw)
        except Exception:
            return None

        if datetime.now(tz=UTC) - payload.cached_at > self._cache_ttl:
            return None

        return payload.payload

    def _write_cache(self, mbid: str, payload: dict[str, Any]) -> None:
        """Write an MBID cache entry."""
        cache_entry = MusicBrainzCacheEntry(cached_at=datetime.now(tz=UTC), payload=payload)
        write_text_atomic(self._cache_path(mbid), cache_entry.model_dump_json(indent=2))

    def _cache_path(self, mbid: str) -> Path:
        """Return the cache path for an MBID."""
        return self._cache_directory / f"{mbid}.json"


class MusicBrainzCacheEntry(BaseModel):
    """Serialized MusicBrainz cache entry."""

    model_config = ConfigDict(frozen=True)

    cached_at: datetime
    payload: dict[str, Any]


def _artist_search_result(item: dict[str, Any]) -> MusicBrainzArtistSearchResult:
    """Parse an artist search result."""
    return MusicBrainzArtistSearchResult(
        mbid=_string(item.get("id")) or "",
        name=_string(item.get("name")) or "",
        sort_name=_string(item.get("sort-name")),
        country=_string(item.get("country")),
        disambiguation=_string(item.get("disambiguation")),
        tags=_tags(item),
        aliases=_aliases(item.get("aliases")),
        life_span=_life_span(item.get("life-span")),
        score=_int(item.get("score")),
    )


def _aliases(value: object) -> list[MusicBrainzAlias]:
    """Parse MusicBrainz aliases."""
    if not isinstance(value, list):
        return []

    aliases: list[MusicBrainzAlias] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        name = _string(item.get("name"))
        if name is None:
            continue

        aliases.append(
            MusicBrainzAlias(
                name=name,
                sort_name=_string(item.get("sort-name")),
                locale=_string(item.get("locale")),
                primary=_bool(item.get("primary")),
                type=_string(item.get("type")),
            )
        )

    return aliases


def _life_span(value: object) -> MusicBrainzLifeSpan | None:
    """Parse a MusicBrainz life-span object."""
    if not isinstance(value, dict):
        return None

    return MusicBrainzLifeSpan(
        begin=_string(value.get("begin")),
        end=_string(value.get("end")),
        ended=_bool(value.get("ended")),
    )


def _tags(item: dict[str, Any]) -> list[str]:
    """Parse MusicBrainz genres or tags."""
    names = _tag_names(item.get("genres"))
    if names:
        return names

    return _tag_names(item.get("tags"))


def _tag_names(value: object) -> list[str]:
    """Parse a list of MusicBrainz tag names."""
    if not isinstance(value, list):
        return []

    names: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        name = _string(item.get("name"))
        if name is not None:
            names.append(name)

    return names


def _labels(item: dict[str, Any]) -> list[str]:
    """Parse labels from MusicBrainz payloads when present."""
    names: list[str] = []
    for key in ("label-info", "labels"):
        value = item.get(key)
        if not isinstance(value, list):
            continue

        for entry in value:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            if isinstance(label, dict):
                name = _string(label.get("name"))
            else:
                name = _string(entry.get("name"))
            if name is not None:
                names.append(name)

    names.extend(_relation_names(item, {"label"}))
    return _dedupe(names)


def _catalog_number(item: dict[str, Any]) -> str | None:
    """Parse the first catalog number from MusicBrainz payloads."""
    label_info = item.get("label-info")
    if not isinstance(label_info, list):
        return None

    for entry in label_info:
        if not isinstance(entry, dict):
            continue
        catalog_number = _string(entry.get("catalog-number"))
        if catalog_number is not None:
            return catalog_number

    return None


def _featured_artists(item: dict[str, Any]) -> list[str]:
    """Parse featured artists from relations and artist credits."""
    names = _relation_names(item, {"featured", "featured artist"})
    for credit in _artist_credit_entries(item):
        joinphrase = _string(credit.get("joinphrase")) or ""
        if "feat" not in joinphrase.casefold():
            continue
        artist = credit.get("artist")
        if isinstance(artist, dict):
            name = _string(artist.get("name"))
        else:
            name = _string(credit.get("name"))
        if name is not None:
            names.append(name)

    return _dedupe(names)


def _relation_names(item: dict[str, Any], relation_types: set[str]) -> list[str]:
    """Parse relation target names for selected MusicBrainz relation types."""
    relations = item.get("relations")
    if not isinstance(relations, list):
        return []

    names: list[str] = []
    normalized_types = {relation_type.casefold() for relation_type in relation_types}
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        relation_type = _string(relation.get("type"))
        if relation_type is None or relation_type.casefold() not in normalized_types:
            continue
        name = _relation_target_name(relation)
        if name is not None:
            names.append(name)

    return _dedupe(names)


def _relation_target_name(relation: dict[str, Any]) -> str | None:
    """Return a MusicBrainz relation target display name."""
    for key in ("artist", "label", "place", "area", "url", "work"):
        value = relation.get(key)
        if isinstance(value, dict):
            name = _string(value.get("name")) or _string(value.get("resource"))
            if name is not None:
                return name

    return _string(relation.get("name")) or _string(relation.get("target"))


def _artist_credit_entries(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Return valid artist credit entries."""
    credits = item.get("artist-credit")
    if not isinstance(credits, list):
        return []
    return [credit for credit in credits if isinstance(credit, dict)]


def _first(values: list[str]) -> str | None:
    """Return the first value."""
    return values[0] if values else None


def _dedupe(values: list[str]) -> list[str]:
    """Return values without case-insensitive duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _artist_credit(item: dict[str, Any]) -> str | None:
    """Parse MusicBrainz artist-credit into a display artist."""
    credits = item.get("artist-credit")
    if not isinstance(credits, list):
        return None

    names = [
        _string(credit.get("name"))
        for credit in credits
        if isinstance(credit, dict) and _string(credit.get("name"))
    ]
    return " & ".join(names) if names else None


def _release_type(item: dict[str, Any]) -> str | None:
    """Return a normalized release type."""
    primary_type = _string(item.get("primary-type"))
    secondary_types = _string_list(item.get("secondary-types"))
    if not secondary_types:
        return primary_type

    types = [release_type for release_type in [primary_type, *secondary_types] if release_type]
    return ", ".join(types) if types else None


def _year(value: str | None) -> int | None:
    """Parse a year from a MusicBrainz date."""
    if value is None or len(value) < 4:
        return None

    try:
        return int(value[:4])
    except ValueError:
        return None


def _string_list(value: object) -> list[str]:
    """Return a list of strings."""
    if not isinstance(value, list):
        return []

    return [text for item in value if (text := _string(item)) is not None]


def _string(value: object) -> str | None:
    """Return a non-empty string."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _bool(value: object) -> bool | None:
    """Return a bool if the value is boolean."""
    return value if isinstance(value, bool) else None


def _int(value: object) -> int | None:
    """Return an int when possible."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
