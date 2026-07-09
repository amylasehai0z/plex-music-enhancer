"""Internal configuration API service adapter."""

from __future__ import annotations

from dataclasses import dataclass

from plex_music_enhancer.api.models import ConfigurationResponse
from plex_music_enhancer.services import ConfigurationService


@dataclass(frozen=True)
class ConfigurationAPIService:
    """Return sanitized configuration through the internal API layer."""

    configuration_service: ConfigurationService

    def configuration(self) -> ConfigurationResponse:
        """Return a versioned configuration response."""
        return ConfigurationResponse(
            configuration=self.configuration_service.snapshot().model_dump(by_alias=True),
        )
