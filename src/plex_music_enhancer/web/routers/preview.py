"""Preview REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.errors import ValidationAPIError
from plex_music_enhancer.api.models import (
    AlbumReviewRequest,
    ArtistReviewRequest,
    PreviewRequest,
    PreviewResponse,
)
from plex_music_enhancer.api.services import ReviewAPIService
from plex_music_enhancer.web.dependencies import get_review_api_service

router = APIRouter()


@router.post("", response_model=PreviewResponse)
async def preview(
    request: PreviewRequest,
    service: Annotated[ReviewAPIService, Depends(get_review_api_service)],
) -> PreviewResponse:
    """Create a read-only preview document."""
    if request.target == "artist":
        response = service.review(
            ArtistReviewRequest(
                artist=request.artist,
                provider=request.provider,
                model=request.model,
            )
        )
        return PreviewResponse(document=response.document)

    if request.album is None:
        raise ValidationAPIError("Album preview requests require an album title.")

    response = service.review(
        AlbumReviewRequest(
            artist=request.artist,
            album=request.album,
            provider=request.provider,
            model=request.model,
            mode=request.mode,
        )
    )
    return PreviewResponse(document=response.document)
