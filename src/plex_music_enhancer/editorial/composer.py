"""Editorial composition from normalized enrichment context."""

from __future__ import annotations

from collections.abc import Iterable
from re import sub

from plex_music_enhancer.editorial.models import EditorialContext, EditorialFact, FactConfidence
from plex_music_enhancer.enrichment.models import AlbumContext
from plex_music_enhancer.verification import FactVerifier, VerificationState
from plex_music_enhancer.verification.models import FactCollection, VerifiedFact

SOURCE_WEIGHTS = {
    "plex": 30,
    "musicbrainz": 35,
    "wikipedia": 30,
    "discogs": 25,
    "lastfm": 12,
    "knowledge_graph": 18,
}


class EditorialComposer:
    """Prepare structured writing guidance from an album context without generating prose."""

    def compose_album(self, context: AlbumContext) -> EditorialContext:
        """Return an editorial context for one album."""
        fact_collection = _fact_collection(context)
        facts = _FactCollector()
        release_date = context.release_date or context.musicbrainz.release_date
        if release_date is None and context.plex.year is not None:
            release_date = str(context.plex.year)

        _add_release_facts(facts, context, release_date, fact_collection)
        _add_career_facts(facts, context, fact_collection)
        _add_recording_facts(facts, context, fact_collection)
        _add_style_facts(facts, context, fact_collection)
        _add_production_facts(facts, context, fact_collection)
        _add_personnel_facts(facts, context, fact_collection)
        _add_lyrical_facts(facts, context, fact_collection)
        _add_historical_facts(facts, context)
        _add_legacy_facts(facts, context)

        section_map = {
            "opening_focus": _opening_focus(context, release_date),
            "career_context": facts.section("career_context"),
            "recording_context": facts.section("recording_context"),
            "musical_style": facts.section("musical_style"),
            "production_context": facts.section("production_context"),
            "personnel_context": facts.section("personnel_context"),
            "lyrical_context": facts.section("lyrical_context"),
            "historical_context": facts.section("historical_context"),
            "legacy_context": facts.section("legacy_context"),
        }
        order = _story_order(section_map)
        missing_context = _missing_context(context, release_date)
        return EditorialContext(
            opening_focus=section_map["opening_focus"],
            career_context=section_map["career_context"],
            recording_context=section_map["recording_context"],
            musical_style=section_map["musical_style"],
            production_context=section_map["production_context"],
            personnel_context=section_map["personnel_context"],
            lyrical_context=section_map["lyrical_context"],
            historical_context=section_map["historical_context"],
            legacy_context=section_map["legacy_context"],
            recommended_story_order=order,
            notable_tracks=_dedupe(
                [
                    *context.notable_tracks,
                    *context.album_highlights,
                    *context.singles,
                    *context.hit_singles,
                    *context.promotional_singles,
                ]
            )
            or None,
            important_facts=facts.important(),
            avoid_topics=_avoid_topics(missing_context),
            missing_context=missing_context,
            writing_guidance=_writing_guidance(),
            verified_facts=_facts_by_state(fact_collection, VerificationState.VERIFIED),
            probable_facts=_facts_by_state(fact_collection, VerificationState.PROBABLE),
            weak_facts=_facts_by_state(fact_collection, VerificationState.WEAK),
            conflicting_facts=fact_collection.conflicts or None,
            missing_facts=fact_collection.missing_facts or None,
        )


