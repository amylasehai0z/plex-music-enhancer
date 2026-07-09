"""Deterministic editorial QA engine."""

from __future__ import annotations

from collections.abc import Iterable
from re import findall, search, split, sub
from typing import Any

from plex_music_enhancer.editorial import GermanEditorialStyleEngine
from plex_music_enhancer.enrichment.models import AlbumContext, ArtistContext
from plex_music_enhancer.quality.models import (
    EditorialMetrics,
    MetadataCoverage,
    QualityCategory,
    QualityCheck,
    QualityLevel,
    QualityRecommendation,
    QualityReport,
    QualityStatus,
    VerificationMetrics,
)
from plex_music_enhancer.verification import VerificationState

DEFAULT_QUALITY_WEIGHTS: dict[QualityCategory, float] = {
    QualityCategory.COMPLETENESS: 0.20,
    QualityCategory.FACT_COVERAGE: 0.20,
    QualityCategory.VERIFICATION_CONFIDENCE: 0.15,
    QualityCategory.NARRATIVE_STRUCTURE: 0.15,
    QualityCategory.GERMAN_LANGUAGE: 0.10,
    QualityCategory.READABILITY: 0.10,
    QualityCategory.OVERALL_EDITORIAL_QUALITY: 0.05,
    QualityCategory.FORMATTING: 0.05,
}

ARTIST_ADMINISTRATIVE_FACT_CATEGORIES = {
    "aliases",
    "associated_acts",
    "labels",
    "members",
    "former_members",
    "occupations",
    "official_website",
}
ARTIST_NARRATIVE_SOURCE_CATEGORIES = {"biography", "career_summary"}
ARTIST_STYLE_CATEGORIES = {"genres", "styles"}
ARTIST_ORIGIN_CATEGORIES = {"origin", "nationality"}
_COUNTRY_VARIANTS = {
    "de": ["Deutschland", "deutsch", "deutsche", "deutscher", "deutschen"],
    "deutschland": ["deutsch", "deutsche", "deutscher", "deutschen"],
    "germany": ["Deutschland", "deutsch", "deutsche", "deutscher", "deutschen"],
    "gb": ["Großbritannien", "britisch", "britische", "britischer", "britischen"],
    "uk": ["Großbritannien", "britisch", "britische", "britischer", "britischen"],
    "united kingdom": [
        "Großbritannien",
        "britisch",
        "britische",
        "britischer",
        "britischen",
    ],
    "england": ["englisch", "englische", "englischer", "englischen", "britisch"],
    "se": ["Schweden", "schwedisch", "schwedische", "schwedischer", "schwedischen"],
    "sweden": ["Schweden", "schwedisch", "schwedische", "schwedischer", "schwedischen"],
    "us": ["USA", "US-amerikanisch", "US-amerikanische", "amerikanisch", "amerikanische"],
    "usa": ["US-amerikanisch", "US-amerikanische", "amerikanisch", "amerikanische"],
    "united states": [
        "USA",
        "US-amerikanisch",
        "US-amerikanische",
        "amerikanisch",
        "amerikanische",
    ],
}


