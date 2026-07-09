"""Typed models for editorial album composition."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.verification.models import VerifiedFact

FactConfidence = Literal["high", "medium", "low"]


class EditorialFact(BaseModel):
    """One prioritized fact prepared for narrative use."""

    model_config = ConfigDict(frozen=True)

    topic: str
    text: str
    sources: list[str] = Field(default_factory=list)
    priority: int = Field(ge=0, le=100)
    confidence: FactConfidence


class EditorialContext(BaseModel):
    """Structured writing guidance for an album summary prompt."""

    model_config = ConfigDict(frozen=True)

    opening_focus: str | None = None
    career_context: list[EditorialFact] | None = None
    recording_context: list[EditorialFact] | None = None
    musical_style: list[EditorialFact] | None = None
    production_context: list[EditorialFact] | None = None
    personnel_context: list[EditorialFact] | None = None
    lyrical_context: list[EditorialFact] | None = None
    historical_context: list[EditorialFact] | None = None
    legacy_context: list[EditorialFact] | None = None
    recommended_story_order: list[str] | None = None
    notable_tracks: list[str] | None = None
    important_facts: list[EditorialFact] | None = None
    avoid_topics: list[str] | None = None
    missing_context: list[str] | None = None
    writing_guidance: list[str] | None = None
    verified_facts: list[VerifiedFact] | None = None
    probable_facts: list[VerifiedFact] | None = None
    weak_facts: list[VerifiedFact] | None = None
    conflicting_facts: list[VerifiedFact] | None = None
    missing_facts: list[str] | None = None
