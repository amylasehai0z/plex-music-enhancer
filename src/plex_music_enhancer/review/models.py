"""Models for interactive summary review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.editorial import GermanStyleDiagnostics
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
    critical_validation: str = "PASS"
    editorial_validation: str = "PASS"
    publishable: bool = True
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
    style: GermanStyleDiagnostics = Field(default_factory=lambda: _empty_style_diagnostics())
    edited: bool = False
    plan: EnrichmentPlan | None = None


def _empty_style_diagnostics() -> GermanStyleDiagnostics:
    """Return neutral style diagnostics for legacy direct model construction."""
    return GermanStyleDiagnostics(
        sentence_variation="GOOD",
        vocabulary_diversity="GOOD",
        repetition="NONE",
        readability="GOOD",
        llm_cliches="NONE",
        passive_voice="NONE",
        overall_style="GOOD",
        readability_score=0,
        average_sentence_length=0,
        average_paragraph_length=0,
        lexical_diversity=0,
    )
