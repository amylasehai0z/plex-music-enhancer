"""Internal backend API preparation tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from plex_music_enhancer.ai.models import GeneratedSummary
from plex_music_enhancer.api.errors import ConfigurationAPIError, ReviewAPIError
from plex_music_enhancer.api.models import API_VERSION, AlbumReviewRequest, PromptAnalysis
from plex_music_enhancer.api.services import ReviewAPIService, review_document_to_api
from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.quality import QualityLevel
from plex_music_enhancer.quality import QualityReport as QAReport
from plex_music_enhancer.review import QualityReport, ReviewDocument
from plex_music_enhancer.services import EnrichmentPreviewDocument


def test_api_error_hierarchy_returns_problem_payload() -> None:
    """API errors should expose stable future HTTP problem payloads."""
    error = ConfigurationAPIError("Missing Plex URL.", details={"field": "plex_url"})

    payload = error.to_problem()

    assert payload["code"] == "configuration_error"
    assert payload["message"] == "Missing Plex URL."
    assert payload["statusCode"] == 400
    assert payload["details"] == {"field": "plex_url"}


def test_api_prompt_analysis_uses_stable_json_aliases() -> None:
    """API models should serialize with stable OpenAPI-friendly field names."""
    analysis = PromptAnalysis(
        name="artist_biography",
        version="1.0",
        characters=1200,
        estimated_tokens=300,
        budget=20000,
        trimmed=False,
        evidence_ranking={"Wikipedia": 98},
    )

    exported = analysis.model_dump(by_alias=True)

    assert exported["estimatedTokens"] == 300
    assert exported["evidenceRanking"] == {"Wikipedia": 98}


def test_review_document_mapper_returns_central_api_document() -> None:
    """Domain review documents should map to the stable API ReviewDocument."""
    document = _review_document()

    api_document = review_document_to_api(document, target="album", mode="create")
    exported = api_document.model_dump(by_alias=True)

    assert exported["apiVersion"] == API_VERSION
    assert exported["target"] == "album"
    assert exported["artist"] == "Nina Simone"
    assert exported["album"] == "Pastel Blues"
    assert exported["ratingKey"] == "42"
    assert exported["currentSummary"] == "Aktuelle Plex-Zusammenfassung."
    assert exported["generatedSummary"] == document.preview.generated_summary.text
    assert exported["unifiedDiff"] == document.diff
    assert exported["prompt"]["budgetDiagnostics"]["evidence_ranking"] == {"Wikipedia": 98}
    assert exported["debug"]["tokenUsage"]["promptTokens"] == 100


def test_review_api_service_accepts_album_review_request() -> None:
    """ReviewAPIService should expose a unified request/response boundary."""
    domain_document = _review_document()
    service = ReviewAPIService(_FakeReviewService(domain_document))

    response = service.review(AlbumReviewRequest(artist="Nina Simone", album="Pastel Blues"))

    assert response.document.artist == "Nina Simone"
    assert response.document.album == "Pastel Blues"
    assert response.document.provider == "openai"
    assert response.apply_allowed is True


def test_review_api_service_wraps_review_failures() -> None:
    """ReviewAPIService should map service failures to API errors."""
    service = ReviewAPIService(_FailingReviewService())

    with pytest.raises(ReviewAPIError, match="boom"):
        service.review(AlbumReviewRequest(artist="Nina Simone", album="Pastel Blues"))


class _FakeReviewService:
    """Minimal fake review service."""

    def __init__(self, document: ReviewDocument) -> None:
        self._document = document

    def create_review(self, *, artist: str, album: str, prompt_name: str | None = None):
        """Return a prepared review document."""
        return self._document


class _FailingReviewService:
    """Fake service that fails."""

    def create_review(self, *, artist: str, album: str, prompt_name: str | None = None):
        """Raise an error."""
        raise RuntimeError("boom")


def _review_document() -> ReviewDocument:
    """Return a complete domain review document fixture."""
    summary = "Nina Simone war eine prägende amerikanische Sängerin mit besonderem Ausdruck."
    return ReviewDocument(
        preview=EnrichmentPreviewDocument(
            context=AlbumContext(
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
                ),
                wikipedia=WikipediaAlbumContext(),
                pipeline=PipelineContext(
                    collected_sources=["plex", "musicbrainz"],
                    missing_fields=[],
                    warnings=[],
                    ready_for_generation=True,
                ),
            ),
            rendered_prompt=RenderedPrompt(
                name="album_summary",
                version="1.0",
                rendered_text="Prompt",
                variables={"artist": "Nina Simone", "album": "Pastel Blues"},
                template="Template",
                budget_diagnostics={
                    "max_characters": 20000,
                    "trimmed": False,
                    "prompt_quality": {"prompt_efficiency": 91},
                    "prompt_decisions": {"included": ["Wikipedia"], "removed": []},
                    "evidence_ranking": {"Wikipedia": 98},
                },
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
            qa_report=QAReport(
                overall_score=91,
                quality_level=QualityLevel.VERY_GOOD,
            ),
        ),
        current_summary="Aktuelle Plex-Zusammenfassung.",
        proposed_summary=summary,
        diff="--- current\n+++ generated",
        quality=QualityReport(
            status="PASS",
            critical_validation="PASS",
            editorial_validation="PASS",
            publishable=True,
            checks={"not_empty": True},
            word_count=len(summary.split()),
        ),
    )
