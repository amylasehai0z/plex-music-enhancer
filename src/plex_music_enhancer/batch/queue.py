"""Persistent sequential batch review/apply queue."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock, Thread
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.api.models import (
    ApplyRequest,
    BatchHistoryResponse,
    BatchQueueItem,
    BatchStartItem,
    BatchStatusResponse,
)
from plex_music_enhancer.runtime_paths import runtime_config_dir
from plex_music_enhancer.utils.files import write_text_atomic

logger = logging.getLogger(__name__)


class BatchQueueError(Exception):
    """Raised when a batch request cannot be processed."""


class _ApplyService(Protocol):
    """Minimal apply API used by the batch queue."""

    def apply(self, request: ApplyRequest):
        """Apply one review request."""


class _BatchStorePayload(BaseModel):
    """Persistent queue payload."""

    model_config = ConfigDict(frozen=True)

    items: list[BatchQueueItem] = Field(default_factory=list)


class BatchQueueStore:
    """JSON persistence for batch queue and history."""

    def __init__(self, *, queue_path: Path, history_path: Path) -> None:
        """Create a store."""
        self.queue_path = queue_path
        self.history_path = history_path

    @classmethod
    def default(cls) -> BatchQueueStore:
        """Return the default store below the persistent config volume."""
        cache_dir = runtime_config_dir() / "cache"
        return cls(
            queue_path=cache_dir / "batch_queue.json",
            history_path=cache_dir / "batch_history.json",
        )

    def load_queue(self) -> list[BatchQueueItem]:
        """Return queued items, resetting interrupted running jobs to pending."""
        items = self._load(self.queue_path)
        reset_items = [
            (
                item.model_copy(update={"status": "pending", "progress": 0, "started_at": None})
                if item.status == "running"
                else item
            )
            for item in items
        ]
        if reset_items != items:
            self.save_queue(reset_items)
        return reset_items

    def save_queue(self, items: list[BatchQueueItem]) -> None:
        """Persist queue items."""
        self._save(self.queue_path, items)

    def load_history(self) -> list[BatchQueueItem]:
        """Return historical batch items."""
        return self._load(self.history_path)

    def append_history(self, item: BatchQueueItem) -> None:
        """Append one finished item to history."""
        history = self.load_history()
        history.append(item)
        self._save(self.history_path, history[-500:])

    def _load(self, path: Path) -> list[BatchQueueItem]:
        if not path.exists():
            return []
        try:
            payload = _BatchStorePayload.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return list(payload.items)

    def _save(self, path: Path, items: list[BatchQueueItem]) -> None:
        payload = _BatchStorePayload(items=items)
        write_text_atomic(path, payload.model_dump_json(indent=2, by_alias=True))


class BatchQueueService:
    """Run review/apply work sequentially for selected artists and albums."""

    def __init__(
        self,
        *,
        store: BatchQueueStore | None = None,
        apply_service: _ApplyService | None = None,
        auto_start: bool = True,
    ) -> None:
        """Create a batch queue service."""
        self._store = store or BatchQueueStore.default()
        self._apply_service = apply_service
        self._auto_start = auto_start
        self._lock = Lock()
        self._running = False
        self._cancel_requested = False
        if self._auto_start and any(item.status == "pending" for item in self._store.load_queue()):
            with self._lock:
                self._ensure_worker_locked()

    def start(self, items: list[BatchStartItem]) -> BatchStatusResponse:
        """Append items to the queue and start processing."""
        if not items:
            raise BatchQueueError("Batch start requires at least one artist or album.")

        queued = [self._queue_item(item) for item in items]
        with self._lock:
            queue = self._store.load_queue()
            queue.extend(queued)
            self._store.save_queue(queue)
            self._cancel_requested = False
            if self._auto_start:
                self._ensure_worker_locked()
        return self.status(message=f"{len(queued)} Einträge wurden zur Batch-Queue hinzugefügt.")

    def cancel(self) -> BatchStatusResponse:
        """Cancel pending items and let a running item finish safely."""
        with self._lock:
            self._cancel_requested = True
            queue = [
                (
                    item.model_copy(update={"status": "skipped", "progress": 0})
                    if item.status == "pending"
                    else item
                )
                for item in self._store.load_queue()
            ]
            self._store.save_queue(queue)
        return self.status(message="Batch-Abbruch wurde angefordert.")

    def clear(self) -> BatchStatusResponse:
        """Clear finished and pending queue items while preserving active work."""
        with self._lock:
            queue = [item for item in self._store.load_queue() if item.status == "running"]
            self._store.save_queue(queue)
        return self.status(message="Batch-Queue wurde geleert.")

    def status(self, *, message: str | None = None) -> BatchStatusResponse:
        """Return current queue status."""
        with self._lock:
            queue = self._store.load_queue()
            running = self._running or any(item.status == "running" for item in queue)
            cancelled = self._cancel_requested
        return _status_from_queue(queue, running=running, cancelled=cancelled, message=message)

    def history(self) -> BatchHistoryResponse:
        """Return completed batch history."""
        return BatchHistoryResponse(history=self._store.load_history())

    def run_pending_once(self) -> None:
        """Process queued entries synchronously for tests and controlled callers."""
        with self._lock:
            self._running = True
        try:
            self._process_queue()
        finally:
            with self._lock:
                self._running = False

    def _ensure_worker_locked(self) -> None:
        """Start a background worker when no worker is active."""
        if self._running:
            return
        self._running = True
        thread = Thread(target=self._run_worker, name="batch-review-queue", daemon=True)
        thread.start()

    def _run_worker(self) -> None:
        try:
            self._process_queue()
        finally:
            with self._lock:
                self._running = False

    def _process_queue(self) -> None:
        while True:
            with self._lock:
                queue = self._store.load_queue()
                pending_index = next(
                    (index for index, item in enumerate(queue) if item.status == "pending"),
                    None,
                )
                if pending_index is None or self._cancel_requested:
                    return
                item = queue[pending_index].model_copy(
                    update={
                        "status": "running",
                        "progress": 10,
                        "started_at": datetime.now(UTC),
                        "error": None,
                    }
                )
                queue[pending_index] = item
                self._store.save_queue(queue)

            finished = self._process_item(item)
            with self._lock:
                queue = [
                    finished if current.id == finished.id else current
                    for current in self._store.load_queue()
                ]
                self._store.save_queue(queue)
                self._store.append_history(finished)

    def _process_item(self, item: BatchQueueItem) -> BatchQueueItem:
        logger.info(
            "Batch item started target=%s plex_id=%s name=%s",
            item.target,
            item.plex_id,
            item.name,
        )
        started_at = item.started_at or datetime.now(UTC)
        try:
            logger.info(
                "Batch step Generate Review target=%s plex_id=%s",
                item.target,
                item.plex_id,
            )
            logger.info("Batch step Backup target=%s plex_id=%s", item.target, item.plex_id)
            logger.info("Batch step Apply target=%s plex_id=%s", item.target, item.plex_id)
            result = self._configured_apply_service().apply(_apply_request(item))
            logger.info("Batch step Verify target=%s plex_id=%s", item.target, item.plex_id)
            ended_at = datetime.now(UTC)
            logger.info("Batch item completed target=%s plex_id=%s", item.target, item.plex_id)
            return item.model_copy(
                update={
                    "status": "completed",
                    "progress": 100,
                    "ended_at": ended_at,
                    "runtime_seconds": (ended_at - started_at).total_seconds(),
                    "error": None,
                    "review_id": result.rating_key,
                }
            )
        except Exception as exc:  # noqa: BLE001 - one batch failure must not stop the queue.
            ended_at = datetime.now(UTC)
            message = str(exc) or exc.__class__.__name__
            logger.warning(
                "Batch item failed target=%s plex_id=%s error=%s",
                item.target,
                item.plex_id,
                message,
            )
            return item.model_copy(
                update={
                    "status": "failed",
                    "progress": 100,
                    "ended_at": ended_at,
                    "runtime_seconds": (ended_at - started_at).total_seconds(),
                    "error": message,
                }
            )

    def _configured_apply_service(self) -> _ApplyService:
        if self._apply_service is None:
            from plex_music_enhancer.web.dependencies import get_apply_api_service

            self._apply_service = get_apply_api_service()
        return self._apply_service

    def _queue_item(self, item: BatchStartItem) -> BatchQueueItem:
        artist = item.artist or (item.name if item.target == "artist" else None)
        album = item.album or (item.name if item.target == "album" else None)
        if item.target == "album" and not artist:
            raise BatchQueueError(f"Album batch item {item.name!r} requires an artist.")
        return BatchQueueItem(
            id=str(uuid4()),
            target=item.target,
            plex_id=item.plex_id,
            name=item.name,
            artist=artist,
            album=album,
        )


def _apply_request(item: BatchQueueItem) -> ApplyRequest:
    return ApplyRequest(
        target=item.target,
        artist=item.artist or item.name,
        album=item.album if item.target == "album" else None,
    )


def _status_from_queue(
    queue: list[BatchQueueItem],
    *,
    running: bool,
    cancelled: bool,
    message: str | None,
) -> BatchStatusResponse:
    total = len(queue)
    completed = sum(1 for item in queue if item.status == "completed")
    failed = sum(1 for item in queue if item.status == "failed")
    skipped = sum(1 for item in queue if item.status == "skipped")
    pending = sum(1 for item in queue if item.status == "pending")
    active = next((item for item in queue if item.status == "running"), None)
    done = completed + failed + skipped
    progress = int((done / total) * 100) if total else 0
    if active is not None and total:
        progress = max(progress, int(((done + (active.progress / 100)) / total) * 100))
    durations = [
        item.runtime_seconds
        for item in queue
        if item.runtime_seconds is not None and item.status in {"completed", "failed", "skipped"}
    ]
    remaining = None
    if durations and pending:
        remaining = (sum(durations) / len(durations)) * pending
    return BatchStatusResponse(
        running=running,
        cancelled=cancelled,
        progress=progress,
        active=active,
        queue=queue,
        pending=pending,
        completed=completed,
        failed=failed,
        skipped=skipped,
        total=total,
        estimated_remaining_seconds=remaining,
        message=message,
    )


__all__ = ["BatchQueueError", "BatchQueueService", "BatchQueueStore"]
