"""MusicBrainz release-group matching service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.providers.musicbrainz import (
    MusicBrainzAlbumSearchResult,
    MusicBrainzAlias,
    MusicBrainzArtistSearchResult,
    MusicBrainzProvider,
)

try:  # pragma: no cover - exercised when rapidfuzz is installed.
    from rapidfuzz import fuzz
except ModuleNotFoundError:  # pragma: no cover - local fallback for constrained environments.
    from difflib import SequenceMatcher

    class _FallbackFuzz:
        """Small compatibility shim used only when rapidfuzz is unavailable."""

        @staticmethod
        def WRatio(left: str, right: str) -> float:  # noqa: N802
            """Return a ratio compatible with rapidfuzz's 0-100 scale."""
            return SequenceMatcher(a=left.casefold(), b=right.casefold()).ratio() * 100

    fuzz = _FallbackFuzz()


CACHE_DIRECTORY = Path("cache/musicbrainz/matches")
CACHE_TTL = timedelta(days=30)
MATCH_THRESHOLD = 75
ARTIST_THRESHOLD = 70


class MatchResult(BaseModel):
    """MusicBrainz release-group match result."""

    model_config = ConfigDict(frozen=True)

    matched: bool
    confidence: int = Field(ge=0, le=100)
    artist_mbid: str | None = None
    release_group_mbid: str | None = None
    release_mbid: str | None = None
    artist_name: str | None = None
    album_title: str | None = None
    first_release_date: str | None = None
    release_year: int | None = None
    primary_type: str | None = None
    secondary_types: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class _MusicBrainzSearchProvider(Protocol):
    """Search operations required by the matcher."""

    def search_artist(
        self,
        name: str,
        *,
        limit: int = 5,
    ) -> list[MusicBrainzArtistSearchResult]:
        """Search artists."""

    def search_album(
        self,
        artist: str,
        album: str,
        *,
        limit: int = 5,
    ) -> list[MusicBrainzAlbumSearchResult]:
        """Search albums."""


