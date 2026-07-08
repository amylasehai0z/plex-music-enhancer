"""Models for interactive summary review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.planner import EnrichmentPlan
from plex_music_enhancer.services import ArtistPreviewDocument, EnrichmentPreviewDocument

QualityStatus = Literal["PASS", "WARNINGS", "FAILED"]


class ReviewLimits(BaseModel):
    """Configurable quality limits for generated summaries."""

    model_config = ConfigDict(frozen=True)

    minimum_words: int = Field(default=80, ge=1)
    maximum_words: int = Field(default=120, ge=1)


class QualityReport(BaseModel):
    """Quality validation report for a generated or edited summary."""

    model_config = ConfigDict(frozen=True)

    status: QualityStatus
    checks: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    word_count: int = Field(ge=0)


class ReviewDocument(BaseModel):
    """Complete read-only review document."""

    model_config = ConfigDict(frozen=True)

    preview: EnrichmentPreviewDocument | ArtistPreviewDocument
    current_summary: str
    proposed_summary: str
    diff: str
    quality: QualityReport
    edited: bool = False
    plan: EnrichmentPlan | None = None