class EditorialQualityEngine:
    """Analyze generated German descriptions without modifying them."""

    def __init__(
        self,
        *,
        style_engine: GermanEditorialStyleEngine | None = None,
        weights: dict[QualityCategory, float] | None = None,
    ) -> None:
        """Create a deterministic QA engine."""
        self._style_engine = style_engine or GermanEditorialStyleEngine()
        self._weights = weights or DEFAULT_QUALITY_WEIGHTS

    def analyze_album(self, context: AlbumContext, generated_text: str) -> QualityReport:
        """Return a QA report for one generated album description."""
        topics = _album_topics(context)
        return self._analyze(
            context=context,
            generated_text=generated_text,
            topics=topics,
            artist=context.plex.artist,
            album=context.plex.album,
        )

    def analyze_artist(self, context: ArtistContext, generated_text: str) -> QualityReport:
        """Return a QA report for one generated artist biography."""
        topics = _artist_topics(context)
        return self._analyze(
            context=context,
            generated_text=generated_text,
            topics=topics,
            artist=context.plex.artist,
            album=None,
        )

    def _analyze(
        self,
        *,
        context: Any,
        generated_text: str,
        topics: list[_Topic],
        artist: str | None,
        album: str | None,
    ) -> QualityReport:
        """Analyze one generated text against available context."""
        text = generated_text.strip()
        style = self._style_engine.analyze(text, artist=artist, album=album)
        recommendable_topics = _recommendable_topics(topics, context)
        mentioned_topics = [
            topic for topic in recommendable_topics if _topic_is_mentioned(text, topic)
        ]
        omitted_topics = [
            topic
            for topic in recommendable_topics
            if topic.recommended and topic not in mentioned_topics
        ]
        verification = _verification_metrics(context, text)
        metadata_coverage = _metadata_coverage(topics, mentioned_topics, omitted_topics)
        editorial_metrics = _editorial_metrics(text)

        checks = [
            _completeness_check(topics, mentioned_topics, omitted_topics),
            _fact_coverage_check(verification),
            _verification_check(verification),
            _editorial_flow_check(text),
            _readability_check(style.readability_score),
            _lexical_diversity_check(style.lexical_diversity),
            _sentence_variety_check(style.sentence_variation),
            _german_language_check(text),
            _repetition_check(style.repetition),
            _placeholder_check(text),
            _formatting_check(text),
            _narrative_structure_check(text),
            _overall_editorial_check(style.overall_style),
        ]
        warnings = _warnings(checks, verification)
        recommendations = _recommendations(omitted_topics, verification)
        overall = _overall_score(checks, self._weights)
        quality_level = _quality_level(overall)
        return QualityReport(
            overall_score=overall,
            overall_level=quality_level,
            quality_level=quality_level,
            checks=checks,
            warnings=warnings,
            recommendations=recommendations,
            missing_topics=[topic.name for topic in omitted_topics],
            style_metrics={
                "average_sentence_length": style.average_sentence_length,
                "average_paragraph_length": style.average_paragraph_length,
                "lexical_diversity": style.lexical_diversity,
                "readability_score": style.readability_score,
                "repetition": style.repetition,
                "passive_voice": style.passive_voice,
                "llm_cliches": style.llm_cliches,
            },
            verification_metrics=verification,
            metadata_coverage=metadata_coverage,
            editorial_metrics=editorial_metrics,
        )


class _Topic:
    """Internal available metadata topic."""

    def __init__(
        self,
        name: str,
        values: Iterable[object],
        *,
        recommended: bool = True,
        categories: Iterable[str] | None = None,
    ) -> None:
        self.name = name
        self.values = _values(values)
        self.recommended = recommended
        self.categories = list(categories or [name.replace(" ", "_")])


def _album_topics(context: AlbumContext) -> list[_Topic]:
    """Return album metadata topics that can be checked for coverage."""
    return [
        _Topic(
            "release date",
            [context.release_date, context.musicbrainz.release_date, context.plex.year],
        ),
        _Topic("artist", [context.plex.artist]),
        _Topic("album", [context.plex.album], recommended=False),
        _Topic("genres", [*context.genres, *context.musicbrainz.genres, *context.plex.genres]),
        _Topic("producer", context.producers),
        _Topic("label", context.labels),
        _Topic("composer", context.composers),
        _Topic("lyricist", context.lyricists),
        _Topic("career position", [context.discography_position, context.career_phase]),
        _Topic(
            "recording context",
            [context.recording_period, context.recording_location, *context.studios],
        ),
        _Topic("historical context", [context.historical_context]),
        _Topic(
            "notable tracks", [*context.notable_tracks, *context.singles, *context.notable_singles]
        ),
    ]


