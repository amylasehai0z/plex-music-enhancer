"""Translation service for existing Plex album summaries."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.enrichment import AlbumContext
from plex_music_enhancer.planner.planner import estimate_language
from plex_music_enhancer.plex.audit import SummaryLanguage
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.translation.models import AlbumTranslationDocument, TranslationValidation

TRANSLATION_PROMPT_NAME = "album_translate"


class TranslationError(Exception):
    """Raised when a summary cannot be translated safely."""


class _ContextPipeline(Protocol):
    """Context pipeline required by translation."""

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Collect album context."""


class _AIManager(Protocol):
    """AI manager methods required by translation."""

    def render_album_summary_prompt(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> RenderedPrompt:
        """Render an album prompt."""

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate a summary from a rendered prompt."""


class TranslationService:
    """Translate existing English Plex album summaries into German."""

    def __init__(self, *, pipeline: _ContextPipeline, ai_manager: _AIManager) -> None:
        """Create a translation service."""
        self._pipeline = pipeline
        self._ai_manager = ai_manager

    def translate_album(self, *, artist: str, album: str) -> AlbumTranslationDocument:
        """Translate one existing Plex album summary into German."""
        context = self._pipeline.collect_album_context(artist=artist, album=album)
        original_summary = (context.plex.summary or "").strip()
        validation = validate_translation_source(original_summary)
        if not validation.can_translate:
            raise TranslationError(validation.reason)

        rendered_prompt = self._ai_manager.render_album_summary_prompt(
            context,
            prompt_name=TRANSLATION_PROMPT_NAME,
        )
        start = perf_counter()
        generated_summary = self._ai_manager.generate_album_summary_from_prompt(rendered_prompt)
        generation_time_seconds = perf_counter() - start

        return AlbumTranslationDocument(
            context=context,
            rendered_prompt=rendered_prompt,
            generated_summary=generated_summary,
            original_summary=original_summary,
            translated_summary=generated_summary.text,
            validation=validation,
            generation_time_seconds=generation_time_seconds,
        )


def validate_translation_source(summary: str | None) -> TranslationValidation:
    """Validate whether a summary should be translated."""
    text = (summary or "").strip()
    word_count = len(text.split()) if text else 0
    if not text:
        return TranslationValidation(
            source_language=SummaryLanguage.UNKNOWN.value,
            can_translate=False,
            reason="No existing Plex summary is available to translate.",
            word_count=0,
        )

    source_language = _translation_source_language(text)
    if source_language == SummaryLanguage.GERMAN.value:
        return TranslationValidation(
            source_language=source_language,
            can_translate=False,
            reason="The existing Plex summary already appears to be German.",
            word_count=word_count,
        )

    return TranslationValidation(
        source_language=source_language,
        can_translate=True,
        reason="Existing Plex summary can be translated into German.",
        word_count=word_count,
    )


def _translation_source_language(summary: str) -> str:
    """Return a translation-specific source language classification."""
    planner_language = estimate_language(summary)
    lowered = f" {summary.casefold()} "
    has_german = planner_language is SummaryLanguage.GERMAN or any(
        marker in lowered for marker in (" der ", " die ", " das ", " und ", " ist ", " wurde ")
    )
    has_german = has_german or any(char in summary for char in "äöüÄÖÜß")
    has_english = any(
        marker in lowered
        for marker in (" the ", " and ", " is ", " with ", " was ", " were ", " from ")
    )
    if has_german and has_english:
        return "mixed"

    return planner_language.value
