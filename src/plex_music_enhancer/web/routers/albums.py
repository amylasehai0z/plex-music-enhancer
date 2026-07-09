"""Album REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from plex_music_enhancer.api.models import LibraryAlbum

router = APIRouter()


@router.get("", response_model=list[LibraryAlbum])
async def list_albums() -> list[LibraryAlbum]:
    """Return album entries for future library views."""
    return []
