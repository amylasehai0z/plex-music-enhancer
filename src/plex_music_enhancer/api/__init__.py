"""Internal backend API preparation layer.

The API package contains versioned request/response models, service adapters,
and errors for future FastAPI integration. It intentionally exposes no HTTP
routes yet.
"""

from plex_music_enhancer.api.errors import (
    APIError,
    ConfigurationAPIError,
    PlexAPIError,
    PromptAPIError,
    ProviderAPIError,
    ReviewAPIError,
    ValidationAPIError,
    VerificationAPIError,
)
from plex_music_enhancer.api.models import API_VERSION

__all__ = [
    "APIError",
    "API_VERSION",
    "ConfigurationAPIError",
    "PlexAPIError",
    "PromptAPIError",
    "ProviderAPIError",
    "ReviewAPIError",
    "ValidationAPIError",
    "VerificationAPIError",
]
