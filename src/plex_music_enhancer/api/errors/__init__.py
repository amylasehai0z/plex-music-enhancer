"""Shared internal API error hierarchy."""

from plex_music_enhancer.api.errors.base import (
    APIError,
    ConfigurationAPIError,
    PlexAPIError,
    PromptAPIError,
    ProviderAPIError,
    ReviewAPIError,
    ValidationAPIError,
    VerificationAPIError,
)

__all__ = [
    "APIError",
    "ConfigurationAPIError",
    "PlexAPIError",
    "PromptAPIError",
    "ProviderAPIError",
    "ReviewAPIError",
    "ValidationAPIError",
    "VerificationAPIError",
]