class MusicBrainzMatcher:
    """Match Plex album identity data to a MusicBrainz release-group."""

    def __init__(
        self,
        provider: _MusicBrainzSearchProvider | None = None,
        *,
        cache_directory: Path = CACHE_DIRECTORY,
        cache_ttl: timedelta = CACHE_TTL,
        match_threshold: int = MATCH_THRESHOLD,
        artist_threshold: int = ARTIST_THRESHOLD,
    ) -> None:
        """Create a MusicBrainz matcher."""
        self._provider = provider or MusicBrainzProvider()
        self._cache_directory = cache_directory
        self._cache_ttl = cache_ttl
        self._match_threshold = match_threshold
        self._artist_threshold = artist_threshold

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        """Return the highest-confidence MusicBrainz release-group match."""
        cache_key = _cache_key(artist_name=artist_name, album_title=album_title, year=release_year)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        result = self._match_album_uncached(
            artist_name=artist_name,
            album_title=album_title,
            release_year=release_year,
        )
        self._write_cache(cache_key, result)
        return result

    def _match_album_uncached(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None,
    ) -> MatchResult:
        """Run the MusicBrainz matching workflow without reading cache."""
        warnings: list[str] = []
        artist_candidates = self._provider.search_artist(artist_name, limit=10)
        if not artist_candidates:
            return _unmatched("No MusicBrainz artist candidates found.")

        artist_candidate, artist_score = _best_artist_candidate(artist_name, artist_candidates)
        if artist_score["total"] < self._artist_threshold:
            return _unmatched(
                "Best artist candidate was below the confidence threshold.",
                score_breakdown={"artist": round(artist_score["total"], 2)},
            )

        album_candidates = self._provider.search_album(artist_candidate.name, album_title, limit=10)
        if not album_candidates:
            return MatchResult(
                matched=False,
                confidence=0,
                artist_mbid=artist_candidate.mbid,
                artist_name=artist_candidate.name,
                album_title=album_title,
                score_breakdown={"artist": round(artist_score["total"], 2)},
                warnings=["No MusicBrainz release-group candidates found."],
            )

        scored_albums = [
            _score_album_candidate(
                requested_artist=artist_name,
                requested_album=album_title,
                requested_year=release_year,
                selected_artist=artist_candidate,
                candidate=candidate,
            )
            for candidate in album_candidates
        ]
        best_album, album_score = max(scored_albums, key=lambda item: item[1]["total"])
        confidence = round(album_score["total"])

        if confidence < self._match_threshold:
            warnings.append("Best release-group candidate was below the confidence threshold.")

        if album_score["year"] < 70:
            warnings.append("Release year is missing or distant from the requested year.")

        score_breakdown = {
            "artist_candidate": round(artist_score["total"], 2),
            "artist_similarity": round(album_score["artist"], 2),
            "album_similarity": round(album_score["album"], 2),
            "release_year": round(album_score["year"], 2),
            "release_type": round(album_score["type"], 2),
            "musicbrainz_score": round(album_score["musicbrainz"], 2),
        }

        return MatchResult(
            matched=confidence >= self._match_threshold,
            confidence=confidence,
            artist_mbid=artist_candidate.mbid,
            release_group_mbid=best_album.release_group_mbid,
            release_mbid=best_album.release_mbid,
            artist_name=artist_candidate.name,
            album_title=best_album.title,
            first_release_date=best_album.first_release_date,
            release_year=_year(best_album.first_release_date),
            primary_type=best_album.primary_type,
            secondary_types=best_album.secondary_types,
            score_breakdown=score_breakdown,
            warnings=warnings,
        )

    def _read_cache(self, cache_key: str) -> MatchResult | None:
        """Read a non-expired match result from cache."""
        path = self._cache_path(cache_key)
        if not path.exists():
            return None

        try:
            entry = MatchCacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        if datetime.now(tz=UTC) - entry.cached_at > self._cache_ttl:
            return None

        return entry.result

    def _write_cache(self, cache_key: str, result: MatchResult) -> None:
        """Write a match result to cache."""
        self._cache_directory.mkdir(parents=True, exist_ok=True)
        entry = MatchCacheEntry(cached_at=datetime.now(tz=UTC), result=result)
        self._cache_path(cache_key).write_text(entry.model_dump_json(indent=2), encoding="utf-8")

    def _cache_path(self, cache_key: str) -> Path:
        """Return a cache path for a match key."""
        return self._cache_directory / f"{cache_key}.json"


class MatchCacheEntry(BaseModel):
    """Serialized MusicBrainz matcher cache entry."""

    model_config = ConfigDict(frozen=True)

    cached_at: datetime
    result: MatchResult


def _best_artist_candidate(
    artist_name: str,
    candidates: Sequence[MusicBrainzArtistSearchResult],
) -> tuple[MusicBrainzArtistSearchResult, dict[str, float]]:
    """Return the highest-scoring artist candidate."""
    scored = [
        (candidate, _score_artist_candidate(artist_name, candidate)) for candidate in candidates
    ]
    return max(scored, key=lambda item: item[1]["total"])


def _score_artist_candidate(
    artist_name: str,
    candidate: MusicBrainzArtistSearchResult,
) -> dict[str, float]:
    """Score a MusicBrainz artist candidate."""
    name_score = _similarity(artist_name, candidate.name)
    alias_score = _alias_similarity(artist_name, candidate.aliases)
    exact_score = 100.0 if _matches_artist_exactly(artist_name, candidate) else 0.0
    disambiguation_score = _disambiguation_score(candidate.disambiguation)
    musicbrainz_score = float(candidate.score if candidate.score is not None else 50)
    best_name_score = max(name_score, alias_score)
    total = (
        (best_name_score * 0.55)
        + (musicbrainz_score * 0.25)
        + (exact_score * 0.15)
        + (disambiguation_score * 0.05)
    )
    return {
        "total": total,
        "name": name_score,
        "alias": alias_score,
        "exact": exact_score,
        "disambiguation": disambiguation_score,
        "musicbrainz": musicbrainz_score,
    }


