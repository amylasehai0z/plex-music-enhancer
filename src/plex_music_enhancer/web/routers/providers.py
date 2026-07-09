"""Provider REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from plex_music_enhancer.api.models import ProviderInfo
from plex_music_enhancer.config import Settings

router = APIRouter()


@router.get("", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    """Return configured provider information."""
    settings = Settings()
    return [
        ProviderInfo(
            name=settings.ai.provider,
            configured=settings.ai.provider == "dummy" or settings.ai.api_key is not None,
            model=settings.ai.model,
            details={"type": "ai"},
        ),
        ProviderInfo(
            name="discogs",
            configured=settings.discogs.token is not None,
            details={"type": "metadata"},
        ),
        ProviderInfo(
            name="lastfm",
            configured=settings.lastfm.api_key is not None,
            details={"type": "metadata"},
        ),
        ProviderInfo(name="musicbrainz", configured=True, details={"type": "metadata"}),
        ProviderInfo(name="wikipedia", configured=True, details={"type": "metadata"}),
    ]
