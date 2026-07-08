"""Typed models for smart enrichment planning."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EnrichmentAction(StrEnum):
    """Recommended enrichment action."""

    CREATE = "CREATE"
    TRANSLATE = "TRANSLATE"
    IMPROVE = "IMPROVE"
    SKIP = "SKIP"
    REVIEW = "REVIEW"


class QualityLevel(StrEnum):
    """Content quality level."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class ContentIssue(StrEnum):
    """Detected content quality issue."""

    SHORT = "SHORT"
    PLACEHOLDER = "PLACEHOLDER"
    REPETITIVE = "REPETITIVE"
    MACHINE_TRANSLATION = "MACHINE_TRANSLATION"
    LOW_READABILITY = "LOW_READABILITY"
    UNKNOWN_LANGUAGE = "UNKNOWN_LANGUAGE"
    EXCESSIVE_WHITESPACE = "EXCESSIVE_WHITESPACE"
    FORMATTING_PROBLEMS = "FORMATTING_PROBLEMS"
    INCOMPLETE_SENTENCE = "INCOMPLETE_SENTENCE"
    MISSING = "MISSING"


class ContentQualityReport(BaseModel):
    """Quality analysis for an existing Plex summary."""

    model_config = ConfigDict(frozen=True)

    quality_score: int = Field(ge=0, le=100)
    quality_level: QualityLevel
    issues: list[ContentIssue] = Field(default_factory=list)


class EnrichmentPlan(BaseModel):
    """Recommended enrichment plan for one album."""

    model_config = ConfigDict(frozen=True)

    action: EnrichmentAction
    reason: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)
    quality: ContentQualityReport


class PlannedAlbum(BaseModel):
    """Album with its enrichment plan."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    library: str
    artist: str
    album: str
    current_summary: str | None = Field(default=None, serialization_alias="currentSummary")
    current_summary_words: int = Field(ge=0, serialization_alias="currentSummaryWords")
    plan: EnrichmentPlan


class PlanningReport(BaseModel):
    """Planning report for a set of albums."""

    model_config = ConfigDict(frozen=True)

    albums: list[PlannedAlbum]