def _artist_topics(context: ArtistContext) -> list[_Topic]:
    """Return artist metadata topics that can be checked for coverage."""
    return [
        _Topic("artist", [context.plex.artist, context.full_name]),
        _Topic(
            "origin",
            [context.origin, context.nationality, context.plex.country],
            categories=["origin", "nationality"],
        ),
        _Topic(
            "musical style",
            [*context.genres, *context.musicbrainz.genres, *context.plex.genres, *context.styles],
            categories=["genres", "styles"],
        ),
        _Topic(
            "career progression",
            [*context.milestones, context.career_summary],
            categories=["milestones", "career_summary"],
        ),
        _Topic(
            "historical context",
            [context.historical_context],
            categories=["historical_context"],
        ),
        _Topic("important albums", context.notable_albums, categories=["notable_albums"]),
        _Topic(
            "major works",
            [*context.notable_albums, *context.milestones],
            categories=["notable_albums", "milestones"],
        ),
        _Topic(
            "legacy",
            [*context.awards, *context.influenced_artists],
            categories=["awards", "influenced_artists"],
        ),
        _Topic("awards", context.awards),
        _Topic("milestones", context.milestones),
    ]


def _recommendable_topics(topics: list[_Topic], context: Any) -> list[_Topic]:
    """Return topics with populated, sufficiently reliable supporting facts."""
    collection = getattr(context, "fact_collection", None)
    if collection is None:
        return [topic for topic in topics if topic.values]

    return [
        topic for topic in topics if topic.values and _topic_has_reliable_fact(topic, collection)
    ]


def _topic_has_reliable_fact(topic: _Topic, collection: Any) -> bool:
    """Return whether a topic has verified or high-confidence probable support."""
    for category in topic.categories:
        for fact in collection.by_category(category):
            if not fact.value:
                continue
            if fact.verification_state == VerificationState.VERIFIED:
                return True
            if (
                fact.verification_state == VerificationState.PROBABLE
                and fact.confidence_score >= 0.80
            ):
                return True
    return False


def _verification_metrics(context: Any, text: str) -> VerificationMetrics:
    """Return fact mention metrics using the existing verification engine output."""
    collection = getattr(context, "fact_collection", None)
    if collection is None:
        return VerificationMetrics()

    verified_mentioned: list[str] = []
    verified_omitted: list[str] = []
    weak_mentioned: list[str] = []
    conflicting_mentioned: list[str] = []
    unknown_mentioned: list[str] = []
    for fact in collection.facts:
        if not fact.value:
            continue
        if isinstance(context, ArtistContext) and _skip_artist_fact_coverage(context, text, fact):
            continue
        label = f"{fact.category}: {fact.value}"
        mentioned = (
            _artist_fact_is_mentioned(context, text, fact)
            if isinstance(context, ArtistContext)
            else _mentions_any(text, [fact.value])
        )
        if fact.verification_state == VerificationState.VERIFIED:
            if mentioned:
                verified_mentioned.append(label)
            else:
                verified_omitted.append(label)
        elif fact.verification_state == VerificationState.WEAK and mentioned:
            weak_mentioned.append(label)
        elif fact.verification_state == VerificationState.CONFLICTING and mentioned:
            conflicting_mentioned.append(label)
        elif fact.verification_state == VerificationState.UNKNOWN and mentioned:
            unknown_mentioned.append(label)

    total_reliable = len(verified_mentioned) + len(verified_omitted)
    if total_reliable:
        coverage_score = round((len(verified_mentioned) / total_reliable) * 100)
    else:
        coverage_score = 100

    return VerificationMetrics(
        verified_facts_mentioned=verified_mentioned,
        verified_facts_omitted=verified_omitted,
        weak_facts_mentioned=weak_mentioned,
        conflicting_facts_mentioned=conflicting_mentioned,
        unknown_facts_mentioned=unknown_mentioned,
        coverage_score=coverage_score,
    )


def _metadata_coverage(
    topics: list[_Topic],
    mentioned: list[_Topic],
    omitted: list[_Topic],
) -> MetadataCoverage:
    """Return topic coverage metrics."""
    available = [topic for topic in topics if topic.recommended and topic.values]
    mentioned_recommended = [topic for topic in mentioned if topic.recommended and topic.values]
    if not available:
        coverage_score = 100
    else:
        coverage_score = round((len(mentioned_recommended) / len(available)) * 100)
    return MetadataCoverage(
        available_topics=[topic.name for topic in available],
        mentioned_topics=[topic.name for topic in mentioned_recommended],
        omitted_topics=[topic.name for topic in omitted],
        coverage_score=coverage_score,
    )


