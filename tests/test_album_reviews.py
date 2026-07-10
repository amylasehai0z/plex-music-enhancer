"""Structured AI album review pipeline tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from plex_music_enhancer.ai.models import GeneratedSummary
from plex_music_enhancer.album_reviews import (
    AlbumReviewError,
    AlbumReviewPromptBuilder,
    AlbumReviewService,
    AlbumReviewStore,
)
from plex_music_enhancer.plex.sync import (
    PlexSyncSnapshot,
    PlexSyncStore,
    SyncedAlbum,
    SyncedLibrary,
    SyncedTrack,
)
from plex_music_enhancer.prompts.renderer import RenderedPrompt


def test_album_review_prompt_contains_required_album_context() -> None:
    """Prompt builder should expose the required structured album context."""
    prompt = AlbumReviewPromptBuilder().build(album=_album(), tracks=_tracks())

    assert "Artist:" in prompt.rendered_text
    assert "Nina Simone" in prompt.rendered_text
    assert "Album:" in prompt.rendered_text
    assert "Pastel Blues" in prompt.rendered_text
    assert "Erscheinungsjahr:" in prompt.rendered_text
    assert "Trackliste:" in prompt.rendered_text
    assert "recommendedFor" in prompt.rendered_text
    assert prompt.name == "album_review"


def test_album_review_generation_persists_structured_content(tmp_path: Path) -> None:
    """Service should parse AI JSON and persist structured reviews."""
    sync_store = _sync_store(tmp_path)
    review_store = AlbumReviewStore(tmp_path / "reviews.json")
    service = AlbumReviewService(
        sync_store=sync_store,
        review_store=review_store,
        ai_manager=FakeAIManager(_json_review_text()),
    )

    review = service.generate_now("200")

    assert review.album_id == "200"
    assert review.content.rating == 91
    assert review.content.strengths == ["Ausdruck", "Atmosphäre"]
    assert review.provider == "openai"

    restarted = AlbumReviewService(
        sync_store=sync_store,
        review_store=review_store,
        ai_manager=FakeAIManager(_json_review_text()),
    )
    assert restarted.get_review("200").content.final_verdict == "Ein starkes Vokalalbum."
    assert restarted.overview().generated_reviews == 1
    assert restarted.overview().average_rating == 91


def test_album_review_generation_requires_sync_snapshot(tmp_path: Path) -> None:
    """Service should fail clearly when Plex has not been synchronized."""
    service = AlbumReviewService(
        sync_store=PlexSyncStore(tmp_path / "missing-sync.json"),
        review_store=AlbumReviewStore(tmp_path / "reviews.json"),
        ai_manager=FakeAIManager(_json_review_text()),
    )

    with pytest.raises(AlbumReviewError, match="Run Plex synchronization"):
        service.generate_now("200")


def test_album_review_generation_rejects_invalid_ai_payload(tmp_path: Path) -> None:
    """Service should reject non-JSON provider responses."""
    service = AlbumReviewService(
        sync_store=_sync_store(tmp_path),
        review_store=AlbumReviewStore(tmp_path / "reviews.json"),
        ai_manager=FakeAIManager("not json"),
    )

    with pytest.raises(AlbumReviewError, match="non-JSON"):
        service.generate_now("200")


class FakeAIManager:
    """Fake AI manager returning static text."""

    def __init__(self, text: str) -> None:
        """Create a fake manager."""
        self.text = text
        self.prompts: list[RenderedPrompt] = []

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Return a fake generated response."""
        self.prompts.append(prompt)
        return GeneratedSummary(
            language="de",
            text=self.text,
            provider="openai",
            model="gpt-5.5",
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=0.9,
            source_count=1,
        )


def _sync_store(tmp_path: Path) -> PlexSyncStore:
    """Create a persisted fake sync store."""
    store = PlexSyncStore(tmp_path / "sync.json")
    store.save(
        PlexSyncSnapshot(
            synced_at=datetime(2026, 1, 1, tzinfo=UTC),
            libraries=[
                SyncedLibrary(
                    library_id="42",
                    title="Music",
                    uuid="music",
                    scanner="Plex Music",
                    agent="tv.plex.agents.music",
                )
            ],
            albums=[_album()],
            tracks=_tracks(),
        )
    )
    return store


def _album() -> SyncedAlbum:
    """Return a fake synchronized album."""
    return SyncedAlbum(
        rating_key="200",
        title="Pastel Blues",
        parent_artist="Nina Simone",
        guid="plex://album/200",
        year=1965,
        library_id="42",
        library_title="Music",
    )


def _tracks() -> list[SyncedTrack]:
    """Return fake synchronized tracks."""
    return [
        SyncedTrack(
            rating_key="301",
            title="Be My Husband",
            parent_artist="Nina Simone",
            parent_album="Pastel Blues",
            guid="plex://track/301",
            index=1,
            library_id="42",
            library_title="Music",
        ),
        SyncedTrack(
            rating_key="302",
            title="Nobody Knows You When You're Down and Out",
            parent_artist="Nina Simone",
            parent_album="Pastel Blues",
            guid="plex://track/302",
            index=2,
            library_id="42",
            library_title="Music",
        ),
    ]


def _json_review_text() -> str:
    """Return valid structured AI review JSON."""
    return """{
  "summary": "Eine konzentrierte Kritik.",
  "rating": 91,
  "genres": ["Blues", "Jazz"],
  "strengths": ["Ausdruck", "Atmosphäre"],
  "weaknesses": ["Knapp dokumentierte Produktionsdaten"],
  "recommendedFor": "Hörer klassischer Vokalalben.",
  "finalVerdict": "Ein starkes Vokalalbum."
}"""
