"""Review REST endpoints."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends

from plex_music_enhancer.api.models import (
    AlbumReviewRequest,
    AlbumReviewResponse,
    ArtistReviewRequest,
    ArtistReviewResponse,
)
from plex_music_enhancer.api.services import ReviewAPIService
from plex_music_enhancer.web.dependencies import get_review_api_service

router = APIRouter()


@router.post("/artist", response_model=ArtistReviewResponse)
async def review_artist(
    request: ArtistReviewRequest,
    service: Annotated[ReviewAPIService, Depends(get_review_api_service)],
) -> ArtistReviewResponse:
    """Create an artist review document."""
    response = service.review(request)
    return cast(ArtistReviewResponse, response)


@router.post("/album", response_model=AlbumReviewResponse)
async def review_album(
    request: AlbumReviewRequest,
    service: Annotated[ReviewAPIService, Depends(get_review_api_service)],
) -> AlbumReviewResponse:
    """Create an album review document."""
    response = service.review(request)
    return cast(AlbumReviewResponse, response)
