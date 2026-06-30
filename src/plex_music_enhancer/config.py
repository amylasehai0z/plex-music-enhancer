"""Runtime configuration for Plex Music Enhancer."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, BeforeValidator, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_trailing_slash(value: object) -> object:
    """Normalize URL-like values before Pydantic validates them."""
    if isinstance(value, str):
        return value.rstrip("/")
    return value


NormalizedHttpUrl = Annotated[AnyHttpUrl, BeforeValidator(_strip_trailing_slash)]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env` files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PLEX_ENHANCER_",
        extra="ignore",
        case_sensitive=False,
    )

    plex_url: NormalizedHttpUrl | None = Field(
        default=None,
        description="Base URL of the Plex server, for example http://localhost:32400.",
    )
    plex_token: SecretStr | None = Field(
        default=None,
        description="Plex authentication token used for server API requests.",
    )
    request_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=60,
        description="Timeout, in seconds, for Plex API health checks.",
    )
    log_level: str = Field(
        default="INFO",
        description="Standard Python log level.",
    )

    @property
    def has_plex_configuration(self) -> bool:
        """Return whether the required Plex connection settings are present."""
        return self.plex_url is not None and self.plex_token is not None


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
