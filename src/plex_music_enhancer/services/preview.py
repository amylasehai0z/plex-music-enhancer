"""End-to-end album enrichment preview service."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

from plex_music_enhancer.ai.manager import AIManager
from plex_music_enhancer.ai.models import GeneratedSummary
from plex_music_enhancer.editorial import GermanEditorialStyleEngine, GermanStyleDiagnostics
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
    style_diagnostics: GermanStyleDiagnostics | None = None
    career_years: str = "unknown"
    source_availability: dict[str, str] = Field(default_factory=dict)
    editorial_recommendations: list[str] = Field(default_factory=list)
    resolved_prompt_variables: dict[str, Any] = Field(default_factory=dict)
    knowledge_summary: dict[str, Any] = Field(default_factory=dict)
    context_summary: dict[str, Any] = Field(default_factory=dict)


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
        style_engine: GermanEditorialStyleEngine | None = None,
    ) -> None:
        """Create an enrichment preview service."""
        if pipeline is None:
            from plex_music_enhancer.enrichment import EnrichmentPipeline

            pipeline = EnrichmentPipeline(base_url, token)

        self._pipeline = pipeline
        self._ai_manager = ai_manager or AIManager()
        self._quality_engine = quality_engine or EditorialQualityEngine()
        self._style_engine = style_engine or GermanEditorialStyleEngine()

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

        qa_report = self._quality_engine.analyze_artist(context, generated_summary.text)
        return ArtistPreviewDocument(
            context=context,
            rendered_prompt=rendered_prompt,
            generated_summary=generated_summary,
            generation_time_seconds=generation_time_seconds,
            qa_report=qa_report,
            style_diagnostics=self._style_engine.analyze(
                generated_summary.text,
                artist=context.plex.artist,
                album=None,
            ),
            career_years=_artist_career_years(context),
            source_availability=_artist_source_availability(context),
            editorial_recommendations=[str(item) for item in qa_report.recommendations],
            resolved_prompt_variables=_artist_resolved_prompt_variables(context),
            knowledge_summary=_artist_knowledge_summary(context),
            context_summary=_artist_context_summary(context),
        )


def _artist_career_years(context: ArtistContext) -> str:
    """Return displayable career years without falling back to birth dates."""
    birth_date = context.birth_date or context.musicbrainz.begin_date
    for value in (context.active_years, context.discogs.active_years):
        text = str(value).strip() if value else ""
        if not text:
            continue
        if birth_date and text == birth_date:
            continue
        if "-" in text or "–" in text or "present" in text.casefold():
            return text
        if len(text) == 4 and text.isdigit():
            return f"{text}–"
    return "unknown"


def _artist_source_availability(context: ArtistContext) -> dict[str, str]:
    """Return concise source availability diagnostics for one artist preview."""
    return {
        "plex": "available" if context.plex.artist else "missing",
        "musicbrainz": (
            "available"
            if context.musicbrainz.artist_mbid
            or context.musicbrainz.artist_name
            or context.musicbrainz.genres
            else "missing"
        ),
        "wikipedia": "available" if context.wikipedia.extract else "missing",
        "discogs": "available" if _discogs_artist_has_unique_data(context) else "missing",
        "lastfm": "available" if context.lastfm.biography or context.lastfm.tags else "missing",
    }


def _artist_resolved_prompt_variables(context: ArtistContext) -> dict[str, Any]:
    """Return populated artist facts represented in the rendered prompt context."""
    variables: dict[str, Any] = {
        "artist": context.plex.artist,
        "aliases": context.aliases,
        "genres": context.genres or context.musicbrainz.genres or context.plex.genres,
        "styles": context.styles,
        "career_summary": context.career_summary,
        "historical_context": context.historical_context,
        "important_albums": context.notable_albums,
        "major_works": [*context.notable_albums, *context.milestones],
        "milestones": context.milestones,
        "labels": context.labels,
        "associated_artists": context.associated_acts,
        "knowledge_context": _artist_knowledge_summary(context),
        "wikipedia_extract": context.wikipedia.extract,
        "discogs_context": _discogs_artist_context(context),
        "lastfm_context": _lastfm_artist_context(context),
        "current_summary": context.plex.summary,
        "career_years": _artist_career_years(context),
        "birth_date": context.birth_date,
        "death_date": context.death_date,
        "nationality": context.nationality,
        "origin": context.origin or context.plex.country,
        "legacy": [*context.awards, *context.influenced_artists],
    }
    return {
        key: value
        for key, value in variables.items()
        if _has_prompt_value(value) and value != "unknown"
    }


def _artist_knowledge_summary(context: ArtistContext) -> dict[str, Any]:
    """Return verified fact counts and conflicts for artist preview export."""
    facts = [fact for fact in context.fact_collection.facts if fact.value]
    return {
        "fact_count": len(facts),
        "verified_count": sum(1 for fact in facts if fact.verification_state == "verified"),
        "probable_count": sum(1 for fact in facts if fact.verification_state == "probable"),
        "conflict_count": len(context.fact_collection.conflicts),
        "missing_facts": context.fact_collection.missing_facts,
    }


def _artist_context_summary(context: ArtistContext) -> dict[str, Any]:
    """Return context-builder diagnostics for artist preview export."""
    return {
        "collected_sources": context.pipeline.collected_sources,
        "missing_fields": context.pipeline.missing_fields,
        "warnings": context.pipeline.warnings,
        "ready_for_generation": context.pipeline.ready_for_generation,
    }


def _discogs_artist_context(context: ArtistContext) -> dict[str, Any]:
    """Return unique Discogs artist fields only."""
    discogs = context.discogs
    data = {
        "profile": discogs.profile if _is_unique_discogs_text(context, discogs.profile) else None,
        "members": discogs.members,
        "aliases": discogs.aliases,
        "name_variations": discogs.name_variations,
        "genres": discogs.genres,
        "styles": discogs.styles,
        "active_years": discogs.active_years,
    }
    return {key: value for key, value in data.items() if _has_prompt_value(value)}


def _lastfm_artist_context(context: ArtistContext) -> dict[str, Any]:
    """Return populated Last.fm fields for artist preview export."""
    lastfm = context.lastfm
    data = {
        "biography": lastfm.biography,
        "short_biography": lastfm.short_biography,
        "tags": lastfm.tags,
        "similar_artists": lastfm.similar_artists,
        "listeners": lastfm.listeners,
        "playcount": lastfm.playcount,
        "url": lastfm.url,
    }
    return {key: value for key, value in data.items() if _has_prompt_value(value)}


def _discogs_artist_has_unique_data(context: ArtistContext) -> bool:
    """Return whether Discogs contributes non-duplicated artist context."""
    return bool(_discogs_artist_context(context))


def _is_unique_discogs_text(context: ArtistContext, text: str | None) -> bool:
    """Return whether Discogs prose differs from existing authoritative prose."""
    if not text:
        return False
    normalized = _normalize_text(text)
    duplicates = (
        context.wikipedia.extract,
        context.career_summary,
        context.biography,
        context.plex.summary,
    )
    return all(_normalize_text(value) != normalized for value in duplicates if value)


def _has_prompt_value(value: object) -> bool:
    """Return whether a diagnostic prompt variable is populated."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_prompt_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_prompt_value(item) for item in value)
    return True


def _normalize_text(value: str | None) -> str:
    """Return normalized text for duplicate detection."""
    return " ".join(value.casefold().split()) if value else ""
