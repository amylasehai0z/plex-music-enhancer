"""Statistics REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from plex_music_enhancer.api.models import StatisticsResponse

router = APIRouter()


@router.get("", response_model=StatisticsResponse)
async def statistics() -> StatisticsResponse:
    """Return placeholder aggregate statistics for future dashboards."""
    return StatisticsResponse()
