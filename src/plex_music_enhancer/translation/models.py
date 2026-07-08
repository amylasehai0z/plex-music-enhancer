"""Typed models for album summary translation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.enrichment import AlbumContext
from plex_music_enhancer.prompts import RenderedPrompt


class TranslationValidation(BaseModel):
    """Validation result for a translation source summary."""

    model_config = ConfigDict(frozen=True)

    source_language: str
    can_translate: bool
    reason: str
    word_count: int = Field(ge=0)


class AlbumTranslationDocument(BaseModel):
    """Complete translation result for one Plex album summary."""

    model_config = ConfigDict(frozen=True)

    context: AlbumContext
    rendered_prompt: RenderedPrompt
    generated_summary: GeneratedSummary
    original_summary: str
    translated_summary: str
    validation: TranslationValidation
    generation_time_seconds: float = Field(ge=0)
