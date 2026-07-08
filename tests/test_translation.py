"""Album translation engine tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.prompts import PromptBuilder, RenderedPrompt
from plex_music_enhancer.translation import TranslationError, TranslationService
from plex_music_enhancer.translation.service import validate_translation_source


def test_translation_rejects_empty_summary() -> None:
    """Translation should require an existing Plex summary."""
    validation = validate_translation_source("")
    service = _service(summary=None)

    assert validation.can_translate is False
    assert validation.source_language == "unknown"
    with pytest.raises(TranslationError, match="No existing Plex summary"):
        service.translate_album(artist="Nina Simone", album="Pastel Blues")


def test_translation_accepts_english_summary() -> None:
    """English summaries should be translated with the translation prompt."""
    summary = "The album was released in 1965 and includes the track Sinnerman."
    ai_manager = FakeAIManager(translated_text="Das Album wurde 1965 veröffentlicht.")
    service = _service(summary=summary, ai_manager=ai_manager)

    document = service.translate_album(artist="Nina Simone", album="Pastel Blues")

    assert document.validation.source_language == "english"
    assert document.original_summary == summary
    assert document.translated_summary == "Das Album wurde 1965 veröffentlicht."
    assert document.rendered_prompt.name == "album_translate"
    assert ai_manager.prompt is not None
    assert summary in ai_manager.prompt.rendered_text


def test_translation_accepts_mixed_english_and_german_summary() -> None:
    """Mixed summaries can still be explicitly translated."""
    summary = "Das Album was released in 1965 and contains reflective songs."

    document = _service(summary=summary).translate_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert document.validation.source_language == "mixed"
    assert document.validation.can_translate is True


def test_translation_accepts_long_english_summary() -> None:
    """Long English summaries should not be summarized before translation."""
    summary = " ".join(
        [
            "The album was recorded with a sparse arrangement and a reflective tone.",
            "It includes original material and interpretations connected by a consistent mood.",
        ]
        * 20
    )
    ai_manager = FakeAIManager()

    document = _service(summary=summary, ai_manager=ai_manager).translate_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert document.validation.word_count > 100
    assert ai_manager.prompt is not None
    assert summary in ai_manager.prompt.rendered_text
    assert (
        "Translate only; do not summarize or condense the text." in ai_manager.prompt.rendered_text
    )


def test_translation_rejects_already_german_summary() -> None:
    """Already German summaries should use improvement, not translation."""
    service = _service(
        summary="Das Album ist eine ruhige Aufnahme und wurde sorgfältig produziert."
    )

    with pytest.raises(TranslationError, match="already appears to be German"):
        service.translate_album(artist="Nina Simone", album="Pastel Blues")


def test_translation_prompt_preserves_punctuation_and_titles() -> None:
    """The prompt should preserve titles, release dates, track titles, and punctuation."""
    summary = 'The album was released on 1965-10-01 and includes "Sinnerman", "Strange Fruit".'
    ai_manager = FakeAIManager()

    _service(summary=summary, ai_manager=ai_manager).translate_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert ai_manager.prompt is not None
    rendered = ai_manager.prompt.rendered_text
    assert '"Sinnerman", "Strange Fruit".' in rendered
    assert "1965-10-01" in rendered
    assert "Keep artist names, album titles, song titles" in rendered
    assert "Preserve release dates and track titles exactly." in rendered
    assert "Translate prose only." in rendered


class FakePipeline:
    """Fake context pipeline for translation tests."""

    def __init__(self, summary: str | None) -> None:
        """Create a fake pipeline."""
        self._summary = summary

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Return album context."""
        return _album_context(artist=artist, album=album, summary=self._summary)


class FakeAIManager:
    """Fake AI manager for translation tests."""

    def __init__(self, translated_text: str = "Deutsche Übersetzung.") -> None:
        """Create a fake AI manager."""
        self.translated_text = translated_text
        self.prompt: RenderedPrompt | None = None

    def render_album_summary_prompt(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> RenderedPrompt:
        """Render the real translation prompt."""
        assert prompt_name == "album_translate"
        return PromptBuilder().build_album_summary_prompt(context, prompt_name=prompt_name)

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Return a fake translated summary."""
        self.prompt = prompt
        return GeneratedSummary(
            language="de",
            text=self.translated_text,
            provider="fake",
            model="fake-v1",
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=0.9,
            source_count=2,
            metadata={},
        )


def _service(
    *,
    summary: str | None,
    ai_manager: FakeAIManager | None = None,
) -> TranslationService:
    """Create a translation service fixture."""
    return TranslationService(
        pipeline=FakePipeline(summary),
        ai_manager=ai_manager or FakeAIManager(),
    )


def _album_context(*, artist: str, album: str, summary: str | None) -> AlbumContext:
    """Create an album context fixture."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist=artist,
            album=album,
            year=1965,
            summary=summary,
            genres=["Jazz"],
            styles=[],
            moods=[],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            genres=["jazz"],
            tags=[],
            confidence=95,
        ),
        wikipedia=WikipediaAlbumContext(
            language="en",
            title=album,
            extract="Wikipedia extract.",
            page_url="https://example.test",
        ),
        pipeline=PipelineContext(
            collected_sources=["plex"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )
