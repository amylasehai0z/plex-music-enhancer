"""Rule-based artist enrichment planner."""

from __future__ import annotations

from typing import Protocol

from plex_music_enhancer.planner.models import (
    ContentIssue,
    ContentQualityReport,
    EnrichmentAction,
    EnrichmentPlan,
    QualityLevel,
)
from plex_music_enhancer.plex.audit import SummaryLanguage

# Same thresholds as Album Planner for consistency
DEFAULT_GERMAN_IMPROVE_THRESHOLD_WORDS = 60
MINIMUM_GOOD_SCORE = 60
MINIMUM_SKIP_SCORE = 80


class ArtistPlanningCandidate(Protocol):
    """Minimal artist fields required for planning."""

    rating_key: str
    library: str
    artist: str
    current_summary: str | None


class ArtistEnrichmentPlanner:
    """Determine the best enrichment strategy for artist biographies before generation."""

    def __init__(
        self,
        *,
        german_improve_threshold_words: int = DEFAULT_GERMAN_IMPROVE_THRESHOLD_WORDS,
    ) -> None:
        """Create an artist enrichment planner."""
        self._german_improve_threshold_words = german_improve_threshold_words

    def plan_biography(self, biography: str | None) -> EnrichmentPlan:
        """Return the recommended plan for an artist biography.
        
        Mirrors album planning logic but for artist biographies:
        - CREATE: No biography exists
        - TRANSLATE: Existing biography is English
        - IMPROVE: German biography but quality score < 60
        - REVIEW: German biography with score 60-80 (user decides)
        - SKIP: German biography with score > 80
        """
        text = (biography or "").strip()
        if not text:
            quality = ContentQualityReport(
                quality_score=0,
                quality_level=QualityLevel.POOR,
                issues=[ContentIssue.MISSING],
            )
            return EnrichmentPlan(
                action=EnrichmentAction.CREATE,
                reason="Missing artist biography.",
                language=SummaryLanguage.UNKNOWN.value,
                confidence=1.0,
                quality=quality,
            )

        language = _estimate_biography_language(text)
        quality = _analyze_biography_quality(text, language=language)

        if language is SummaryLanguage.ENGLISH:
            return EnrichmentPlan(
                action=EnrichmentAction.TRANSLATE,
                reason="Existing biography appears to be English.",
                language=language.value,
                confidence=0.9,
                quality=quality,
            )

        if language is SummaryLanguage.GERMAN:
            if quality.quality_score < MINIMUM_GOOD_SCORE:
                return EnrichmentPlan(
                    action=EnrichmentAction.IMPROVE,
                    reason=f"German biography quality is poor ({quality.quality_score}/100).",
                    language=language.value,
                    confidence=0.85,
                    quality=quality,
                )

            if quality.quality_score <= MINIMUM_SKIP_SCORE:
                return EnrichmentPlan(
                    action=EnrichmentAction.REVIEW,
                    reason=(
                        "German biography quality is acceptable but should be reviewed "
                        f"({quality.quality_score}/100)."
                    ),
                    language=language.value,
                    confidence=0.7,
                    quality=quality,
                )

            return EnrichmentPlan(
                action=EnrichmentAction.SKIP,
                reason=f"German biography quality is high ({quality.quality_score}/100).",
                language=language.value,
                confidence=0.8,
                quality=quality,
            )

        # Unknown or other language
        return EnrichmentPlan(
            action=EnrichmentAction.REVIEW,
            reason=f"Biography language is {language.value}; human review recommended.",
            language=language.value,
            confidence=0.6,
            quality=quality,
        )


def _estimate_biography_language(text: str) -> SummaryLanguage:
    """Estimate language of artist biography using heuristic patterns.
    
    Mirrors the album planner's language detection but tuned for biographies.
    """
    normalized = text.lower()

    # German indicators (weighted)
    german_indicators = [
        "ü", "ö", "ä", "ß",  # German characters
        " und ", " ist ", " der ", " die ", " das ", " von ", " in ",
        " wurde ", " hat ", " sich ", " als ", " mit ", " über ",
    ]
    german_score = sum(1 for indicator in german_indicators if indicator in normalized)

    # English indicators (weighted)
    english_indicators = [
        " and ", " is ", " the ", " of ", " in ", " was ", " has ", " been ",
        " as ", " with ", " for ", " on ", " at ", " this ", " that ",
    ]
    english_score = sum(1 for indicator in english_indicators if indicator in normalized)

    if german_score > english_score:
        return SummaryLanguage.GERMAN
    elif english_score > german_score:
        return SummaryLanguage.ENGLISH
    else:
        return SummaryLanguage.UNKNOWN


def _analyze_biography_quality(
    text: str, language: SummaryLanguage
) -> ContentQualityReport:
    """Analyze quality of artist biography text.
    
    Mirrors album quality analysis but adapted for biography context.
    Checks for: length, structure, common pitfalls, style issues.
    """
    issues: list[ContentIssue] = []
    scores: dict[str, float] = {}

    # Length check (biographies typically 150-300 words)
    word_count = len(text.split())
    if word_count < 50:
        issues.append(ContentIssue.TOO_SHORT)
        scores["length"] = max(0, word_count / 50 * 60)
    elif word_count > 500:
        issues.append(ContentIssue.TOO_LONG)
        scores["length"] = max(40, 100 - (word_count - 500) / 1000 * 40)
    else:
        scores["length"] = 100

    # Structure check (should be prose, not bullets or lists)
    if any(text.startswith(prefix) for prefix in ["•", "-", "*", "·"]):
        issues.append(ContentIssue.MARKDOWN_DETECTED)
        scores["structure"] = 50
    elif text.count("\n") > 4:
        issues.append(ContentIssue.MARKDOWN_DETECTED)
        scores["structure"] = 60
    else:
        scores["structure"] = 100

    # Language consistency check
    if language is SummaryLanguage.GERMAN:
        # Check for English words in German text (simple heuristic)
        english_words = [
            "the ", "and ", "is ", "was ", "has been",
            "one of", "also known", "best known for",
        ]
        english_count = sum(
            1 for word in english_words if word.lower() in text.lower()
        )
        if english_count > 3:
            issues.append(ContentIssue.MIXED_LANGUAGE)
            scores["language"] = max(50, 100 - english_count * 10)
        else:
            scores["language"] = 100
    else:
        scores["language"] = 100

    # Generic quality baseline
    if not issues:
        scores["baseline"] = 100
    else:
        scores["baseline"] = max(40, 100 - len(issues) * 15)

    # Aggregate score (weighted average)
    weights = {"length": 0.25, "structure": 0.25, "language": 0.25, "baseline": 0.25}
    quality_score = sum(
        scores.get(key, 50) * weight for key, weight in weights.items()
    )
    quality_score = round(max(0, min(100, quality_score)))

    # Determine quality level
    if quality_score >= 80:
        quality_level = QualityLevel.EXCELLENT
    elif quality_score >= 60:
        quality_level = QualityLevel.GOOD
    elif quality_score >= 40:
        quality_level = QualityLevel.ACCEPTABLE
    else:
        quality_level = QualityLevel.POOR

    return ContentQualityReport(
        quality_score=quality_score,
        quality_level=quality_level,
        issues=issues,
    )