class _FactCollector:
    """Collect and deduplicate editorial facts."""

    def __init__(self) -> None:
        self._facts: dict[str, EditorialFact] = {}
        self._sections: dict[str, list[str]] = {}

    def add(
        self,
        section: str,
        *,
        topic: str,
        text: str | None,
        sources: Iterable[str],
    ) -> None:
        """Add one fact when populated."""
        if not text:
            return

        source_list = _dedupe(list(sources))
        if not source_list:
            return
        key = _fact_key(topic=topic, text=text)
        existing = self._facts.get(key)
        if existing is not None:
            source_list = _dedupe([*existing.sources, *source_list])

        fact = EditorialFact(
            topic=topic,
            text=text,
            sources=source_list,
            priority=_priority(source_list),
            confidence=_confidence(source_list),
        )
        self._facts[key] = fact
        self._sections.setdefault(section, [])
        if key not in self._sections[section]:
            self._sections[section].append(key)

    def section(self, name: str) -> list[EditorialFact] | None:
        """Return facts for a section sorted by priority."""
        facts = [self._facts[key] for key in self._sections.get(name, [])]
        return _sort_facts(facts) or None

    def important(self) -> list[EditorialFact] | None:
        """Return all facts sorted by editorial priority."""
        return _sort_facts(self._facts.values()) or None


def render_editorial_context(context: EditorialContext) -> str:
    """Render editorial context as compact prompt guidance."""
    lines: list[str] = []
    _append_value(lines, "Opening focus", context.opening_focus)
    _append_list(lines, "Recommended story order", context.recommended_story_order)
    _append_facts(lines, "Most important facts", context.important_facts)
    _append_facts(lines, "Career context", context.career_context)
    _append_facts(lines, "Recording context", context.recording_context)
    _append_facts(lines, "Musical style", context.musical_style)
    _append_facts(lines, "Production context", context.production_context)
    _append_facts(lines, "Personnel context", context.personnel_context)
    _append_facts(lines, "Lyrical context", context.lyrical_context)
    _append_facts(lines, "Historical context", context.historical_context)
    _append_facts(lines, "Legacy context", context.legacy_context)
    _append_list(lines, "Notable tracks", context.notable_tracks)
    _append_verified(lines, "Verified facts", context.verified_facts)
    _append_verified(lines, "Probable facts", context.probable_facts)
    _append_verified(lines, "Weak facts", context.weak_facts)
    _append_verified(lines, "Conflicting facts", context.conflicting_facts)
    _append_list(lines, "Missing facts", context.missing_facts)
    _append_list(lines, "Writing guidance", context.writing_guidance)
    _append_list(lines, "Do not invent missing context", context.missing_context)
    _append_list(lines, "Avoid topics", context.avoid_topics)
    return "\n".join(lines) if lines else "No editorial guidance available."


def _add_release_facts(
    facts: _FactCollector,
    context: AlbumContext,
    release_date: str | None,
    fact_collection: FactCollection,
) -> None:
    sources = []
    if context.musicbrainz.release_date:
        sources.append("musicbrainz")
    if context.plex.year is not None:
        sources.append("plex")
    if (
        context.wikipedia.extract
        and context.plex.year
        and str(context.plex.year) in context.wikipedia.extract
    ):
        sources.append("wikipedia")
    facts.add(
        "opening_focus",
        topic="release_date",
        text=f"Release date: {release_date}" if release_date else None,
        sources=_verified_sources(
            fact_collection,
            "release_date",
            release_date,
            fallback=sources or ["plex"],
        ),
    )
    facts.add(
        "opening_focus",
        topic="album_identity",
        text=f"{context.plex.album} by {context.plex.artist}",
        sources=["plex"],
    )


def _add_career_facts(
    facts: _FactCollector,
    context: AlbumContext,
    fact_collection: FactCollection,
) -> None:
    facts.add("career_context", topic="career_phase", text=context.career_phase, sources=["plex"])
    facts.add(
        "career_context",
        topic="discography_position",
        text=context.discography_position,
        sources=_verified_sources(
            fact_collection,
            "career_position",
            context.discography_position,
            fallback=["plex"],
        ),
    )
    facts.add(
        "career_context",
        topic="previous_album",
        text=_related_album("Previous album", context.previous_album, context.previous_album_year),
        sources=["plex"],
    )
    facts.add(
        "career_context",
        topic="next_album",
        text=_related_album("Next album", context.next_album, context.next_album_year),
        sources=["plex"],
    )
    facts.add(
        "career_context",
        topic="artist_biography",
        text=context.lastfm_artist.short_biography or context.lastfm_artist.biography,
        sources=["lastfm"],
    )


