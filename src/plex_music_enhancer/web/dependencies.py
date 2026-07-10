"""FastAPI dependency factories."""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr

from plex_music_enhancer.ai import AIError, AIManager
from plex_music_enhancer.api.errors import ConfigurationAPIError, ProviderAPIError
from plex_music_enhancer.api.services import (
    ApplyAPIService,
    ConfigurationAPIService,
    ReviewAPIService,
)
from plex_music_enhancer.apply import ApplyService
from plex_music_enhancer.config import Settings
from plex_music_enhancer.plex.sync import PlexLibrarySyncService
from plex_music_enhancer.review import ReviewService
from plex_music_enhancer.services import ConfigurationService, EnrichmentPreviewService


def get_settings() -> Settings:
    """Return application settings."""
    return Settings()


def require_plex_settings(settings: Settings | None = None) -> tuple[str, SecretStr]:
    """Return configured Plex connection settings or raise an API error."""
    selected = settings or get_settings()
    if selected.plex_url is None or selected.plex_token is None:
        raise ConfigurationAPIError("Plex URL and token are required.")
    return str(selected.plex_url), selected.plex_token


def get_configuration_api_service() -> ConfigurationAPIService:
    """Return the configuration API service."""
    return ConfigurationAPIService(ConfigurationService())


@lru_cache
def get_plex_sync_service() -> PlexLibrarySyncService:
    """Return the process-wide Plex sync service."""
    return PlexLibrarySyncService()


def get_review_api_service() -> ReviewAPIService:
    """Return the review API service."""
    settings = get_settings()
    plex_url, plex_token = require_plex_settings(settings)
    try:
        ai_manager = AIManager(settings=settings.ai)
    except AIError as exc:
        raise ProviderAPIError(str(exc) or "AI provider configuration failed.") from exc
    preview_service = EnrichmentPreviewService(plex_url, plex_token, ai_manager=ai_manager)
    return ReviewAPIService(ReviewService(preview_service=preview_service))


def get_apply_api_service() -> ApplyAPIService:
    """Return the apply API service."""
    settings = get_settings()
    plex_url, plex_token = require_plex_settings(settings)
    review_service = get_review_api_service().review_service
    apply_service = ApplyService(
        review_service=review_service,
        base_url=plex_url,
        token=plex_token,
        minimum_quality_score=settings.quality.minimum_quality_score,
        verification_confidence_threshold=settings.quality.verification_confidence_threshold,
    )
    return ApplyAPIService(apply_service)