def _editorial_metrics(text: str) -> EditorialMetrics:
    """Return deterministic editorial structure metrics."""
    sentences = _sentences(text)
    paragraphs = [paragraph for paragraph in split(r"\n\s*\n", text.strip()) if paragraph.strip()]
    return EditorialMetrics(
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
        has_opening=bool(sentences),
        has_closing=bool(sentences) and not _ends_abruptly(text),
        has_transition=_has_transition(text),
        chronological_flow=_has_chronological_flow(text),
        coherent_structure=len(sentences) >= 2 and len(paragraphs) <= 3,
    )


def _completeness_check(
    topics: list[_Topic],
    mentioned: list[_Topic],
    omitted: list[_Topic],
) -> QualityCheck:
    """Score metadata completeness."""
    recommended = [topic for topic in topics if topic.recommended and topic.values]
    mentioned_recommended = [topic for topic in mentioned if topic.recommended and topic.values]
    if not recommended:
        return _check(QualityCategory.COMPLETENESS, 100, ["No optional metadata available."])
    score = round((len(mentioned_recommended) / len(recommended)) * 100)
    details = [f"{len(mentioned_recommended)} of {len(recommended)} available topics mentioned."]
    details.extend(f"{topic.name} available but omitted." for topic in omitted)
    return _check(QualityCategory.COMPLETENESS, score, details)


def _fact_coverage_check(metrics: VerificationMetrics) -> QualityCheck:
    """Score verified fact coverage."""
    total = len(metrics.verified_facts_mentioned) + len(metrics.verified_facts_omitted)
    if total == 0:
        return _check(QualityCategory.FACT_COVERAGE, 100, ["No verified facts available."])
    score = round((len(metrics.verified_facts_mentioned) / total) * 100)
    return _check(
        QualityCategory.FACT_COVERAGE,
        score,
        [f"{len(metrics.verified_facts_mentioned)} of {total} verified facts mentioned."],
    )


def _verification_check(metrics: VerificationMetrics) -> QualityCheck:
    """Score verification risk."""
    score = 100
    details: list[str] = []
    if metrics.conflicting_facts_mentioned:
        score -= 45
        details.append("Conflicting facts were mentioned.")
    if metrics.weak_facts_mentioned:
        score -= min(30, len(metrics.weak_facts_mentioned) * 10)
        details.append("Weak facts were mentioned.")
    if metrics.unknown_facts_mentioned:
        score -= min(20, len(metrics.unknown_facts_mentioned) * 8)
        details.append("Unknown facts were mentioned.")
    return _check(
        QualityCategory.VERIFICATION_CONFIDENCE, score, details or ["No verification risks."]
    )


def _editorial_flow_check(text: str) -> QualityCheck:
    """Score deterministic editorial flow."""
    sentences = _sentences(text)
    has_transition = _has_transition(text) or len(sentences) <= 3
    score = 100
    details: list[str] = []
    if len(sentences) < 2:
        score -= 35
        details.append("Text has too few sentences for narrative flow.")
    if not has_transition:
        score -= 20
        details.append("No clear transition language detected.")
    if _starts_weakly(text):
        score -= 15
        details.append("Opening sentence is generic.")
    if _ends_abruptly(text):
        score -= 15
        details.append("Closing sentence appears abrupt.")
    return _check(QualityCategory.EDITORIAL_FLOW, score, details or ["Flow is coherent."])


def _readability_check(score: int) -> QualityCheck:
    """Return readability check."""
    return _check(QualityCategory.READABILITY, score, [f"Readability score: {score}."])


def _lexical_diversity_check(diversity: float) -> QualityCheck:
    """Return lexical diversity check."""
    score = round(diversity * 100)
    return _check(
        QualityCategory.LEXICAL_DIVERSITY, score, [f"Lexical diversity: {diversity:.3f}."]
    )


