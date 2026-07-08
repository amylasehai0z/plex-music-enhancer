"""Interactive review workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from rich.console import Console

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.review import ReviewLimits, ReviewRenderer, ReviewService
from plex_music_enhancer.review.diff import unified_summary_diff
from plex_music_enhancer.review.service import validate_summary_quality
from plex_music_enhancer.services import EnrichmentPreviewDocument


def test_unified_summary_diff_marks_changes() -> None:
    """Unified diff should compare current and generated summary text."""
    diff = unified_summary_diff("Alte Zusammenfassung.", "Neue Zusammenfassung.")

    assert "--- current summary" in diff
    assert "+++ generated summary" in diff
    assert "-Alte Zusammenfassung." in diff
    assert "+Neue Zusammenfassung." in diff


def test_quality_validation_passes_good_german_summary() -> None:
    """Quality validation should pass clean German prose in range."""
    summary = _german_summary(words=95)

    report = validate_summary_quality(summary)

    assert report.status == "PASS"
    assert report.word_count == 95
    assert report.failures == []
    assert report.warnings == []
    assert all(report.checks.values())


def test_quality_validation_warns_for_short_summary() -> None:
    """Quality validation should warn when prose is valid but too short."""
    report = validate_summary_quality(
        "Das Album ist ein Jazzalbum mit verifizierbaren Angaben.",
        limits=ReviewLimits(minimum_words=10, maximum_words=120),
    )

    assert report.status == "WARNINGS"
    assert report.failures == []
    assert report.warnings
    assert report.checks["length_in_range"] is False


def test_quality_validation_rejects_empty_markdown_bullets_and_placeholders() -> None:
    """Quality validation should fail summaries that can never be applied."""
    empty = validate_summary_quality("")
    markdown = validate_summary_quality("## Titel\n\nDies ist ein placeholder Text.")
    bullet = validate_summary_quality("- Das Album ist ein Jazzalbum.")

    assert empty.status == "FAILED"
    assert "Summary is empty." in empty.failures
    assert markdown.status == "FAILED"
    assert "Summary contains Markdown formatting." in markdown.failures
    assert "Summary contains placeholder text." in markdown.failures
    assert bullet.status == "FAILED"
    assert "Summary contains bullet lists." in bullet.failures


def test_review_service_creates_and_edits_review_document() -> None:
    """ReviewService should build review documents and revalidate edits."""
    service = ReviewService(
        preview_service=FakePreviewService(_preview_document(_german_summary(words=95)))
    )

    document = service.create_review(artist="Nina Simone", album="Pastel Blues")
    edited = service.update_summary(document, _german_summary(words=90))

    assert document.current_summary == "Aktuelle Plex-Zusammenfassung."
    assert document.quality.status == "PASS"
    assert edited.edited is True
    assert edited.quality.status == "PASS"
    assert edited.proposed_summary != document.proposed_summary
    assert "+Das Album ist" in edited.diff


def test_review_service_rejects_generated_placeholder_summary() -> None:
    """ReviewService should mark placeholder output as failed."""
    service = ReviewService(preview_service=FakePreviewService(_preview_document("placeholder")))

    document = service.create_review(artist="Nina Simone", album="Pastel Blues")

    assert document.quality.status == "FAILED"
    assert "Summary contains placeholder text." in document.quality.failures


def test_review_renderer_outputs_required_sections() -> None:
    """ReviewRenderer should display summary, diff, and quality sections."""
    service = ReviewService(
        preview_service=FakePreviewService(_preview_document(_german_summary(words=95)))
    )
    document = service.create_review(artist="Nina Simone", album="Pastel Blues")
    console = Console(record=True, width=120)

    ReviewRenderer(console).render(document)

    output = console.export_text()
    assert "CURRENT SUMMARY" in output
    assert "GENERATED SUMMARY" in output
    assert "UNIFIED DIFF" in output
    assert "QUALITY" in output
    assert "PASS" in output


class FakePreviewService:
    """Fake preview service for review tests."""

    def __init__(self, document: EnrichmentPreviewDocument) -> None:
        """Create a fake preview service."""
        self._document = document

    def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
        """Return fake preview output."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return self._document


class _FrozenModel(BaseModel):
    """Base frozen model for fixtures."""

    model_config = ConfigDict(frozen=True)


def _preview_document(summary: str) -> EnrichmentPreviewDocument:
    """Return preview document fixture."""
    return EnrichmentPreviewDocument(
        context=_album_context(),
        rendered_prompt=RenderedPrompt(
            name="album_summary",
            version="1.0",
            rendered_text="Prompt",
            variables={"artist": "Nina Simone", "album": "Pastel Blues", "language": "de"},
            template="Template",
        ),
        generated_summary=GeneratedSummary(
            language="de",
            text=summary,
            provider="openai",
            model="gpt-5.5",
            prompt_name="album_summary",
            prompt_version="1.0",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=0.9,
            source_count=3,
            metadata={"prompt_tokens": 100, "completion_tokens": 40},
        ),
        generation_time_seconds=0.25,
    )


def _album_context() -> AlbumContext:
    """Return album context fixture."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Aktuelle Plex-Zusammenfassung.",
            genres=["Jazz", "Soul"],
            styles=[],
            moods=[],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            genres=["jazz"],
            tags=["blues"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(
            language="de",
            title="Pastel Blues",
            extract="Wikipedia summary",
            page_url="https://de.wikipedia.org/wiki/Pastel_Blues",
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )


def _german_summary(*, words: int) -> str:
    """Return deterministic German prose with a requested word count."""
    base_words = [
        "Das",
        "Album",
        "ist",
        "eine",
        "sachliche",
        "Sammlung",
        "verifizierbarer",
        "Angaben",
        "und",
        "beschreibt",
        "die",
        "musikalische",
        "Einordnung",
        "mit",
        "ruhigem",
        "Ton",
        "und",
        "neutraler",
        "Sprache",
    ]
    repeated = [base_words[index % len(base_words)] for index in range(words)]
    return " ".join(repeated) + "."