def _score_album_candidate(
    *,
    requested_artist: str,
    requested_album: str,
    requested_year: int | None,
    selected_artist: MusicBrainzArtistSearchResult,
    candidate: MusicBrainzAlbumSearchResult,
) -> tuple[MusicBrainzAlbumSearchResult, dict[str, float]]:
    """Score a MusicBrainz release-group candidate."""
    artist_label = candidate.artist_name or selected_artist.name
    artist_score = _similarity(requested_artist, artist_label)
    album_score = _similarity(requested_album, candidate.title)
    year_score = _year_score(requested_year, _year(candidate.first_release_date))
    type_score = _release_type_score(candidate)
    musicbrainz_score = float(candidate.score if candidate.score is not None else 50)
    total = (
        (album_score * 0.45)
        + (artist_score * 0.25)
        + (year_score * 0.15)
        + (type_score * 0.10)
        + (musicbrainz_score * 0.05)
    )
    return (
        candidate,
        {
            "total": total,
            "artist": artist_score,
            "album": album_score,
            "year": year_score,
            "type": type_score,
            "musicbrainz": musicbrainz_score,
        },
    )


def _alias_similarity(artist_name: str, aliases: Sequence[MusicBrainzAlias]) -> float:
    """Return the best alias similarity score."""
    scores = [_similarity(artist_name, alias.name) for alias in aliases]
    return max(scores) if scores else 0.0


def _matches_artist_exactly(artist_name: str, candidate: MusicBrainzArtistSearchResult) -> bool:
    """Return whether the artist name exactly matches a candidate name or alias."""
    normalized = _normalize(artist_name)
    if normalized == _normalize(candidate.name):
        return True

    return any(normalized == _normalize(alias.name) for alias in candidate.aliases)


def _disambiguation_score(disambiguation: str | None) -> float:
    """Score MusicBrainz disambiguation text."""
    if not disambiguation:
        return 80.0

    text = disambiguation.casefold()
    if any(marker in text for marker in ("tribute", "cover", "karaoke", "impersonator")):
        return 20.0

    return 60.0


def _release_type_score(candidate: MusicBrainzAlbumSearchResult) -> float:
    """Score release type fit for a Plex album."""
    primary = (candidate.primary_type or "").casefold()
    secondary = {item.casefold() for item in candidate.secondary_types}
    if primary == "album" and "compilation" not in secondary:
        return 100.0
    if primary == "album":
        return 90.0
    if primary == "ep":
        return 55.0
    if primary == "single":
        return 30.0
    return 60.0


def _year_score(requested_year: int | None, candidate_year: int | None) -> float:
    """Score release year proximity."""
    if requested_year is None:
        return 75.0
    if candidate_year is None:
        return 60.0

    distance = abs(requested_year - candidate_year)
    if distance == 0:
        return 100.0
    if distance == 1:
        return 85.0
    if distance == 2:
        return 70.0
    return max(0.0, 50.0 - (distance * 5))


def _similarity(left: str, right: str | None) -> float:
    """Return fuzzy string similarity on a 0-100 scale."""
    if not right:
        return 0.0

    return float(fuzz.WRatio(_normalize(left), _normalize(right)))


def _year(value: str | None) -> int | None:
    """Parse a year from a MusicBrainz date."""
    if value is None or len(value) < 4:
        return None

    try:
        return int(value[:4])
    except ValueError:
        return None


def _unmatched(
    warning: str,
    *,
    score_breakdown: dict[str, float] | None = None,
) -> MatchResult:
    """Return an unmatched result."""
    return MatchResult(
        matched=False,
        confidence=0,
        score_breakdown=score_breakdown or {},
        warnings=[warning],
    )


def _cache_key(*, artist_name: str, album_title: str, year: int | None) -> str:
    """Return a stable cache key for match inputs."""
    raw = f"{_normalize(artist_name)}|{_normalize(album_title)}|{year or ''}"
    return sha256(raw.encode("utf-8")).hexdigest()


def _normalize(value: str) -> str:
    """Normalize text for matching."""
    return " ".join(value.casefold().strip().split())