def _sentence_variety_check(rating: str) -> QualityCheck:
    """Return sentence variety check."""
    scores = {"EXCELLENT": 100, "VERY GOOD": 90, "GOOD": 82, "FAIR": 72, "POOR": 55}
    return _check(QualityCategory.SENTENCE_VARIETY, scores.get(rating, 70), [rating])


def _german_language_check(text: str) -> QualityCheck:
    """Return German language signal check."""
    score = 100 if _looks_german(text) else 55
    return _check(
        QualityCategory.GERMAN_LANGUAGE,
        score,
        ["German markers detected." if score == 100 else "Few German markers detected."],
    )


def _repetition_check(level: str) -> QualityCheck:
    """Return repetition check."""
    scores = {"NONE": 100, "LOW": 90, "MEDIUM": 72, "HIGH": 50}
    return _check(QualityCategory.REPETITION, scores.get(level, 70), [f"Repetition: {level}."])


def _placeholder_check(text: str) -> QualityCheck:
    """Return placeholder detection check."""
    has_placeholder = bool(
        search(r"(?i)(placeholder|lorem ipsum|todo|tbd|dummyprovider|{{|}})", text)
    )
    return _check(
        QualityCategory.PLACEHOLDER_DETECTION,
        0 if has_placeholder else 100,
        ["Placeholder text detected."] if has_placeholder else ["No placeholder text detected."],
    )


def _formatting_check(text: str) -> QualityCheck:
    """Return formatting check."""
    has_bad_formatting = bool(search(r"(?m)^\s*([-*+]|\d+\.)\s+", text)) or bool(
        search(r"(^|\s)(#{1,6}\s|\*\*|__|`|>\s)", text)
    )
    return _check(
        QualityCategory.FORMATTING,
        45 if has_bad_formatting else 100,
        (
            ["List or Markdown formatting detected."]
            if has_bad_formatting
            else ["No list or Markdown formatting."]
        ),
    )


def _narrative_structure_check(text: str) -> QualityCheck:
    """Return narrative structure check."""
    paragraphs = [paragraph for paragraph in split(r"\n\s*\n", text.strip()) if paragraph.strip()]
    sentences = _sentences(text)
    score = 100
    details: list[str] = []
    if len(sentences) < 2:
        score -= 40
        details.append("Too few sentences.")
    if len(paragraphs) > 3:
        score -= 15
        details.append("Too many paragraphs for a concise Plex summary.")
    if any(len(_words(paragraph)) > 160 for paragraph in paragraphs):
        score -= 15
        details.append("Paragraph is very long.")
    return _check(
        QualityCategory.NARRATIVE_STRUCTURE, score, details or ["Narrative structure is balanced."]
    )


def _overall_editorial_check(rating: str) -> QualityCheck:
    """Return overall editorial style check."""
    scores = {"EXCELLENT": 100, "VERY GOOD": 92, "GOOD": 84, "FAIR": 74, "POOR": 55}
    return _check(QualityCategory.OVERALL_EDITORIAL_QUALITY, scores.get(rating, 70), [rating])


def _check(category: QualityCategory, score: int, details: list[str]) -> QualityCheck:
    """Build a quality check with status derived from score."""
    bounded = max(0, min(100, score))
    if bounded >= 85:
        status = QualityStatus.PASS
    elif bounded >= 75:
        status = QualityStatus.GOOD
    elif bounded >= 60:
        status = QualityStatus.WARNING
    else:
        status = QualityStatus.FAIL
    return QualityCheck(category=category, score=bounded, status=status, details=details)


def _overall_score(checks: list[QualityCheck], weights: dict[QualityCategory, float]) -> int:
    """Return weighted overall score."""
    if not checks:
        return 0
    by_category = {check.category: check.score for check in checks}
    weighted_total = 0.0
    used_weight = 0.0
    for category, weight in weights.items():
        if category not in by_category:
            continue
        weighted_total += by_category[category] * weight
        used_weight += weight
    if not used_weight:
        return round(sum(check.score for check in checks) / len(checks))
    return round(weighted_total / used_weight)


