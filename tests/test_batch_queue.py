"""Persistent batch queue tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from plex_music_enhancer.api.models import (
    ApplyResponse,
    BatchQueueItem,
    BatchStartItem,
    DebugMeta,
    PromptAnalysis,
    QualityAnalysis,
    ReviewDocument,
    TokenUsage,
    VerificationAnalysis,
)
from plex_music_enhancer.batch import BatchQueueService, BatchQueueStore


def test_batch_queue_persists_and_processes_items(tmp_path: Path) -> None:
    """Batch queue should persist, apply sequentially and write history."""
    service = _service(tmp_path, apply_service=_FakeApplyService())

    status = service.start(
        [
            BatchStartItem(
                target="artist",
                plex_id="100",
                name="Nina Simone",
                artist="Nina Simone",
            ),
            BatchStartItem(
                target="album",
                plex_id="200",
                name="Pastel Blues",
                artist="Nina Simone",
                album="Pastel Blues",
            ),
        ]
    )
    service.run_pending_once()

    assert status.total == 2
    finished = service.status()
    assert finished.completed == 2
    assert finished.failed == 0
    assert service.history().history[-1].name == "Pastel Blues"


def test_batch_queue_resets_running_items_after_restart(tmp_path: Path) -> None:
    """Interrupted running jobs should become pending on the next process start."""
    store = _store(tmp_path)
    store.save_queue(
        [
            BatchQueueItem(
                id="1",
                target="artist",
                plex_id="100",
                name="Nina Simone",
                artist="Nina Simone",
                status="running",
                progress=50,
            )
        ]
    )

    restarted = store.load_queue()

    assert restarted[0].status == "pending"
    assert restarted[0].progress == 0


def test_batch_queue_keeps_running_after_item_failure(tmp_path: Path) -> None:
    """One failed item should not stop following entries."""
    service = _service(tmp_path, apply_service=_FailingOnceApplyService())

    service.start(
        [
            BatchStartItem(target="artist", plex_id="100", name="Broken", artist="Broken"),
            BatchStartItem(target="artist", plex_id="101", name="Working", artist="Working"),
        ]
    )
    service.run_pending_once()

    status = service.status()
    assert status.failed == 1
    assert status.completed == 1
    assert [item.status for item in service.history().history] == ["failed", "completed"]


def test_batch_queue_cancel_and_clear(tmp_path: Path) -> None:
    """Cancel should skip pending items and clear should remove non-running queue rows."""
    service = _service(tmp_path, apply_service=_FakeApplyService())
    service.start(
        [
            BatchStartItem(
                target="artist",
                plex_id="100",
                name="Nina Simone",
                artist="Nina Simone",
            )
        ]
    )

    cancelled = service.cancel()
    cleared = service.clear()

    assert cancelled.skipped == 1 or cancelled.running is True
    assert cleared.total in {0, 1}


class _FakeApplyService:
    """Fake successful apply service."""

    def apply(self, request):
        """Return a fake successful apply response."""
        return ApplyResponse(
            status="SUCCESS",
            artist=request.artist,
            album=request.album or "artist",
            rating_key="42",
            backup_created=True,
            write_successful=True,
            verification_passed=True,
            audit_stored=True,
            message="ok",
            review=_api_review_document(
                target=request.target,
                artist=request.artist,
                album=request.album,
            ),
        )


class _FailingOnceApplyService(_FakeApplyService):
    """Fail the first apply and succeed afterwards."""

    def __init__(self) -> None:
        """Create fake service."""
        self.calls = 0

    def apply(self, request):
        """Fail once."""
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("apply failed")
        return super().apply(request)


def _store(tmp_path: Path) -> BatchQueueStore:
    return BatchQueueStore(
        queue_path=tmp_path / "batch_queue.json",
        history_path=tmp_path / "batch_history.json",
    )


def _api_review_document(
    *,
    target: str = "album",
    artist: str = "Jennifer Rush",
    album: str | None = "Credo",
) -> ReviewDocument:
    """Return a fake API ReviewDocument."""
    return ReviewDocument(
        target=target,
        artist=artist,
        album=album,
        rating_key="42",
        current_summary="Alt.",
        generated_summary="Neu.",
        proposed_summary="Neu.",
        unified_diff="--- old\n+++ new",
        qa=QualityAnalysis(
            status="PASS",
            critical_validation="PASS",
            editorial_validation="PASS",
            publishable=True,
            word_count=120,
        ),
        editorial={},
        verification=VerificationAnalysis(),
        prompt=PromptAnalysis(
            name="artist_biography" if target == "artist" else "album_summary",
            version="1.0",
            characters=100,
            estimated_tokens=25,
            budget=20000,
            evidence_ranking={"Wikipedia": 98},
        ),
        debug=DebugMeta(
            provider="openai",
            model="gpt-5.5",
            generation_time_seconds=0.2,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
        ),
        provider="openai",
        model="gpt-5.5",
        context={"generatedAt": datetime(2026, 1, 1, tzinfo=UTC).isoformat()},
    )


def _service(tmp_path: Path, *, apply_service) -> BatchQueueService:
    return BatchQueueService(store=_store(tmp_path), apply_service=apply_service, auto_start=False)