def _add_recording_facts(
    facts: _FactCollector,
    context: AlbumContext,
    fact_collection: FactCollection,
) -> None:
    facts.add(
        "recording_context",
        topic="recording_period",
        text=context.recording_period,
        sources=_verified_sources(
            fact_collection,
            "recording_dates",
            context.recording_period,
            fallback=_sources_for_value(
                context.recording_period, {"discogs": context.discogs.recording_dates}
            ),
        ),
    )
    facts.add(
        "recording_context",
        topic="recording_location",
        text=context.recording_location,
        sources=_verified_sources(
            fact_collection,
            "recording_location",
            context.recording_location,
            fallback=_sources_for_value(
                context.recording_location,
                {
                    "discogs": context.discogs.recording_location,
                    "musicbrainz": context.recording_location,
                },
            ),
        ),
    )
    facts.add(
        "recording_context",
        topic="recording_location",
        text=context.discogs.recording_location,
        sources=_verified_sources(
            fact_collection,
            "recording_location",
            context.discogs.recording_location,
            fallback=["discogs"],
        ),
    )
    facts.add(
        "recording_context",
        topic="recording_dates",
        text=context.discogs.recording_dates,
        sources=_verified_sources(
            fact_collection,
            "recording_dates",
            context.discogs.recording_dates,
            fallback=["discogs"],
        ),
    )
    for studio in context.studios:
        facts.add(
            "recording_context",
            topic="studio",
            text=f"Studio: {studio}",
            sources=["musicbrainz"],
        )


def _add_style_facts(
    facts: _FactCollector,
    context: AlbumContext,
    fact_collection: FactCollection,
) -> None:
    genres = _dedupe([*context.genres, *context.musicbrainz.genres, *context.plex.genres])
    facts.add(
        "musical_style",
        topic="genres",
        text=f"Genres: {', '.join(genres)}" if genres else None,
        sources=_verified_sources(
            fact_collection,
            "genres",
            genres[0] if genres else None,
            fallback=_genre_sources(context),
        ),
    )
    facts.add(
        "musical_style",
        topic="community_tags",
        text=(
            "Community style tags: "
            f"{', '.join(_dedupe(context.lastfm_artist.tags + context.lastfm.tags))}"
            if context.lastfm_artist.tags or context.lastfm.tags
            else None
        ),
        sources=["lastfm"],
    )
    facts.add(
        "musical_style",
        topic="genre_evolution",
        text=f"Genre evolution: {context.genre_evolution}" if context.genre_evolution else None,
        sources=["plex"],
    )
    for highlight in context.stylistic_highlights:
        facts.add("musical_style", topic="stylistic_highlight", text=highlight, sources=["plex"])


def _add_production_facts(
    facts: _FactCollector,
    context: AlbumContext,
    fact_collection: FactCollection,
) -> None:
    for producer in _dedupe([*context.producers, *context.discogs.producer]):
        facts.add(
            "production_context",
            topic="producer",
            text=f"Producer: {producer}",
            sources=_verified_sources(
                fact_collection,
                "producer",
                producer,
                fallback=_producer_sources(producer, context),
            ),
        )
    for label in context.labels:
        facts.add(
            "production_context",
            topic="label",
            text=f"Label: {label}",
            sources=_verified_sources(
                fact_collection,
                "label",
                label,
                fallback=_label_sources(label, context),
            ),
        )
    facts.add(
        "production_context",
        topic="catalog_number",
        text=f"Catalog number: {context.catalog_number}" if context.catalog_number else None,
        sources=(
            ["musicbrainz", "discogs"]
            if context.catalog_number in context.discogs.catalog_numbers
            else ["musicbrainz"]
        ),
    )


