"""Apply REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.models import ApplyRequest, ApplyResponse
from plex_music_enhancer.api.services import ApplyAPIService
from plex_music_enhancer.web.dependencies import get_apply_api_service

router = APIRouter()


@router.post("", response_model=ApplyResponse)
async def apply_metadata(
    request: ApplyRequest,
    service: Annotated[ApplyAPIService, Depends(get_apply_api_service)],
) -> ApplyResponse:
    """Apply approved generated metadata."""
    return service.apply(request)
