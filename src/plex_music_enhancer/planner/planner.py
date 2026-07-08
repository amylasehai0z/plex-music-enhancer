"""Rule-based album enrichment planner."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from plex_music_enhancer.planner.models import (
    EnrichmentAction,
    EnrichmentPlan,
    PlannedAlbum,
    PlanningReport,
)
from plex_music_enhancer.plex.audit import SummaryLanguage

DEFAULT_GERMAN_IMPROVE_THRESHOLD_WORDS = 60


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
            return EnrichmentPlan(
                action=EnrichmentAction.CREATE,
                reason="Missing summary.",
                language=SummaryLanguage.UNKNOWN.value,
                confidence=1.0,
            )

        language = estimate_language(text)
        word_count = _word_count(text)
        if language is SummaryLanguage.ENGLISH:
            return EnrichmentPlan(
                action=EnrichmentAction.TRANSLATE,
                reason="Existing summary appears to be English.",
                language=language.value,
                confidence=0.9,
            )

        if language is SummaryLanguage.GERMAN:
            if word_count < self._german_improve_threshold_words:
                return EnrichmentPlan(
                    action=EnrichmentAction.IMPROVE,
                    reason=(
                        "German summary is shorter than the configured threshold "
                        f"({word_count}/{self._german_improve_threshold_words} words)."
                    ),
                    language=language.value,
                    confidence=0.85,
                )

            return EnrichmentPlan(
                action=EnrichmentAction.SKIP,
                reason="German summary already appears complete enough.",
                language=language.value,
                confidence=0.8,
            )

        if language is SummaryLanguage.OTHER:
            return EnrichmentPlan(
                action=EnrichmentAction.REVIEW,
                reason="Summary language is neither clearly German nor English.",
                language=language.value,
                confidence=0.5,
            )

        return EnrichmentPlan(
            action=EnrichmentAction.REVIEW,
            reason="Summary language could not be determined confidently.",
            language=language.value,
            confidence=0.4,
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


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    """Count keyword hits in text."""
    return sum(text.count(keyword) for keyword in keywords)


def _word_count(text: str) -> int:
    """Return a whitespace word count."""
    return len(text.split()) if text.strip() else 0