def _add_personnel_facts(
    facts: _FactCollector,
    context: AlbumContext,
    fact_collection: FactCollection,
) -> None:
    for engineer in context.sound_engineers:
        facts.add(
            "personnel_context",
            topic="engineer",
            text=f"Engineer: {engineer}",
            sources=_person_sources(engineer, context.discogs.engineer),
        )
    for engineer in context.mixing_engineers:
        facts.add(
            "personnel_context",
            topic="mixing",
            text=f"Mixed by: {engineer}",
            sources=_person_sources(engineer, context.discogs.mixed_by),
        )
    for engineer in context.mastering_engineers:
        facts.add(
            "personnel_context",
            topic="mastering",
            text=f"Mastering: {engineer}",
            sources=_person_sources(engineer, context.discogs.mastering),
        )
    for musician in _dedupe([*context.guest_musicians, *context.featured_artists]):
        facts.add(
            "personnel_context",
            topic="guest_musician",
            text=f"Guest musician: {musician}",
            sources=_verified_sources(
                fact_collection,
                "guest_musicians",
                musician,
                fallback=_person_sources(
                    musician, context.discogs.guest_musicians + context.discogs.personnel
                ),
            ),
        )


def _add_lyrical_facts(
    facts: _FactCollector,
    context: AlbumContext,
    fact_collection: FactCollection,
) -> None:
    for composer in context.composers:
        facts.add(
            "lyrical_context",
            topic="composer",
            text=f"Composer: {composer}",
            sources=_verified_sources(
                fact_collection,
                "composer",
                composer,
                fallback=["musicbrainz"],
            ),
        )
    for lyricist in context.lyricists:
        facts.add(
            "lyrical_context",
            topic="lyricist",
            text=f"Lyricist: {lyricist}",
            sources=_verified_sources(
                fact_collection,
                "lyricist",
                lyricist,
                fallback=["musicbrainz"],
            ),
        )
    for theme in context.recurring_themes:
        facts.add(
            "lyrical_context",
            topic="theme",
            text=f"Recurring theme: {theme}",
            sources=["plex"],
        )


def _add_historical_facts(facts: _FactCollector, context: AlbumContext) -> None:
    facts.add(
        "historical_context",
        topic="historical_context",
        text=(
            f"Historical context: {context.historical_context}"
            if context.historical_context
            else None
        ),
        sources=["plex"],
    )
    facts.add(
        "historical_context",
        topic="wikipedia_extract",
        text=context.wikipedia.extract,
        sources=["wikipedia"],
    )
    facts.add(
        "historical_context",
        topic="lastfm_album_summary",
        text=context.lastfm.summary,
        sources=["lastfm"],
    )
    for summary in context.knowledge_graph.summaries:
        facts.add(
            "historical_context",
            topic="knowledge_graph",
            text=summary,
            sources=["knowledge_graph"],
        )


def _add_legacy_facts(facts: _FactCollector, context: AlbumContext) -> None:
    facts.add(
        "legacy_context",
        topic="legacy_summary",
        text=context.legacy_summary,
        sources=["plex"],
    )
    facts.add(
        "legacy_context",
        topic="commercial_summary",
        text=context.commercial_summary,
        sources=["plex"],
    )
    facts.add(
        "legacy_context",
        topic="critical_consensus",
        text=context.critical_consensus,
        sources=["plex"],
    )


def _opening_focus(context: AlbumContext, release_date: str | None) -> str:
    """Return a concise opening recommendation."""
    bits = [context.plex.album, f"by {context.plex.artist}"]
    if release_date:
        bits.append(f"released {release_date}")
    if context.discography_position:
        bits.append(context.discography_position)
    return "; ".join(bits)


