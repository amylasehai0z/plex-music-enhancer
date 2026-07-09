"""Deterministic local fact verification."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from re import sub

from plex_music_enhancer.enrichment.models import AlbumContext, ArtistContext
from plex_music_enhancer.verification.models import (
    FactCollection,
    VerificationState,
    VerifiedFact,
)

SUPPORTED_CATEGORIES = (
    "release_date",
    "release_year",
    "genres",
    "styles",
    "label",
    "producer",
    "composer",
    "lyricist",
    "recording_location",
    "recording_dates",
    "personnel",
    "guest_musicians",
    "notable_tracks",
    "career_position",
)
SUPPORTED_ARTIST_CATEGORIES = (
    "full_name",
    "aliases",
    "birth_name",
    "birth_date",
    "death_date",
    "origin",
    "nationality",
    "active_years",
    "genres",
    "styles",
    "occupations",
    "members",
    "former_members",
    "associated_acts",
    "labels",
    "official_website",
    "biography",
    "career_summary",
    "historical_context",
    "influences",
    "influenced_artists",
    "notable_albums",
    "awards",
    "milestones",
)
SINGLE_VALUE_CATEGORIES = {
    "release_date",
    "release_year",
    "label",
    "recording_location",
    "recording_dates",
    "career_position",
}
SINGLE_VALUE_ARTIST_CATEGORIES = {
    "full_name",
    "birth_name",
    "birth_date",
    "death_date",
    "origin",
    "nationality",
    "active_years",
    "official_website",
}
PREFERRED_SOURCE_ORDER = ("musicbrainz", "plex", "discogs", "wikipedia", "lastfm")


@dataclass(frozen=True)
class _CandidateFact:
    """Internal provider candidate."""

    category: str
    value: str
    source: str


class FactVerifier:
    """Verify collected metadata without contacting external services."""

    def verify_album(self, context: AlbumContext) -> FactCollection:
        """Return verified facts for one album context."""
        return _verify_candidates(
            candidates=_candidates(context),
            categories=SUPPORTED_CATEGORIES,
            single_value_categories=SINGLE_VALUE_CATEGORIES,
        )

    def verify_artist(self, context: ArtistContext) -> FactCollection:
        """Return verified facts for one artist context."""
        return _verify_candidates(
            candidates=_artist_candidates(context),
            categories=SUPPORTED_ARTIST_CATEGORIES,
            single_value_categories=SINGLE_VALUE_ARTIST_CATEGORIES,
        )


def _verify_candidates(
    *,
    candidates: list[_CandidateFact],
    categories: tuple[str, ...],
    single_value_categories: set[str],
) -> FactCollection:
    """Verify grouped candidates for any entity type."""
    grouped = _group_candidates(candidates)
    facts: list[VerifiedFact] = []
    conflicts: list[VerifiedFact] = []
    missing: list[str] = []

    for category in categories:
        category_values = grouped.get(category, {})
        if not category_values:
            missing.append(category)
            facts.append(_unknown_fact(category))
            continue

        has_conflict = _has_conflict(category, category_values, single_value_categories)
        conflicting_sources = _conflicting_sources(category_values) if has_conflict else []
        for value, sources in category_values.items():
            fact = _verified_fact(
                category=category,
                value=value,
                sources=sources,
                conflicting_sources=conflicting_sources,
                conflicting=has_conflict,
            )
            facts.append(fact)
            if has_conflict:
                conflicts.append(fact)

    return FactCollection(
        facts=sorted(facts, key=lambda fact: (fact.category, -fact.confidence_score, fact.value)),
        conflicts=sorted(
            conflicts,
            key=lambda fact: (fact.category, fact.value),
        ),
        missing_facts=missing,
    )


def confidence_for_sources(*, sources: Iterable[str], conflicting: bool = False) -> float:
    """Return deterministic confidence for source support."""
    source_set = set(sources)
    if conflicting:
        return 0.30
    if {"musicbrainz", "discogs", "wikipedia"}.issubset(source_set):
        return 1.00
    if {"musicbrainz", "wikipedia"}.issubset(source_set):
        return 0.95
    if source_set == {"discogs"}:
        return 0.75
    if source_set == {"wikipedia"}:
        return 0.70
    if source_set == {"lastfm"}:
        return 0.50
    if source_set == {"musicbrainz"}:
        return 0.90
    if source_set == {"plex"}:
        return 0.80
    if "musicbrainz" in source_set:
        return 0.90
    if "discogs" in source_set:
        return 0.75
    if "wikipedia" in source_set:
        return 0.70
    if "lastfm" in source_set:
        return 0.50
    if source_set:
        return 0.40
    return 0.0


def _verified_fact(
    *,
    category: str,
    value: str,
    sources: list[str],
    conflicting_sources: list[str],
    conflicting: bool,
) -> VerifiedFact:
    """Build one verified fact."""
    confidence = confidence_for_sources(sources=sources, conflicting=conflicting)
    return VerifiedFact(
        value=value,
        category=category,
        confidence_score=confidence,
        supporting_sources=sources,
        conflicting_sources=conflicting_sources,
        preferred_source=_preferred_source(sources),
        verification_state=_state(confidence, conflicting=conflicting),
    )


def _unknown_fact(category: str) -> VerifiedFact:
    """Return an unknown placeholder fact for missing categories."""
    return VerifiedFact(
        value="",
        category=category,
        confidence_score=0.0,
        supporting_sources=[],
        conflicting_sources=[],
        preferred_source=None,
        verification_state=VerificationState.UNKNOWN,
    )


def _state(confidence: float, *, conflicting: bool) -> VerificationState:
    """Return verification state for a confidence score."""
    if conflicting:
        return VerificationState.CONFLICTING
    if confidence >= 0.90:
        return VerificationState.VERIFIED
    if confidence >= 0.70:
        return VerificationState.PROBABLE
    if confidence > 0:
        return VerificationState.WEAK
    return VerificationState.UNKNOWN


def _candidates(context: AlbumContext) -> list[_CandidateFact]:
    """Collect fact candidates from all provider contexts."""
    candidates: list[_CandidateFact] = []
    _add(candidates, "release_date", context.musicbrainz.release_date, "musicbrainz")
    _add(candidates, "release_date", context.release_date, "plex")
    _add(candidates, "release_year", _year(context.musicbrainz.release_date), "musicbrainz")
    _add(candidates, "release_year", context.plex.year, "plex")
    if _extract_mentions_year(context.wikipedia.extract, _year(context.musicbrainz.release_date)):
        _add(candidates, "release_date", context.musicbrainz.release_date, "wikipedia")
        _add(candidates, "release_year", _year(context.musicbrainz.release_date), "wikipedia")
    elif _extract_mentions_year(context.wikipedia.extract, context.plex.year):
        _add(candidates, "release_year", context.plex.year, "wikipedia")
    _add_list(candidates, "genres", context.musicbrainz.genres or context.genres, "musicbrainz")
    _add_list(candidates, "genres", context.plex.genres, "plex")
    _add_list(candidates, "genres", context.lastfm.tags, "lastfm")
    _add_list(candidates, "styles", context.plex.styles, "plex")
    _add_list(candidates, "styles", context.lastfm.tags, "lastfm")
    _add_list(candidates, "label", context.labels, "musicbrainz")
    _add_list(candidates, "label", context.discogs.labels, "discogs")
    _add_list(candidates, "producer", context.producers, "musicbrainz")
    _add_list(candidates, "producer", context.discogs.producer, "discogs")
    _add_list(candidates, "composer", context.composers, "musicbrainz")
    _add_list(candidates, "lyricist", context.lyricists, "musicbrainz")
    _add(candidates, "recording_location", context.recording_location, "musicbrainz")
    _add(candidates, "recording_location", context.discogs.recording_location, "discogs")
    _add(candidates, "recording_dates", context.recording_period, "plex")
    _add(candidates, "recording_dates", context.discogs.recording_dates, "discogs")
    _add_list(candidates, "personnel", context.featured_artists, "musicbrainz")
    _add_list(candidates, "personnel", context.discogs.personnel, "discogs")
    _add_list(candidates, "guest_musicians", context.guest_musicians, "musicbrainz")
    _add_list(candidates, "guest_musicians", context.discogs.guest_musicians, "discogs")
    _add_list(candidates, "notable_tracks", context.notable_tracks, "plex")
    _add_list(candidates, "notable_tracks", context.singles, "plex")
    _add(candidates, "career_position", context.discography_position, "plex")
    return candidates


def _artist_candidates(context: ArtistContext) -> list[_CandidateFact]:
    """Collect artist fact candidates from all provider contexts."""
    candidates: list[_CandidateFact] = []
    _add(candidates, "full_name", context.musicbrainz.artist_name, "musicbrainz")
    _add(candidates, "full_name", context.full_name, "plex")
    _add_list(candidates, "aliases", context.musicbrainz.aliases, "musicbrainz")
    _add_list(candidates, "aliases", context.discogs.aliases, "discogs")
    _add_list(candidates, "aliases", context.discogs.name_variations, "discogs")
    _add_list(candidates, "aliases", context.aliases, "plex")
    _add(candidates, "birth_name", context.birth_name, "plex")
    _add(candidates, "birth_date", context.musicbrainz.begin_date, "musicbrainz")
    _add(candidates, "birth_date", context.birth_date, "plex")
    _add(candidates, "death_date", context.musicbrainz.end_date, "musicbrainz")
    _add(candidates, "death_date", context.death_date, "plex")
    _add(candidates, "origin", context.plex.country, "plex")
    _add(candidates, "origin", context.origin, "plex")
    _add(candidates, "nationality", context.musicbrainz.country, "musicbrainz")
    _add(candidates, "nationality", context.nationality, "plex")
    _add(candidates, "active_years", context.discogs.active_years, "discogs")
    _add(
        candidates,
        "active_years",
        _career_years_value(context.active_years, birth_date=context.birth_date),
        "plex",
    )
    _add_list(candidates, "genres", context.musicbrainz.genres, "musicbrainz")
    _add_list(candidates, "genres", context.plex.genres, "plex")
    _add_list(candidates, "genres", context.discogs.genres, "discogs")
    _add_list(candidates, "genres", context.lastfm.tags, "lastfm")
    _add_list(candidates, "styles", context.discogs.styles, "discogs")
    _add_list(candidates, "styles", context.styles, "plex")
    _add_list(candidates, "occupations", context.occupations, "plex")
    _add_list(candidates, "members", context.discogs.members, "discogs")
    _add_list(candidates, "members", context.members, "plex")
    _add_list(candidates, "former_members", context.former_members, "plex")
    _add_list(candidates, "associated_acts", context.associated_acts, "plex")
    _add_list(candidates, "labels", context.labels, "plex")
    _add(candidates, "official_website", context.official_website, "plex")
    _add(candidates, "biography", context.wikipedia.extract, "wikipedia")
    _add(candidates, "biography", context.lastfm.biography, "lastfm")
    _add(candidates, "biography", context.discogs.profile, "discogs")
    _add(candidates, "biography", context.plex.summary, "plex")
    _add(candidates, "career_summary", context.lastfm.short_biography, "lastfm")
    _add(candidates, "career_summary", context.career_summary, "wikipedia")
    _add(candidates, "historical_context", context.wikipedia.extract, "wikipedia")
    _add(candidates, "historical_context", context.historical_context, "plex")
    _add_list(candidates, "influences", context.influences, "plex")
    _add_list(candidates, "influenced_artists", context.influenced_artists, "plex")
    _add_list(candidates, "notable_albums", context.notable_albums, "plex")
    _add_list(candidates, "awards", context.awards, "plex")
    _add_list(candidates, "milestones", context.milestones, "plex")
    return candidates


def _group_candidates(
    candidates: list[_CandidateFact],
) -> dict[str, dict[str, list[str]]]:
    """Group candidates by category and normalized value."""
    grouped: dict[str, dict[str, list[str]]] = defaultdict(dict)
    display_values: dict[tuple[str, str], str] = {}
    for candidate in candidates:
        key = _normalize(candidate.value)
        display_values.setdefault((candidate.category, key), candidate.value)
        value = display_values[(candidate.category, key)]
        sources = grouped[candidate.category].setdefault(value, [])
        if candidate.source not in sources:
            sources.append(candidate.source)
    return dict(grouped)


def _has_conflict(
    category: str,
    values: dict[str, list[str]],
    single_value_categories: set[str],
) -> bool:
    """Return whether a category contains conflicting provider values."""
    if len(values) <= 1:
        return False
    return category in single_value_categories


def _conflicting_sources(values: dict[str, list[str]]) -> list[str]:
    """Return all sources participating in a conflict."""
    return _dedupe(source for sources in values.values() for source in sources)


def _preferred_source(sources: list[str]) -> str | None:
    """Return the highest-priority source."""
    for source in PREFERRED_SOURCE_ORDER:
        if source in sources:
            return source
    return sources[0] if sources else None


def _add(
    candidates: list[_CandidateFact],
    category: str,
    value: object,
    source: str,
) -> None:
    """Add one candidate value."""
    text = _string(value)
    if text:
        candidates.append(_CandidateFact(category=category, value=text, source=source))


def _career_years_value(value: str | None, *, birth_date: str | None) -> str | None:
    """Return career years only when they are not accidentally a birth date."""
    text = _string(value)
    if text is None:
        return None
    if birth_date and _normalize(text) == _normalize(birth_date):
        return None
    if "-" in text or "–" in text or "present" in text.casefold():
        return text
    return text if len(text) == 4 and text.isdigit() else None


def _add_list(
    candidates: list[_CandidateFact],
    category: str,
    values: Iterable[object],
    source: str,
) -> None:
    """Add candidate values from a list."""
    for value in values:
        _add(candidates, category, value, source)


def _year(value: str | None) -> str | None:
    """Return a four-digit year from a date-like value."""
    return value[:4] if value and len(value) >= 4 else None


def _extract_mentions_year(extract: str | None, year: object) -> bool:
    """Return whether a prose extract mentions a release year."""
    if extract is None or year is None:
        return False
    return str(year) in extract


def _normalize(value: str) -> str:
    """Return a normalized comparison key."""
    return sub(r"\s+", " ", value.strip().casefold())


def _string(value: object) -> str | None:
    """Return a stripped string."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe(values: Iterable[str]) -> list[str]:
    """Return values with case-insensitive duplicates removed."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
