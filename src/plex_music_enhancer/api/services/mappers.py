"""Mapping helpers from domain documents to internal API documents."""

from __future__ import annotations

from typing import Any

from plex_music_enhancer.api.models import (
    API_VERSION,
    DebugMeta,
    EditorialAnalysis,
    PromptAnalysis,
    QualityAnalysis,
    ReviewDocument,
    ReviewMode,
    ReviewTarget,
    TokenUsage,
    VerificationAnalysis,
)
from plex_music_enhancer.quality import QualityReport as EditorialQualityReport
from plex_music_enhancer.review import ReviewDocument as DomainReviewDocument


def review_document_to_api(
    document: DomainReviewDocument,
    *,
    target: ReviewTarget | None = None,
    mode: ReviewMode = "create",
) -> ReviewDocument:
    """Return the stable internal API representation of a review document."""
    preview = document.preview
    context = preview.context
    generated = preview.generated_summary
    prompt = preview.rendered_prompt
    qa_report = getattr(preview, "qa_report", None)
    resolved_target: ReviewTarget = target or (
        "album" if hasattr(context.plex, "album") else "artist"
    )
    artist = context.plex.artist
    album = getattr(context.plex, "album", None)
    rating_key = getattr(context.plex, "rating_key", None)

    return ReviewDocument(
        api_version=API_VERSION,
        target=resolved_target,
        mode=mode,
        artist=artist,
        album=album,
        rating_key=rating_key,
        current_summary=document.current_summary,
        generated_summary=generated.text,
        proposed_summary=document.proposed_summary,
        unified_diff=document.diff,
        qa=_quality_analysis(document, qa_report),
        editorial=_editorial_analysis(qa_report),
        verification=_verification_analysis(qa_report),
        prompt=_prompt_analysis(prompt),
        debug=_debug_meta(preview),
        provider=generated.provider,
        model=generated.model,
        edited=document.edited,
        plan=document.plan.model_dump(mode="json") if document.plan is not None else None,
        context=_context_summary(context),
    )


def _quality_analysis(
    document: DomainReviewDocument,
    qa_report: EditorialQualityReport | None,
) -> QualityAnalysis:
    """Return review quality analysis."""
    return QualityAnalysis(
        status=document.quality.status,
        critical_validation=document.quality.critical_validation,
        editorial_validation=document.quality.editorial_validation,
        publishable=document.quality.publishable,
        word_count=document.quality.word_count,
        checks=document.quality.checks,
        warnings=document.quality.warnings,
        failures=document.quality.failures,
        overall_score=getattr(qa_report, "overall_score", None),
        overall_level=_level_value(qa_report),
    )


def _editorial_analysis(qa_report: EditorialQualityReport | None) -> EditorialAnalysis:
    """Return editorial analysis from QA data."""
    if qa_report is None:
        return EditorialAnalysis()
    return EditorialAnalysis(
        score=qa_report.overall_score,
        level=_level_value(qa_report),
        recommendations=[str(item) for item in qa_report.recommendations],
        missing_topics=qa_report.missing_topics,
        style_metrics=qa_report.style_metrics,
        editorial_metrics=qa_report.editorial_metrics.model_dump(mode="json"),
    )


def _verification_analysis(qa_report: EditorialQualityReport | None) -> VerificationAnalysis:
    """Return verification analysis from QA data."""
    if qa_report is None:
        return VerificationAnalysis()
    metrics = qa_report.verification_metrics
    return VerificationAnalysis(
        verified_facts=len(metrics.verified_facts_mentioned),
        weak_facts=len(metrics.weak_facts_mentioned),
        conflicting_facts=len(metrics.conflicting_facts_mentioned),
        unknown_facts=len(metrics.unknown_facts_mentioned),
        coverage_score=metrics.coverage_score,
        conflicts=metrics.conflicting_facts_mentioned,
        missing_facts=metrics.verified_facts_omitted,
    )


