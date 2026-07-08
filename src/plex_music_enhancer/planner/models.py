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


class EnrichmentPlan(BaseModel):
    """Recommended enrichment plan for one album."""

    model_config = ConfigDict(frozen=True)

    action: EnrichmentAction
    reason: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)


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
