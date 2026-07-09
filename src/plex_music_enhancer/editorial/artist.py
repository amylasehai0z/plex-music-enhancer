"""Editorial composition for artist biography prompts."""

from __future__ import annotations

from collections.abc import Iterable
from re import sub

from plex_music_enhancer.editorial.models import EditorialContext, EditorialFact, FactConfidence
from plex_music_enhancer.enrichment.models import ArtistContext
from plex_music_enhancer.verification import FactVerifier, VerificationState
from plex_music_enhancer.verification.models import FactCollection, VerifiedFact

SOURCE_WEIGHTS = {
    "plex": 25,
    "musicbrainz": 35,
    "wikipedia": 32,
    "discogs": 25,
    "lastfm": 14,
}


class ArtistEditorialComposer:
    """Prepare structured writing guidance for German artist biographies."""

    def compose_artist(self, context: ArtistContext) -> EditorialContext:
        """Return editorial guidance for one artist biography."""
        facts = _FactCollector()
        collection = _fact_collection(context)

        _add_identity_facts(facts, context)
        _add_origin_facts(facts, context)
        _add_career_facts(facts, context)
        _add_style_facts(facts, context)
        _add_collaboration_facts(facts, context)
        _add_influence_facts(facts, context)
        _add_legacy_facts(facts, context)

        section_map = {
            "opening_focus": _opening_focus(context),
            "career_context": facts.section("career_context"),
            "recording_context": facts.section("origin_context"),
            "musical_style": facts.section("musical_style"),
            "production_context": facts.section("major_albums"),
            "personnel_context": facts.section("collaborations"),
            "historical_context": facts.section("influence_context"),
            "legacy_context": facts.section("legacy_context"),
        }
        missing = collection.missing_facts or None
        return EditorialContext(
            opening_focus=section_map["opening_focus"],
            career_context=section_map["career_context"],
            recording_context=section_map["recording_context"],
            musical_style=section_map["musical_style"],
            production_context=section_map["production_context"],
            personnel_context=section_map["personnel_context"],
            historical_context=section_map["historical_context"],
            legacy_context=section_map["legacy_context"],
            recommended_story_order=_story_order(section_map),
            important_facts=facts.important(),
            avoid_topics=_avoid_topics(missing),
            missing_context=missing,
            writing_guidance=_writing_guidance(),
            verified_facts=_facts_by_state(collection, VerificationState.VERIFIED),
            probable_facts=_facts_by_state(collection, VerificationState.PROBABLE),
            weak_facts=_facts_by_state(collection, VerificationState.WEAK),
            conflicting_facts=collection.conflicts or None,
            missing_facts=missing,
        )


class _FactCollector:
    """Collect and deduplicate artist editorial facts."""

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
        """Add one populated fact."""
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
        """Return sorted section facts."""
        return _sort_facts([self._facts[key] for key in self._sections.get(name, [])]) or None

    def important(self) -> list[EditorialFact] | None:
        """Return sorted important facts."""
        return _sort_facts(self._facts.values()) or None


def _add_identity_facts(facts: _FactCollector, context: ArtistContext) -> None:
    facts.add(
        "career_context",
        topic="identity",
        text=context.full_name or context.plex.artist,
        sources=["musicbrainz" if context.musicbrainz.artist_name else "plex"],
    )
    facts.add(
        "career_context",
        topic="aliases",
        text=f"Aliases: {', '.join(context.aliases)}" if context.aliases else None,
        sources=["musicbrainz", "discogs"],
    )


def _add_origin_facts(facts: _FactCollector, context: ArtistContext) -> None:
    facts.add("origin_context", topic="birth_name", text=context.birth_name, sources=["plex"])
    facts.add(
        "origin_context",
        topic="birth_date",
        text=f"Born: {context.birth_date}" if context.birth_date else None,
        sources=["musicbrainz"],
    )
    facts.add(
        "origin_context",
        topic="death_date",
        text=f"Died: {context.death_date}" if context.death_date else None,
        sources=["musicbrainz"],
    )
    facts.add("origin_context", topic="origin", text=context.origin, sources=["plex"])
    facts.add(
        "origin_context",
        topic="nationality",
        text=context.nationality,
        sources=["musicbrainz"],
    )


def _add_career_facts(facts: _FactCollector, context: ArtistContext) -> None:
    facts.add(
        "career_context",
        topic="active_years",
        text=f"Active years: {context.active_years}" if context.active_years else None,
        sources=["discogs", "musicbrainz"],
    )
    facts.add(
        "career_context",
        topic="career_summary",
        text=context.career_summary,
        sources=["wikipedia", "lastfm"],
    )
    facts.add(
        "career_context",
        topic="biography",
        text=context.biography,
        sources=["wikipedia", "lastfm", "discogs"],
    )
    for milestone in context.milestones:
        facts.add("career_context", topic="milestone", text=milestone, sources=["plex"])


