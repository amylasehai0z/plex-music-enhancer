"""Rule-based album enrichment planner."""

from __future__ import annotations

from collections.abc import Iterable
from re import search, split
from typing import Protocol

from plex_music_enhancer.planner.models import (
    ContentIssue,
    ContentQualityReport,
    EnrichmentAction,
    EnrichmentPlan,
    PlannedAlbum,
    PlanningReport,
    QualityLevel,
)
from plex_music_enhancer.plex.audit import SummaryLanguage

DEFAULT_GERMAN_IMPROVE_THRESHOLD_WORDS = 60
MINIMUM_GOOD_SCORE = 60
MINIMUM_SKIP_SCORE = 80


class AlbumPlanningCandidate(Protocol):
    """Minimal album fields required for planning."""

    rating_key: str
    library: str
    artist: str
    album: str
    current_summary: str | None


class EnrichmentPlanner:
    """Determine the best enrichment strategy before generation."""

    def __init__(
        self,
        *,
        german_improve_threshold_words: int = DEFAULT_GERMAN_IMPROVE_THRESHOLD_WORDS,
    ) -> None:
        """Create an enrichment planner."""
        self._german_improve_threshold_words = german_improve_threshold_words

    def plan_summary(self, summary: str | None) -> EnrichmentPlan:
        """Return the recommended plan for a summary."""
        text = (summary or "").strip()
        if not text:
            quality = ContentQualityReport(
                quality_score=0,
                quality_level=QualityLevel.POOR,
                issues=[ContentIssue.MISSING],
            )
            return EnrichmentPlan(
                action=EnrichmentAction.CREATE,
                reason="Missing summary.",
                language=SummaryLanguage.UNKNOWN.value,
                confidence=1.0,
                quality=quality,
            )

        language = estimate_language(text)
        quality = analyze_content_quality(text, language=language)
        if language is SummaryLanguage.ENGLISH:
            return EnrichmentPlan(
                action=EnrichmentAction.TRANSLATE,
                reason="Existing summary appears to be English.",
                language=language.value,
                confidence=0.9,
                quality=quality,
            )

        if language is SummaryLanguage.GERMAN:
            if quality.quality_score < MINIMUM_GOOD_SCORE:
                return EnrichmentPlan(
                    action=EnrichmentAction.IMPROVE,
                    reason=f"German summary quality is poor ({quality.quality_score}/100).",
                    language=language.value,
                    confidence=0.85,
                    quality=quality,
                )

            if quality.quality_score <= MINIMUM_SKIP_SCORE:
                return EnrichmentPlan(
                    action=EnrichmentAction.REVIEW,
                    reason=(
                        "German summary quality is acceptable but should be reviewed "
                        f"({quality.quality_score}/100)."
                    ),
                    language=language.value,
                    confidence=0.7,
                    quality=quality,
                )

            return EnrichmentPlan(
                action=EnrichmentAction.SKIP,
                reason=f"German summary quality is high ({quality.quality_score}/100).",
                language=language.value,
                confidence=0.8,
                quality=quality,
            )

        if language is SummaryLanguage.OTHER:
            return EnrichmentPlan(
                action=EnrichmentAction.REVIEW,
                reason="Summary language is neither clearly German nor English.",
                language=language.value,
                confidence=0.5,
                quality=quality,
            )

        return EnrichmentPlan(
            action=EnrichmentAction.REVIEW,
            reason="Summary language could not be determined confidently.",
            language=language.value,
            confidence=0.4,
            quality=quality,
        )

    def plan_album(self, candidate: AlbumPlanningCandidate) -> PlannedAlbum:
        """Return a planned album result."""
        summary = candidate.current_summary
        return PlannedAlbum(
            rating_key=candidate.rating_key,
            library=candidate.library,
            artist=candidate.artist,
            album=candidate.album,
            current_summary=summary,
            current_summary_words=_word_count(summary or ""),
            plan=self.plan_summary(summary),
        )

    def plan_albums(self, candidates: Iterable[AlbumPlanningCandidate]) -> PlanningReport:
        """Return plans for all album candidates."""
        return PlanningReport(albums=[self.plan_album(candidate) for candidate in candidates])


def estimate_language(summary: str | None) -> SummaryLanguage:
    """Estimate summary language using deterministic keyword heuristics."""
    text = (summary or "").strip()
    if not text:
        return SummaryLanguage.UNKNOWN

    lowered = f" {text.casefold()} "
    german_score = _keyword_score(
        lowered,
        (" der ", " die ", " das ", " und ", " ist ", " mit ", " ein ", " eine ", " wurde "),
    )
    english_score = _keyword_score(
        lowered,
        (" the ", " and ", " is ", " with ", " a ", " an ", " was ", " were ", " from "),
    )

    if any(char in text for char in "äöüÄÖÜß"):
        german_score += 2

    if german_score == 0 and english_score == 0:
        return SummaryLanguage.OTHER
    if german_score > english_score:
        return SummaryLanguage.GERMAN
    if english_score > german_score:
        return SummaryLanguage.ENGLISH
    return SummaryLanguage.UNKNOWN


