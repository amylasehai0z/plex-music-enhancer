"""Internal configuration API service adapter."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import SecretStr, ValidationError

from plex_music_enhancer.api.errors import ConfigurationAPIError
from plex_music_enhancer.api.models import (
    ConfigurationResponse,
    ConfigurationUpdateRequest,
    PlexConnectionTestRequest,
    PlexConnectionTestResponse,
)
from plex_music_enhancer.config import Settings
from plex_music_enhancer.plex.client import PlexClient
from plex_music_enhancer.services import ConfigurationService
from plex_music_enhancer.services.configuration import configuration_update_from_payload


@dataclass(frozen=True)
class ConfigurationAPIService:
    """Return sanitized configuration through the internal API layer."""

    configuration_service: ConfigurationService

    def configuration(self) -> ConfigurationResponse:
        """Return a versioned configuration response."""
        return ConfigurationResponse(
            configuration=self.configuration_service.snapshot().model_dump(by_alias=True),
        )

    def update(self, request: ConfigurationUpdateRequest) -> ConfigurationResponse:
        """Validate and persist runtime configuration."""
        try:
            update = configuration_update_from_payload(
                request.model_dump(by_alias=True, exclude_unset=True),
            )
            snapshot = self.configuration_service.update(update)
        except ValueError as exc:
            raise ConfigurationAPIError(str(exc)) from exc
        except ValidationError as exc:
            raise ConfigurationAPIError(
                "Configuration validation failed.",
                details={"errors": exc.errors(include_url=False)},
            ) from exc
        return ConfigurationResponse(configuration=snapshot.model_dump(by_alias=True))

    def test_plex_connection(
        self,
        request: PlexConnectionTestRequest,
    ) -> PlexConnectionTestResponse:
        """Test Plex connectivity without returning or persisting secrets."""
        settings = Settings()
        plex_url = request.plex_url or (str(settings.plex_url) if settings.plex_url else None)
        plex_token = request.plex_token or (
            settings.plex_token.get_secret_value() if settings.plex_token else None
        )
        if not plex_url or not plex_token:
            raise ConfigurationAPIError("Plex URL and token are required to test the connection.")

        try:
            validated = Settings(
                _env_file=None,
                plex_url=plex_url,
                plex_token=SecretStr(plex_token),
            )
        except ValidationError as exc:
            raise ConfigurationAPIError(
                "Plex connection settings are invalid.",
                details={"errors": exc.errors(include_url=False)},
            ) from exc

        if validated.plex_url is None or validated.plex_token is None:
            raise ConfigurationAPIError("Plex URL and token are required to test the connection.")

        result = PlexClient(
            validated.plex_url,
            validated.plex_token,
            timeout_seconds=validated.request_timeout_seconds,
        ).check_connection()
        return PlexConnectionTestResponse(
            ok=result.ok,
            status_code=result.status_code,
            server_name=result.server_name,
            message=result.message
            or ("Connected successfully." if result.ok else "Connection failed."),
        )
