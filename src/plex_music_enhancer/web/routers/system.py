"""System REST endpoints."""

from __future__ import annotations

from importlib.metadata import version

from fastapi import APIRouter

from plex_music_enhancer.api.models import API_VERSION

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return service health."""
    return {"status": "ok", "apiVersion": API_VERSION}


@router.get("/version")
async def api_version() -> dict[str, str]:
    """Return application and API version information."""
    return {
        "name": "plex-music-enhancer",
        "version": version("plex-music-enhancer"),
        "apiVersion": API_VERSION,
    }