def _prompt_analysis(prompt: Any) -> PromptAnalysis:
    """Return prompt analysis from a rendered prompt."""
    diagnostics = prompt.budget_diagnostics or {}
    quality = diagnostics.get("prompt_quality", {})
    return PromptAnalysis(
        name=prompt.name,
        version=prompt.version,
        characters=len(prompt.rendered_text),
        estimated_tokens=(
            max(1, round(len(prompt.rendered_text) / 4)) if prompt.rendered_text else 0
        ),
        budget=diagnostics.get("max_characters"),
        trimmed=bool(diagnostics.get("trimmed", False)),
        budget_diagnostics=diagnostics,
        decisions=_dict_of_lists(diagnostics.get("prompt_decisions")),
        quality=quality if isinstance(quality, dict) else {},
        efficiency=quality.get("prompt_efficiency") if isinstance(quality, dict) else None,
        utilization=_prompt_utilization(diagnostics),
        evidence_ranking=_dict_of_ints(diagnostics.get("evidence_ranking")),
        evidence_coverage=_coverage_from_quality(quality),
        editorial_coverage=_coverage_from_quality(quality),
        editorial_balance=_balance_from_quality(quality),
        missed_opportunities=_missed_opportunities(diagnostics),
    )


def _debug_meta(preview: Any) -> DebugMeta:
    """Return provider and timing debug metadata."""
    generated = preview.generated_summary
    metadata = generated.metadata
    return DebugMeta(
        provider=generated.provider,
        model=generated.model,
        generation_time_seconds=preview.generation_time_seconds,
        token_usage=TokenUsage(
            prompt_tokens=_optional_int(metadata.get("prompt_tokens")),
            completion_tokens=_optional_int(metadata.get("completion_tokens")),
        ),
        source_count=generated.source_count,
        raw=metadata,
    )


def _context_summary(context: Any) -> dict[str, Any]:
    """Return a compact context summary suitable for API payloads."""
    return {
        "artist": context.plex.artist,
        "album": getattr(context.plex, "album", None),
        "ratingKey": getattr(context.plex, "rating_key", None),
        "sources": list(getattr(context.pipeline, "collected_sources", [])),
        "warnings": list(getattr(context.pipeline, "warnings", [])),
    }


def _level_value(report: EditorialQualityReport | None) -> str | None:
    """Return a serializable QA level."""
    if report is None:
        return None
    level = report.overall_level or report.quality_level
    return str(level.value if hasattr(level, "value") else level) if level else None


def _dict_of_lists(value: object) -> dict[str, list[str]]:
    """Return a dict[str, list[str]] when possible."""
    if not isinstance(value, dict):
        return {}
    return {
        str(key): [str(item) for item in items]
        for key, items in value.items()
        if isinstance(items, list)
    }


def _dict_of_ints(value: object) -> dict[str, int]:
    """Return a dict[str, int] when possible."""
    if not isinstance(value, dict):
        return {}
    return {str(key): int(item) for key, item in value.items() if isinstance(item, int)}


def _optional_int(value: object) -> int | None:
    """Return an optional int for provider metadata."""
    return value if isinstance(value, int) else None


def _prompt_utilization(diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Return compact prompt utilization metrics."""
    return {
        "budgetUsed": diagnostics.get("prompt_budget_used"),
        "budgetTrimmed": diagnostics.get("prompt_budget_trimmed"),
        "sourceSizes": diagnostics.get("source_sizes", {}),
    }


def _coverage_from_quality(quality: object) -> dict[str, Any]:
    """Return coverage-style metrics from prompt quality diagnostics."""
    if not isinstance(quality, dict):
        return {}
    return {
        "historical": quality.get("historical_coverage"),
        "career": quality.get("career_coverage"),
        "legacy": quality.get("legacy_coverage"),
    }


def _balance_from_quality(quality: object) -> dict[str, Any]:
    """Return balance-style metrics from prompt quality diagnostics."""
    if not isinstance(quality, dict):
        return {}
    return {
        "sourceBalance": quality.get("source_balance"),
        "evidenceDiversity": quality.get("evidence_diversity"),
        "informationDensity": quality.get("information_density"),
    }


def _missed_opportunities(diagnostics: dict[str, Any]) -> list[str]:
    """Return missed opportunity hints from prompt decisions when available."""
    decisions = diagnostics.get("prompt_decisions")
    if not isinstance(decisions, dict):
        return []
    removed = decisions.get("removed")
    return [str(item) for item in removed] if isinstance(removed, list) else []
