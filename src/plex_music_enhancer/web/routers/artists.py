"""Artist REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from plex_music_enhancer.api.models import LibraryArtist

router = APIRouter()


@router.get("", response_model=list[LibraryArtist])
async def list_artists() -> list[LibraryArtist]:
    """Return artist entries for future library views."""
    return []