def _quality_level(score: int) -> QualityLevel:
    """Return quality level from score."""
    if score >= 95:
        return QualityLevel.EXCELLENT
    if score >= 90:
        return QualityLevel.VERY_GOOD
    if score >= 80:
        return QualityLevel.GOOD
    if score >= 70:
        return QualityLevel.FAIR
    return QualityLevel.POOR


def _warnings(checks: list[QualityCheck], metrics: VerificationMetrics) -> list[str]:
    """Return warning messages."""
    warnings = [
        f"{check.category.value}: {', '.join(check.details)}"
        for check in checks
        if check.status in {QualityStatus.WARNING, QualityStatus.FAIL}
    ]
    if metrics.conflicting_facts_mentioned:
        warnings.append("Generated text mentions conflicting facts.")
    return warnings


def _recommendations(
    omitted_topics: list[_Topic],
    metrics: VerificationMetrics,
) -> list[QualityRecommendation]:
    """Return deterministic improvement recommendations."""
    recommendations = [
        QualityRecommendation(
            message=_recommendation_message(topic.name),
            category=QualityCategory.COMPLETENESS,
            priority=3,
        )
        for topic in omitted_topics
    ]
    recommendations.extend(
        QualityRecommendation(
            message=f"Verified fact omitted: {fact}.",
            category=QualityCategory.FACT_COVERAGE,
            priority=2,
        )
        for fact in metrics.verified_facts_omitted[:8]
    )
    return recommendations


def _recommendation_message(topic_name: str) -> str:
    """Return a stable, user-facing recommendation for omitted context."""
    messages = {
        "notable tracks": "Notable tracks available but not mentioned.",
        "important albums": "Important albums available but not mentioned.",
        "major works": "Major works available but not mentioned.",
        "historical context": "Historical context available but not mentioned.",
        "career progression": "Career milestones available but not mentioned.",
        "musical style": "Musical style information available but not mentioned.",
        "legacy": "Legacy context available but not mentioned.",
    }
    return messages.get(topic_name, f"{topic_name.title()} available but not mentioned.")


def _values(values: Iterable[object]) -> list[str]:
    """Return populated string values."""
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result.append(text)
    return _dedupe(result)


def _mentions_any(text: str, values: Iterable[str]) -> bool:
    """Return whether text mentions any value, with year support for date-like values."""
    lowered = text.casefold()
    for value in values:
        needle = value.casefold().strip()
        if not needle:
            continue
        if needle in lowered:
            return True
        if len(needle) >= 4 and needle[:4].isdigit() and needle[:4] in lowered:
            return True
    return False


def _topic_is_mentioned(text: str, topic: _Topic) -> bool:
    """Return whether a topic is covered in editorial prose."""
    categories = set(topic.categories)
    if categories & ARTIST_ORIGIN_CATEGORIES:
        return _artist_origin_is_mentioned(text, topic.values)
    if categories & ARTIST_STYLE_CATEGORIES:
        return _artist_style_is_mentioned(text, topic.values)
    return _mentions_any(text, topic.values)


def _artist_fact_is_mentioned(context: ArtistContext, text: str, fact: Any) -> bool:
    """Return whether an artist fact is covered by exact or semantic prose."""
    if fact.category in ARTIST_ORIGIN_CATEGORIES:
        return _artist_origin_is_mentioned(text, _artist_origin_values(context, fact.value))
    if fact.category in ARTIST_STYLE_CATEGORIES:
        return _artist_style_is_mentioned(text, _artist_style_values(context, fact.value))
    return _mentions_any(text, [fact.value])


def _skip_artist_fact_coverage(context: ArtistContext, text: str, fact: Any) -> bool:
    """Return whether an artist fact should not affect editorial coverage."""
    if fact.category in ARTIST_ADMINISTRATIVE_FACT_CATEGORIES:
        return True
    if fact.category in ARTIST_NARRATIVE_SOURCE_CATEGORIES:
        return True
    return fact.category in ARTIST_STYLE_CATEGORIES and _artist_style_is_mentioned(
        text, _artist_style_values(context, fact.value)
    )


