"""Album REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.models import LibraryAlbum
from plex_music_enhancer.plex.sync import PlexLibrarySyncService
from plex_music_enhancer.web.dependencies import get_plex_sync_service

router = APIRouter()


@router.get("", response_model=list[LibraryAlbum])
async def list_albums(
    sync_service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
) -> list[LibraryAlbum]:
    """Return synchronized Plex album entries for library views."""
    snapshot = sync_service.snapshot()
    if snapshot is None:
        return []
    return [
        LibraryAlbum(
            rating_key=album.rating_key,
            title=album.title,
            artist=album.parent_artist or "Unbekannter Interpret",
            library=album.library_title,
            year=album.year,
            summary_present=False,
        )
        for album in snapshot.albums
    ]
