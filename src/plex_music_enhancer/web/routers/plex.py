"""Plex synchronization REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.errors import PlexAPIError
from plex_music_enhancer.api.models import PlexSyncStatusResponse
from plex_music_enhancer.plex.sync import PlexLibrarySyncService, PlexSyncError
from plex_music_enhancer.web.dependencies import get_plex_sync_service

router = APIRouter()


@router.post("/sync", response_model=PlexSyncStatusResponse)
async def start_sync(
    service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
) -> PlexSyncStatusResponse:
    """Start Plex library synchronization."""
    try:
        return service.start()
    except PlexSyncError as exc:
        raise PlexAPIError(str(exc)) from exc


@router.get("/sync/status", response_model=PlexSyncStatusResponse)
async def sync_status(
    service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
) -> PlexSyncStatusResponse:
    """Return current Plex library synchronization status."""
    return service.status()