def _add_style_facts(facts: _FactCollector, context: ArtistContext) -> None:
    facts.add(
        "musical_style",
        topic="genres",
        text=f"Genres: {', '.join(context.genres)}" if context.genres else None,
        sources=["musicbrainz", "plex", "discogs", "lastfm"],
    )
    facts.add(
        "musical_style",
        topic="styles",
        text=f"Styles: {', '.join(context.styles)}" if context.styles else None,
        sources=["discogs"],
    )
    for influence in context.influences:
        facts.add("musical_style", topic="influence", text=influence, sources=["plex"])


def _add_collaboration_facts(facts: _FactCollector, context: ArtistContext) -> None:
    for member in context.members:
        facts.add("collaborations", topic="member", text=member, sources=["discogs"])
    for act in context.associated_acts:
        facts.add("collaborations", topic="associated_act", text=act, sources=["plex"])


def _add_influence_facts(facts: _FactCollector, context: ArtistContext) -> None:
    for album in context.notable_albums:
        facts.add("major_albums", topic="notable_album", text=album, sources=["plex"])
    for artist in context.influenced_artists:
        facts.add("influence_context", topic="influenced_artist", text=artist, sources=["plex"])
    facts.add(
        "influence_context",
        topic="historical_context",
        text=context.historical_context,
        sources=["wikipedia"],
    )


def _add_legacy_facts(facts: _FactCollector, context: ArtistContext) -> None:
    for award in context.awards:
        facts.add("legacy_context", topic="award", text=award, sources=["plex"])
    facts.add(
        "legacy_context",
        topic="lastfm_context",
        text=context.lastfm.short_biography,
        sources=["lastfm"],
    )


def _opening_focus(context: ArtistContext) -> str:
    """Return concise opening focus."""
    bits = [context.plex.artist]
    if context.nationality:
        bits.append(context.nationality)
    if context.active_years:
        bits.append(f"active {context.active_years}")
    return "; ".join(bits)


def _story_order(section_map: dict[str, object]) -> list[str]:
    """Return natural artist biography story order."""
    candidates = [
        ("opening_focus", "Introduction"),
        ("recording_context", "Origins"),
        ("career_context", "Career development"),
        ("musical_style", "Musical style"),
        ("production_context", "Major albums"),
        ("personnel_context", "Collaborations"),
        ("historical_context", "Influence"),
        ("legacy_context", "Legacy"),
        ("opening_focus", "Closing"),
    ]
    return [label for key, label in candidates if section_map.get(key)]


def _avoid_topics(missing: list[str] | None) -> list[str]:
    """Return artist facts the model must not invent."""
    topics = [
        "awards unless explicitly supplied",
        "influence unless explicitly supplied",
        "collaborations unless explicitly supplied",
        "notable albums unless explicitly supplied",
    ]
    if missing:
        topics.extend(f"unsupplied {item}" for item in missing)
    return topics


def _writing_guidance() -> list[str]:
    """Return artist biography writing guidance."""
    return [
        "write as a German music encyclopedia biography",
        "begin with verified identity and career context",
        "connect origins, style, career development, and legacy naturally",
        "emphasize verified facts and treat weak facts as background only",
        "never resolve conflicting facts by guessing",
        "avoid fan language, marketing tone, and isolated fact lists",
    ]


def _fact_collection(context: ArtistContext) -> FactCollection:
    """Return verified artist facts."""
    if context.fact_collection.facts:
        return context.fact_collection
    return FactVerifier().verify_artist(context)


def _facts_by_state(
    collection: FactCollection,
    state: VerificationState,
) -> list[VerifiedFact] | None:
    """Return facts for one state."""
    facts = [
        fact
        for fact in collection.by_state(state)
        if fact.value and fact.verification_state != VerificationState.CONFLICTING
    ]
    return (
        sorted(facts, key=lambda fact: (-fact.confidence_score, fact.category, fact.value)) or None
    )


def _priority(sources: list[str]) -> int:
    """Return priority score."""
    return min(100, 20 + sum(SOURCE_WEIGHTS.get(source, 10) for source in set(sources)))


def _confidence(sources: list[str]) -> FactConfidence:
    """Return confidence label."""
    priority = _priority(sources)
    if priority >= 75:
        return "high"
    if priority >= 45:
        return "medium"
    return "low"


def _sort_facts(facts: Iterable[EditorialFact]) -> list[EditorialFact]:
    """Sort facts by priority."""
    return sorted(facts, key=lambda fact: (-fact.priority, fact.topic, fact.text))


def _fact_key(*, topic: str, text: str) -> str:
    """Return a dedupe key."""
    return f"{topic}:{sub(r'\s+', ' ', text.casefold()).strip()}"


def _dedupe(values: Iterable[str]) -> list[str]:
    """Return case-insensitive deduped strings."""
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
