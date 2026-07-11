"""Batch review/apply REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.errors import ReviewAPIError, ValidationAPIError
from plex_music_enhancer.api.models import (
    BatchHistoryResponse,
    BatchStartRequest,
    BatchStatusResponse,
)
from plex_music_enhancer.batch import BatchQueueError, BatchQueueService
from plex_music_enhancer.web.dependencies import get_batch_queue_service

router = APIRouter()


@router.post("/start", response_model=BatchStatusResponse)
async def start_batch(
    request: BatchStartRequest,
    service: Annotated[BatchQueueService, Depends(get_batch_queue_service)],
) -> BatchStatusResponse:
    """Start a sequential batch review/apply queue."""
    try:
        return service.start(request.items)
    except BatchQueueError as exc:
        raise ValidationAPIError(str(exc) or "Batch start request is invalid.") from exc
    except Exception as exc:
        raise ReviewAPIError(str(exc) or "Unable to start batch queue.") from exc


@router.post("/cancel", response_model=BatchStatusResponse)
async def cancel_batch(
    service: Annotated[BatchQueueService, Depends(get_batch_queue_service)],
) -> BatchStatusResponse:
    """Cancel pending batch queue items."""
    return service.cancel()


@router.post("/clear", response_model=BatchStatusResponse)
async def clear_batch(
    service: Annotated[BatchQueueService, Depends(get_batch_queue_service)],
) -> BatchStatusResponse:
    """Clear non-running batch queue items."""
    return service.clear()


@router.get("/status", response_model=BatchStatusResponse)
async def batch_status(
    service: Annotated[BatchQueueService, Depends(get_batch_queue_service)],
) -> BatchStatusResponse:
    """Return current batch queue status."""
    return service.status()


@router.get("/history", response_model=BatchHistoryResponse)
async def batch_history(
    service: Annotated[BatchQueueService, Depends(get_batch_queue_service)],
) -> BatchHistoryResponse:
    """Return recent batch history."""
    return service.history()
