"""Typed editorial QA models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualityLevel(StrEnum):
    """Overall deterministic QA level."""

    EXCELLENT = "EXCELLENT"
    VERY_GOOD = "VERY GOOD"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class QualityStatus(StrEnum):
    """Per-category QA status."""

    PASS = "PASS"  # noqa: S105 - QA status label, not a secret.
    GOOD = "GOOD"
    WARNING = "WARNING"
    FAIL = "FAIL"


class QualityCategory(StrEnum):
    """Editorial QA category names."""

    COMPLETENESS = "Completeness"
    FACT_COVERAGE = "Fact Coverage"
    VERIFICATION_CONFIDENCE = "Verification Confidence"
    EDITORIAL_FLOW = "Editorial Flow"
    READABILITY = "Readability"
    LEXICAL_DIVERSITY = "Lexical Diversity"
    SENTENCE_VARIETY = "Sentence Variety"
    GERMAN_LANGUAGE = "German Language"
    REPETITION = "Repetition"
    PLACEHOLDER_DETECTION = "Placeholder Detection"
    FORMATTING = "Formatting"
    NARRATIVE_STRUCTURE = "Narrative Structure"
    OVERALL_EDITORIAL_QUALITY = "Overall Editorial Quality"


class QualityRecommendation(BaseModel):
    """One deterministic QA recommendation."""

    model_config = ConfigDict(frozen=True)

    message: str
    category: QualityCategory | None = None
    priority: int = Field(default=3, ge=1, le=5)

    def __contains__(self, value: object) -> bool:
        """Support legacy substring checks against recommendation text."""
        return isinstance(value, str) and value in self.message

    def __str__(self) -> str:
        """Return user-facing recommendation text."""
        return self.message


class QualityCheck(BaseModel):
    """One scored editorial QA check."""

    model_config = ConfigDict(frozen=True)

    category: QualityCategory
    score: int = Field(ge=0, le=100)
    status: QualityStatus
    details: list[str] = Field(default_factory=list)


class VerificationMetrics(BaseModel):
    """Verification-aware QA metrics."""

    model_config = ConfigDict(frozen=True)

    verified_facts_mentioned: list[str] = Field(default_factory=list)
    verified_facts_omitted: list[str] = Field(default_factory=list)
    weak_facts_mentioned: list[str] = Field(default_factory=list)
    conflicting_facts_mentioned: list[str] = Field(default_factory=list)
    unknown_facts_mentioned: list[str] = Field(default_factory=list)
    coverage_score: int = Field(default=100, ge=0, le=100)


class MetadataCoverage(BaseModel):
    """Coverage of available context topics in generated prose."""

    model_config = ConfigDict(frozen=True)

    available_topics: list[str] = Field(default_factory=list)
    mentioned_topics: list[str] = Field(default_factory=list)
    omitted_topics: list[str] = Field(default_factory=list)
    coverage_score: int = Field(default=100, ge=0, le=100)


class EditorialMetrics(BaseModel):
    """Deterministic editorial structure metrics."""

    model_config = ConfigDict(frozen=True)

    sentence_count: int = Field(default=0, ge=0)
    paragraph_count: int = Field(default=0, ge=0)
    has_opening: bool = False
    has_closing: bool = False
    has_transition: bool = False
    chronological_flow: bool = False
    coherent_structure: bool = False


class QualityReport(BaseModel):
    """Complete deterministic editorial QA report."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    overall_score: int = Field(ge=0, le=100)
    overall_level: QualityLevel | None = None
    quality_level: QualityLevel | None = None
    checks: list[QualityCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[QualityRecommendation] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    style_metrics: dict[str, Any] = Field(default_factory=dict)
    verification_metrics: VerificationMetrics = Field(default_factory=VerificationMetrics)
    metadata_coverage: MetadataCoverage = Field(default_factory=MetadataCoverage)
    editorial_metrics: EditorialMetrics = Field(default_factory=EditorialMetrics)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def _sync_level_fields(cls, data: object) -> object:
        """Keep the new report name and the legacy alias in sync."""
        if isinstance(data, dict):
            level = data.get("overall_level") or data.get("quality_level")
            if level is not None:
                data.setdefault("overall_level", level)
                data.setdefault("quality_level", level)
        return data
