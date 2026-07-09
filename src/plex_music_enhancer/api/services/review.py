"""Internal review API service adapter."""

from __future__ import annotations

from dataclasses import dataclass

from plex_music_enhancer.api.errors import ReviewAPIError, ValidationAPIError
from plex_music_enhancer.api.models import (
    AlbumReviewRequest,
    AlbumReviewResponse,
    ArtistReviewRequest,
    ArtistReviewResponse,
    ReviewMode,
)
from plex_music_enhancer.api.services.mappers import review_document_to_api
from plex_music_enhancer.review import ReviewService, evaluate_review_policy


@dataclass(frozen=True)
class ReviewAPIService:
    """Frontend-neutral adapter around the existing ReviewService."""

    review_service: ReviewService

    def review(
        self,
        request: AlbumReviewRequest | ArtistReviewRequest,
    ) -> AlbumReviewResponse | ArtistReviewResponse:
        """Create a review response from a typed API request."""
        if isinstance(request, AlbumReviewRequest):
            return self.review_album(request)
        return self.review_artist(request)

    def review_album(self, request: AlbumReviewRequest) -> AlbumReviewResponse:
        """Create an album review response."""
        prompt_name = _prompt_name_for_mode(request.mode)
        try:
            document = (
                self.review_service.create_review(
                    artist=request.artist,
                    album=request.album,
                )
                if prompt_name == "album_summary"
                else self.review_service.create_review(
                    artist=request.artist,
                    album=request.album,
                    prompt_name=prompt_name,
                )
            )
        except Exception as exc:
            raise ReviewAPIError(str(exc) or "Unable to create album review.") from exc

        policy = evaluate_review_policy(document)
        return AlbumReviewResponse(
            document=review_document_to_api(document, target="album", mode=request.mode),
            apply_allowed=policy.apply_allowed,
            messages=policy.messages,
        )

    def review_artist(self, request: ArtistReviewRequest) -> ArtistReviewResponse:
        """Create an artist review response."""
        try:
            document = self.review_service.create_artist_review(artist=request.artist)
        except Exception as exc:
            raise ReviewAPIError(str(exc) or "Unable to create artist review.") from exc

        policy = evaluate_review_policy(document)
        return ArtistReviewResponse(
            document=review_document_to_api(document, target="artist", mode="create"),
            apply_allowed=policy.apply_allowed,
            messages=policy.messages,
        )


def _prompt_name_for_mode(mode: ReviewMode) -> str:
    """Return the album prompt template for one API review mode."""
    if mode == "create":
        return "album_summary"
    if mode == "translate":
        return "album_translate"
    if mode == "improve":
        return "album_improve"
    raise ValidationAPIError(f"Unsupported review mode: {mode}")
