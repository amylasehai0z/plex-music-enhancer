"""Statistics REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.models import StatisticsResponse
from plex_music_enhancer.cache.store import KnowledgeCacheStore
from plex_music_enhancer.plex.sync import PlexLibrarySyncService
from plex_music_enhancer.web.dependencies import get_plex_sync_service

router = APIRouter()


@router.get("", response_model=StatisticsResponse)
async def statistics(
    sync_service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
) -> StatisticsResponse:
    """Return aggregate statistics from the latest Plex synchronization."""
    sync_status = sync_service.status()
    cache_stats = KnowledgeCacheStore().stats()
    return StatisticsResponse(
        libraries=sync_status.libraries,
        artists=sync_status.artists,
        albums=sync_status.albums,
        tracks=sync_status.tracks,
        cache_entries=cache_stats.total_entries,
    )