def analyze_content_quality(
    summary: str | None,
    *,
    language: SummaryLanguage | None = None,
) -> ContentQualityReport:
    """Analyze existing summary quality."""
    text = (summary or "").strip()
    if not text:
        return ContentQualityReport(
            quality_score=0,
            quality_level=QualityLevel.POOR,
            issues=[ContentIssue.MISSING],
        )

    selected_language = language or estimate_language(text)
    issues: list[ContentIssue] = []
    score = 100
    word_count = _word_count(text)

    if word_count < 40:
        issues.append(ContentIssue.SHORT)
        score -= 45 if word_count < 20 else 20

    if _has_placeholder(text):
        issues.append(ContentIssue.PLACEHOLDER)
        score -= 55

    if _has_duplicated_phrases(text):
        issues.append(ContentIssue.REPETITIVE)
        score -= 25

    if _has_machine_translation_markers(text):
        issues.append(ContentIssue.MACHINE_TRANSLATION)
        score -= 25

    if _has_low_readability(text):
        issues.append(ContentIssue.LOW_READABILITY)
        score -= 15

    if selected_language in {SummaryLanguage.UNKNOWN, SummaryLanguage.OTHER}:
        issues.append(ContentIssue.UNKNOWN_LANGUAGE)
        score -= 20

    if _has_excessive_whitespace(text):
        issues.append(ContentIssue.EXCESSIVE_WHITESPACE)
        score -= 10

    if _has_formatting_problems(text):
        issues.append(ContentIssue.FORMATTING_PROBLEMS)
        score -= 15

    if not _has_complete_sentence(text):
        issues.append(ContentIssue.INCOMPLETE_SENTENCE)
        score -= 20

    normalized_score = max(0, min(100, score))
    return ContentQualityReport(
        quality_score=normalized_score,
        quality_level=_quality_level(normalized_score),
        issues=list(dict.fromkeys(issues)),
    )


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    """Count keyword hits in text."""
    return sum(text.count(keyword) for keyword in keywords)


def _word_count(text: str) -> int:
    """Return a whitespace word count."""
    return len(text.split()) if text.strip() else 0


def _quality_level(score: int) -> QualityLevel:
    """Return quality level for a score."""
    if score > 85:
        return QualityLevel.EXCELLENT
    if score > 80:
        return QualityLevel.GOOD
    if score >= 60:
        return QualityLevel.FAIR
    return QualityLevel.POOR


def _has_placeholder(text: str) -> bool:
    """Return whether text contains placeholder markers."""
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "placeholder",
            "lorem ipsum",
            "todo",
            "tbd",
            "dummyprovider",
            "{{",
            "}}",
        )
    )


def _has_duplicated_phrases(text: str) -> bool:
    """Return whether text repeats short phrases excessively."""
    words = [word.strip(".,;:!?()[]\"'").casefold() for word in text.split()]
    words = [word for word in words if word]
    if len(words) < 8:
        return False

    phrases = [" ".join(words[index : index + 3]) for index in range(len(words) - 2)]
    return any(phrases.count(phrase) >= 3 for phrase in set(phrases))


def _has_machine_translation_markers(text: str) -> bool:
    """Return whether text contains awkward machine-translation-like German."""
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "ist den genres",
            "ist dem genre",
            "wurde veröffentlicht in",
            "veröffentlicht in ",
            "zugeordnet werden kann",
            "das album hat eine produktion",
            "es enthält die tracks",
        )
    )


def _has_low_readability(text: str) -> bool:
    """Return whether sentence shape suggests low readability."""
    sentences = [sentence.strip() for sentence in split(r"[.!?]+", text) if sentence.strip()]
    if not sentences:
        return True

    word_counts = [_word_count(sentence) for sentence in sentences]
    average_words = sum(word_counts) / len(word_counts)
    return average_words > 32 or any(count > 45 for count in word_counts)


def _has_excessive_whitespace(text: str) -> bool:
    """Return whether text contains excessive whitespace."""
    return bool(search(r"\s{3,}", text)) or "\n\n\n" in text


def _has_formatting_problems(text: str) -> bool:
    """Return whether text contains formatting not suitable for Plex summaries."""
    return bool(search(r"(?m)^\s*([-*+]|\d+\.)\s+", text)) or any(
        marker in text for marker in ("**", "__", "# ", "`")
    )


def _has_complete_sentence(text: str) -> bool:
    """Return whether text appears to end with a complete sentence."""
    return text.rstrip().endswith((".", "!", "?"))