def _story_order(section_map: dict[str, object]) -> list[str]:
    """Return a logical story order, omitting unavailable sections."""
    candidates = [
        ("opening_focus", "Studio album"),
        ("career_context", "Career placement"),
        ("recording_context", "Recording"),
        ("musical_style", "Musical style"),
        ("production_context", "Production"),
        ("personnel_context", "Personnel"),
        ("lyrical_context", "Songwriting and themes"),
        ("historical_context", "Historical significance"),
        ("legacy_context", "Closing classification"),
    ]
    return [label for key, label in candidates if section_map.get(key)]


def _missing_context(context: AlbumContext, release_date: str | None) -> list[str] | None:
    """Return missing factual areas that must not be invented."""
    missing: list[str] = []
    if not release_date:
        missing.append("release date")
    if not (context.genres or context.musicbrainz.genres or context.plex.genres):
        missing.append("genres")
    if not (
        context.artist_history
        or context.career_phase
        or context.discography_position
        or context.lastfm_artist.biography
    ):
        missing.append("artist context")
    if not context.producers:
        missing.append("producer")
    if not context.labels:
        missing.append("label")
    if not (context.recording_period or context.recording_location or context.studios):
        missing.append("recording information")
    return missing or None


def _avoid_topics(missing_context: list[str] | None) -> list[str] | None:
    """Return topics the prompt should avoid inventing."""
    base = [
        "chart positions unless explicitly supplied",
        "certifications unless explicitly supplied",
        "reviews or reception unless explicitly supplied",
        "influence or legacy unless explicitly supplied",
        "community opinion as objective fact",
    ]
    if missing_context:
        base.extend(f"unsupplied {item}" for item in missing_context)
    return base


def _writing_guidance() -> list[str]:
    """Return reusable writing guidance for German album prose."""
    return [
        "begin with the album's role in the artist's career when supported",
        "prefer chronological storytelling",
        "integrate production facts naturally",
        "mention personnel only if relevant",
        "emphasize verified facts and treat weak facts as background only",
        "never resolve conflicting facts by guessing",
        "avoid isolated fact lists",
        "avoid repetitive sentence openings",
    ]


def _fact_collection(context: AlbumContext) -> FactCollection:
    """Return the context fact collection, computing it when absent."""
    if context.fact_collection.facts:
        return context.fact_collection
    return FactVerifier().verify_album(context)


def _facts_by_state(
    collection: FactCollection,
    state: VerificationState,
) -> list[VerifiedFact] | None:
    """Return useful facts for one verification state."""
    facts = [
        fact
        for fact in collection.by_state(state)
        if fact.value and fact.verification_state != VerificationState.CONFLICTING
    ]
    return _sort_verified(facts) or None


def _sort_verified(facts: Iterable[VerifiedFact]) -> list[VerifiedFact]:
    """Sort verified facts by confidence and stable category."""
    return sorted(facts, key=lambda fact: (-fact.confidence_score, fact.category, fact.value))


def _verified_sources(
    collection: FactCollection,
    category: str,
    value: str | None,
    *,
    fallback: list[str],
) -> list[str]:
    """Return fact-backed sources, omitting conflicting values from narrative use."""
    fact = _matching_fact(collection, category, value)
    if fact is None:
        return fallback
    if fact.verification_state == VerificationState.CONFLICTING:
        return []
    return fact.supporting_sources or fallback


def _matching_fact(
    collection: FactCollection,
    category: str,
    value: str | None,
) -> VerifiedFact | None:
    """Return the verified fact matching a category/value pair."""
    if value is None:
        return None
    for fact in collection.by_category(category):
        if fact.value and _same_value(fact.value, value):
            return fact
    return None


def _priority(sources: list[str]) -> int:
    """Return a priority score based on source support."""
    weighted = sum(SOURCE_WEIGHTS.get(source, 10) for source in set(sources))
    return min(100, 20 + weighted)


def _confidence(sources: list[str]) -> FactConfidence:
    """Return confidence label based on source support."""
    priority = _priority(sources)
    if priority >= 75:
        return "high"
    if priority >= 45:
        return "medium"
    return "low"


