"""Structured album review REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plex_music_enhancer.album_reviews import AlbumReviewError, AlbumReviewService
from plex_music_enhancer.api.errors import ReviewAPIError
from plex_music_enhancer.api.models import (
    AlbumReviewGenerationResponse,
    AlbumReviewOverviewResponse,
    StoredAlbumReview,
)
from plex_music_enhancer.web.dependencies import get_album_review_service

router = APIRouter()


@router.post("/generate/{album_id}", response_model=AlbumReviewGenerationResponse)
async def generate_album_review(
    album_id: str,
    service: Annotated[AlbumReviewService, Depends(get_album_review_service)],
) -> AlbumReviewGenerationResponse:
    """Start structured AI review generation for a synchronized album."""
    try:
        return service.start_generation(album_id)
    except AlbumReviewError as exc:
        raise ReviewAPIError(str(exc) or "Album review generation failed.") from exc


@router.get("/{album_id}", response_model=StoredAlbumReview)
async def get_album_review(
    album_id: str,
    service: Annotated[AlbumReviewService, Depends(get_album_review_service)],
) -> StoredAlbumReview:
    """Return a stored structured album review."""
    try:
        return service.get_review(album_id)
    except AlbumReviewError as exc:
        raise ReviewAPIError(str(exc) or "Album review is not available.") from exc


@router.get("", response_model=AlbumReviewOverviewResponse)
async def list_album_reviews(
    service: Annotated[AlbumReviewService, Depends(get_album_review_service)],
) -> AlbumReviewOverviewResponse:
    """Return synchronized albums with structured review status."""
    try:
        return service.overview()
    except AlbumReviewError as exc:
        raise ReviewAPIError(str(exc) or "Album review overview is not available.") from exc