def _artist_origin_values(context: ArtistContext, value: object) -> list[str]:
    """Return origin and nationality spellings that can satisfy origin coverage."""
    values = _values([value, context.origin, context.nationality, context.plex.country])
    expanded: list[str] = []
    for item in values:
        expanded.extend(_origin_variants(item))
    return _dedupe([*values, *expanded])


def _artist_style_values(context: ArtistContext, value: object) -> list[str]:
    """Return style values that can satisfy concise musical characterization."""
    return _values(
        [
            value,
            *context.genres,
            *context.musicbrainz.genres,
            *context.plex.genres,
            *context.styles,
        ]
    )


def _artist_origin_is_mentioned(text: str, values: Iterable[str]) -> bool:
    """Return whether origin is covered by place, country code, or nationality adjective."""
    variants = _dedupe([variant for value in values for variant in _origin_variants(value)])
    return _mentions_any(text, variants)


def _artist_style_is_mentioned(text: str, values: Iterable[str]) -> bool:
    """Return whether prose gives a concise musical style characterization."""
    if _mentions_any(text, values):
        return True
    lowered = f" {text.casefold()} "
    style_markers = (
        " musikalische ",
        " musikalischen ",
        " musikalischer ",
        " klang ",
        " sound ",
        " stil ",
        " stilistisch ",
        " repertoire ",
        " gesang ",
        " performance ",
    )
    return any(marker in lowered for marker in style_markers)


def _origin_variants(value: object) -> list[str]:
    """Return country and nationality variants for origin matching."""
    text = str(value).strip()
    if not text:
        return []
    lowered = text.casefold()
    variants = [] if lowered in _COUNTRY_VARIANTS and len(lowered) <= 2 else [text]
    variants.extend(_COUNTRY_VARIANTS.get(lowered, []))
    return variants


def _sentences(text: str) -> list[str]:
    """Return sentence-like chunks."""
    return [sentence.strip() for sentence in split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _words(text: str) -> list[str]:
    """Return word tokens."""
    return findall(r"\b[\wÄÖÜäöüß-]+\b", text)


def _has_transition(text: str) -> bool:
    """Return whether prose contains simple transition markers."""
    lowered = f" {text.casefold()} "
    markers = (
        " dabei ",
        " zudem ",
        " zugleich ",
        " während ",
        " später ",
        " dennoch ",
        " außerdem ",
        " damit ",
    )
    return any(marker in lowered for marker in markers)


def _has_chronological_flow(text: str) -> bool:
    """Return whether the text contains simple chronological signals."""
    lowered = f" {text.casefold()} "
    if search(r"\b(19|20)\d{2}\b", lowered):
        return True
    markers = (
        "zuvor",
        "danach",
        "später",
        "anschließend",
        "in dieser phase",
        "im anschluss",
        "folgte",
    )
    return any(marker in lowered for marker in markers)


def _starts_weakly(text: str) -> bool:
    """Return whether opening is generic."""
    sentences = _sentences(text)
    if not sentences:
        return True
    first = sentences[0].casefold()
    return first.startswith(("das album ist ", "dies ist ", "es ist ", "der künstler ist "))


def _ends_abruptly(text: str) -> bool:
    """Return whether closing appears abrupt."""
    sentences = _sentences(text)
    if len(sentences) < 2:
        return False
    return len(_words(sentences[-1])) < 6 or text.rstrip().endswith((",", ";", ":"))


def _looks_german(text: str) -> bool:
    """Return whether simple German markers are present."""
    lowered = f" {text.casefold()} "
    markers = (" der ", " die ", " das ", " und ", " ist ", " mit ", " eine ", " album ")
    return any(marker in lowered for marker in markers) or any(char in text for char in "äöüÄÖÜß")


def _dedupe(values: Iterable[str]) -> list[str]:
    """Return values with case-insensitive duplicates removed."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = sub(r"\s+", " ", value).strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result
