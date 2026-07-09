"""Review/apply policy for generated summaries."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.quality import QualityLevel
from plex_music_enhancer.review.models import ReviewDocument
from plex_music_enhancer.verification import VerificationState

ValidationState = Literal["PASS", "WARNINGS", "FAIL"]

CRITICAL_CHECKS = frozenset(
    {
        "not_empty",
        "language_is_german",
        "no_placeholder_text",
        "no_markdown",
        "no_bullet_lists",
    }
)

EDITORIAL_WARNING_CHECKS = frozenset(
    {
        "length_in_range",
        "strong_opening",
        "natural_transitions",
        "varied_sentence_openings",
        "not_fact_list_style",
        "complete_closing",
    }
)

PUBLISHABLE_LEVELS = frozenset(
    {
        QualityLevel.GOOD,
        QualityLevel.VERY_GOOD,
        QualityLevel.EXCELLENT,
    }
)

DEFAULT_EDITORIAL_SCORE_THRESHOLD = 85
DEFAULT_VERIFICATION_CONFIDENCE_THRESHOLD = 0.7


class ReviewPolicyResult(BaseModel):
    """Decision produced by the review/apply policy."""

    model_config = ConfigDict(frozen=True)

    critical_validation: ValidationState
    editorial_validation: ValidationState
    publishable: bool
    apply_allowed: bool
    critical_failures: list[str] = Field(default_factory=list)
    editorial_warnings: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


def evaluate_review_policy(
    document: ReviewDocument,
    *,
    editorial_score_threshold: int = DEFAULT_EDITORIAL_SCORE_THRESHOLD,
    verification_confidence_threshold: float = DEFAULT_VERIFICATION_CONFIDENCE_THRESHOLD,
) -> ReviewPolicyResult:
    """Return whether a reviewed summary may be applied."""
    critical_failures = _critical_failures(
        document,
        verification_confidence_threshold=verification_confidence_threshold,
    )
    editorial_warnings = _editorial_warnings(document)
    score_passes, score_message = _editorial_score_passes(
        document,
        editorial_score_threshold=editorial_score_threshold,
    )

    messages: list[str] = []
    if score_message is not None:
        messages.append(score_message)

    critical_validation: ValidationState = "FAIL" if critical_failures else "PASS"
    if critical_failures:
        editorial_validation: ValidationState = "FAIL" if not score_passes else "WARNINGS"
    elif not score_passes:
        editorial_validation = "FAIL"
    elif editorial_warnings:
        editorial_validation = "WARNINGS"
    else:
        editorial_validation = "PASS"

    publishable = critical_validation == "PASS" and editorial_validation in {"PASS", "WARNINGS"}
    return ReviewPolicyResult(
        critical_validation=critical_validation,
        editorial_validation=editorial_validation,
        publishable=publishable,
        apply_allowed=publishable,
        critical_failures=critical_failures,
        editorial_warnings=editorial_warnings,
        messages=messages,
    )


def _critical_failures(
    document: ReviewDocument,
    *,
    verification_confidence_threshold: float,
) -> list[str]:
    """Return hard failures that must block apply."""
    failures: list[str] = []
    checks = document.quality.checks
    for check in CRITICAL_CHECKS:
        if checks.get(check) is False:
            failures.append(_critical_failure_message(check))

    if not document.proposed_summary.strip():
        failures.append("Generated text is empty.")

    failures.extend(document.quality.failures)
    failures.extend(_verification_failures(document, threshold=verification_confidence_threshold))
    return _deduplicate(failures)


def _editorial_warnings(document: ReviewDocument) -> list[str]:
    """Return non-blocking editorial warnings."""
    warnings = list(document.quality.warnings)
    checks = document.quality.checks
    for check in EDITORIAL_WARNING_CHECKS:
        if checks.get(check) is False:
            warnings.append(_editorial_warning_message(check))

    warnings.extend(document.style.issues)
    return _deduplicate(warnings)


def _editorial_score_passes(
    document: ReviewDocument,
    *,
    editorial_score_threshold: int,
) -> tuple[bool, str | None]:
    """Return whether deterministic editorial QA is good enough for publication."""
    report = getattr(document.preview, "qa_report", None)
    if report is None:
        return True, None

    level = report.overall_level or report.quality_level
    if report.overall_score >= editorial_score_threshold or level in PUBLISHABLE_LEVELS:
        return True, None

    return False, "Generated summary does not yet meet the required editorial quality."


def _verification_failures(document: ReviewDocument, *, threshold: float) -> list[str]:
    """Return verification-related hard failures."""
    collection = getattr(document.preview.context, "fact_collection", None)
    if collection is None:
        return []

    failures: list[str] = []
    conflicting_facts = [
        fact
        for fact in [*collection.conflicts, *collection.facts]
        if fact.verification_state == VerificationState.CONFLICTING
    ]
    if conflicting_facts:
        failures.append("Factual conflicts exist.")

    mentioned_weak_facts = _mentioned_unreliable_fact_categories(document)
    if not mentioned_weak_facts:
        return failures

    low_confidence = [
        fact
        for fact in collection.facts
        if fact.value
        and fact.category in mentioned_weak_facts
        and fact.verification_state != VerificationState.UNKNOWN
        and fact.confidence_score < threshold
    ]
    if low_confidence:
        failures.append(
            "Verification confidence is below the configured threshold " f"({threshold:.2f})."
        )

    return failures


def _mentioned_unreliable_fact_categories(document: ReviewDocument) -> set[str]:
    """Return unreliable fact categories that QA detected in generated prose."""
    report = getattr(document.preview, "qa_report", None)
    if report is None:
        return set()

    metrics = report.verification_metrics
    return {
        *metrics.weak_facts_mentioned,
        *metrics.unknown_facts_mentioned,
        *metrics.conflicting_facts_mentioned,
    }


def _critical_failure_message(check: str) -> str:
    """Return a human-readable hard failure message."""
    messages = {
        "not_empty": "Summary is empty.",
        "language_is_german": "Summary does not appear to be German.",
        "no_placeholder_text": "Summary contains placeholder text.",
        "no_markdown": "Summary contains Markdown formatting.",
        "no_bullet_lists": "Summary contains bullet lists.",
    }
    return messages.get(check, f"Critical validation failed: {check}.")


def _editorial_warning_message(check: str) -> str:
    """Return a human-readable editorial warning message."""
    messages = {
        "length_in_range": "Summary length is outside the configured range.",
        "strong_opening": "WEAK_OPENING: Summary opens with generic or weak phrasing.",
        "natural_transitions": "POOR_TRANSITIONS: Summary lacks natural transitions.",
        "varied_sentence_openings": "REPETITIVE_SENTENCE_STARTS: Summary repeats openings.",
        "not_fact_list_style": "FACT_LIST_STYLE: Summary reads like a metadata list.",
        "complete_closing": "ABRUPT_ENDING: Summary ends abruptly or incompletely.",
    }
    return messages.get(check, f"Editorial recommendation: {check}.")


def _deduplicate(values: list[str]) -> list[str]:
    """Return values without duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
