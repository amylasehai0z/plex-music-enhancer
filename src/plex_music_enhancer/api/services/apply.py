"""Internal apply API service adapter."""

from __future__ import annotations

from dataclasses import dataclass

from plex_music_enhancer.api.errors import ReviewAPIError, ValidationAPIError
from plex_music_enhancer.api.models import ApplyRequest, ApplyResponse
from plex_music_enhancer.api.services.mappers import review_document_to_api
from plex_music_enhancer.apply import ApplyService


@dataclass(frozen=True)
class ApplyAPIService:
    """Frontend-neutral adapter around the existing ApplyService."""

    apply_service: ApplyService

    def apply(self, request: ApplyRequest) -> ApplyResponse:
        """Apply generated metadata through a typed API request."""
        try:
            if request.target == "artist":
                result = self.apply_service.apply_artist_summary(artist=request.artist)
            elif request.album is not None:
                result = self.apply_service.apply_album_summary(
                    artist=request.artist,
                    album=request.album,
                    prompt_name=_prompt_name_for_mode(request.mode),
                )
            else:
                raise ValidationAPIError("Album apply requests require an album title.")
        except ValidationAPIError:
            raise
        except Exception as exc:
            raise ReviewAPIError(str(exc) or "Unable to apply generated metadata.") from exc

        return ApplyResponse(
            status=result.status,
            artist=result.artist,
            album=result.album,
            rating_key=result.rating_key,
            backup_created=result.backup_created,
            write_successful=result.write_successful,
            verification_passed=result.verification_passed,
            audit_stored=result.audit_stored,
            message=result.message,
            review=review_document_to_api(
                result.review,
                target=request.target,
                mode=request.mode,
            ),
        )


def _prompt_name_for_mode(mode: str) -> str:
    """Return an album prompt template for one apply mode."""
    if mode == "create":
        return "album_summary"
    if mode == "translate":
        return "album_translate"
    if mode == "improve":
        return "album_improve"
    raise ValidationAPIError(f"Unsupported apply mode: {mode}")