def _sort_facts(facts: Iterable[EditorialFact]) -> list[EditorialFact]:
    """Sort facts by priority and stable text."""
    return sorted(facts, key=lambda fact: (-fact.priority, fact.topic, fact.text))


def _fact_key(*, topic: str, text: str) -> str:
    """Return a dedupe key for a fact."""
    normalized = sub(r"\s+", " ", text.casefold()).strip()
    return f"{topic}:{normalized}"


def _related_album(label: str, title: str | None, year: int | None) -> str | None:
    """Return a related album fact."""
    if title is None:
        return None
    suffix = f" ({year})" if year is not None else ""
    return f"{label}: {title}{suffix}"


def _sources_for_value(value: str | None, candidates: dict[str, str | None]) -> list[str]:
    """Return sources whose candidate value matches the selected value."""
    if value is None:
        return []
    sources = [source for source, candidate in candidates.items() if _same_value(value, candidate)]
    return sources or ["plex"]


def _person_sources(value: str, discogs_values: list[str]) -> list[str]:
    """Return likely sources for a personnel value."""
    if any(_same_value(value, item) for item in discogs_values):
        return ["discogs"]
    return ["musicbrainz"]


def _producer_sources(value: str, context: AlbumContext) -> list[str]:
    """Return likely sources for a producer value."""
    in_discogs = any(_same_value(value, item) for item in context.discogs.producer)
    occurrences = sum(1 for item in context.producers if _same_value(value, item))
    if in_discogs and occurrences > 1:
        return ["musicbrainz", "discogs"]
    if in_discogs:
        return ["discogs"]
    return ["musicbrainz"]


def _label_sources(value: str, context: AlbumContext) -> list[str]:
    """Return likely sources for a label value."""
    sources = ["musicbrainz"]
    if any(_same_value(value, item) for item in context.discogs.labels):
        sources.append("discogs")
    return sources


def _genre_sources(context: AlbumContext) -> list[str]:
    """Return likely sources for style information."""
    sources: list[str] = []
    if context.musicbrainz.genres or context.genres:
        sources.append("musicbrainz")
    if context.plex.genres:
        sources.append("plex")
    if context.lastfm.tags or context.lastfm_artist.tags:
        sources.append("lastfm")
    return sources or ["plex"]


def _same_value(left: str | None, right: str | None) -> bool:
    """Return whether two values normalize to the same string."""
    if left is None or right is None:
        return False
    return left.strip().casefold() == right.strip().casefold()


def _dedupe(values: Iterable[str]) -> list[str]:
    """Return values with case-insensitive duplicates removed."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = value.strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _append_value(lines: list[str], label: str, value: str | None) -> None:
    """Append a scalar editorial line."""
    if value:
        lines.append(f"{label}: {value}")


def _append_list(lines: list[str], label: str, values: list[str] | None) -> None:
    """Append a list editorial line."""
    if values:
        lines.append(f"{label}: {', '.join(values)}")


def _append_facts(lines: list[str], label: str, facts: list[EditorialFact] | None) -> None:
    """Append sorted facts with compact confidence/source annotations."""
    if not facts:
        return
    rendered = [
        f"{fact.text} [{fact.confidence}; sources: {', '.join(fact.sources)}]" for fact in facts
    ]
    lines.append(f"{label}: {' | '.join(rendered)}")


def _append_verified(lines: list[str], label: str, facts: list[VerifiedFact] | None) -> None:
    """Append verified facts with confidence annotations."""
    if not facts:
        return
    rendered = [
        (
            f"{fact.category}: {fact.value} "
            f"({fact.verification_state.value}, {fact.confidence_score:.2f}; "
            f"sources: {', '.join(fact.supporting_sources) or 'none'})"
        )
        for fact in facts
    ]
    lines.append(f"{label}: {' | '.join(rendered)}")
