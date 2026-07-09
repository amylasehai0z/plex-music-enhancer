"""End-to-end album enrichment preview service."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

from plex_music_enhancer.ai.manager import AIManager
from plex_music_enhancer.ai.models import GeneratedSummary
from plex_music_enhancer.enrichment.models import AlbumContext, ArtistContext
from plex_music_enhancer.prompts.renderer import RenderedPrompt
from plex_music_enhancer.quality import EditorialQualityEngine, QualityReport
from plex_music_enhancer.translation import TranslationError, TranslationService


class EnrichmentPreviewDocument(BaseModel):
    """Complete read-only preview document for one album."""

    model_config = ConfigDict(frozen=True)

    context: AlbumContext
    rendered_prompt: RenderedPrompt
    generated_summary: GeneratedSummary
    generation_time_seconds: float = Field(ge=0)
    qa_report: QualityReport | None = None


class ArtistPreviewDocument(BaseModel):
    """Complete read-only preview document for one artist."""

    model_config = ConfigDict(frozen=True)

    context: ArtistContext
    rendered_prompt: RenderedPrompt
    generated_summary: GeneratedSummary
    generation_time_seconds: float = Field(ge=0)
    qa_report: QualityReport | None = None


class PreviewError(Exception):
    """Raised when an enrichment preview cannot be prepared."""


class _ContextPipeline(Protocol):
    """Album context pipeline protocol used by preview."""

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Collect album context."""

    def collect_artist_context(self, *, artist: str) -> ArtistContext:
        """Collect artist context."""


class _AIManager(Protocol):
    """AI manager protocol used by preview."""

    def render_album_summary_prompt(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> RenderedPrompt:
        """Render an album summary prompt."""

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an album summary from a rendered prompt."""

    def render_artist_summary_prompt(self, context: ArtistContext) -> RenderedPrompt:
        """Render an artist summary prompt."""

    def generate_artist_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an artist summary from a rendered prompt."""


class EnrichmentPreviewService:
    """Prepare a read-only generated summary preview for one Plex album."""

    def __init__(
        self,
        base_url: AnyHttpUrl,
        token: SecretStr,
        *,
        pipeline: _ContextPipeline | None = None,
        ai_manager: _AIManager | None = None,
        quality_engine: EditorialQualityEngine | None = None,
    ) -> None:
        """Create an enrichment preview service."""
        if pipeline is None:
            from plex_music_enhancer.enrichment import EnrichmentPipeline

            pipeline = EnrichmentPipeline(base_url, token)

        self._pipeline = pipeline
        self._ai_manager = ai_manager or AIManager()
        self._quality_engine = quality_engine or EditorialQualityEngine()

    def preview_album(
        self,
        *,
        artist: str,
        album: str,
        prompt_name: str = "album_summary",
    ) -> EnrichmentPreviewDocument:
        """Build album context and generate a preview summary without modifying Plex."""
        if prompt_name == "album_translate":
            return self._preview_album_translation(artist=artist, album=album)

        try:
            context = self._pipeline.collect_album_context(artist=artist, album=album)
            rendered_prompt = (
                self._ai_manager.render_album_summary_prompt(context)
                if prompt_name == "album_summary"
                else self._ai_manager.render_album_summary_prompt(
                    context,
                    prompt_name=prompt_name,
                )
            )
            start = perf_counter()
            generated_summary = self._ai_manager.generate_album_summary_from_prompt(rendered_prompt)
            generation_time_seconds = perf_counter() - start
        except Exception as exc:
            msg = str(exc) or "Unable to generate album preview."
            raise PreviewError(msg) from exc

        return EnrichmentPreviewDocument(
            context=context,
            rendered_prompt=rendered_prompt,
            generated_summary=generated_summary,
            generation_time_seconds=generation_time_seconds,
            qa_report=self._quality_engine.analyze_album(context, generated_summary.text),
        )

    def _preview_album_translation(
        self,
        *,
        artist: str,
        album: str,
    ) -> EnrichmentPreviewDocument:
        """Build a translation preview using the translation engine."""
        try:
            document = TranslationService(
                pipeline=self._pipeline,
                ai_manager=self._ai_manager,
            ).translate_album(artist=artist, album=album)
        except TranslationError as exc:
            raise PreviewError(str(exc)) from exc
        except Exception as exc:
            msg = str(exc) or "Unable to translate album summary."
            raise PreviewError(msg) from exc

        return EnrichmentPreviewDocument(
            context=document.context,
            rendered_prompt=document.rendered_prompt,
            generated_summary=document.generated_summary,
            generation_time_seconds=document.generation_time_seconds,
            qa_report=self._quality_engine.analyze_album(
                document.context,
                document.generated_summary.text,
            ),
        )

    def preview_artist(self, *, artist: str) -> ArtistPreviewDocument:
        """Build artist context and generate a preview biography without modifying Plex."""
        try:
            context = self._pipeline.collect_artist_context(artist=artist)
            rendered_prompt = self._ai_manager.render_artist_summary_prompt(context)
            start = perf_counter()
            generated_summary = self._ai_manager.generate_artist_summary_from_prompt(
                rendered_prompt
            )
            generation_time_seconds = perf_counter() - start
        except Exception as exc:
            msg = str(exc) or "Unable to generate artist preview."
            raise PreviewError(msg) from exc

        return ArtistPreviewDocument(
            context=context,
            rendered_prompt=rendered_prompt,
            generated_summary=generated_summary,
            generation_time_seconds=generation_time_seconds,
            qa_report=self._quality_engine.analyze_artist(context, generated_summary.text),
        )
