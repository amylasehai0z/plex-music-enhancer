"""Application-level configuration access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from plex_music_enhancer.config import Settings
from plex_music_enhancer.contracts import ConfigurationContract


class _SettingsFactory(Protocol):
    """Callable settings factory used for dependency injection."""

    def __call__(self) -> Settings:
        """Return application settings."""


@dataclass(frozen=True)
class ConfigurationService:
    """Expose sanitized runtime configuration to frontends and diagnostics."""

    settings_factory: _SettingsFactory = Settings

    def snapshot(self) -> ConfigurationContract:
        """Return a frontend-safe configuration snapshot without secrets."""
        settings = self.settings_factory()
        return ConfigurationContract(
            plex_configured=settings.has_plex_configuration,
            plex_url=str(settings.plex_url) if settings.plex_url is not None else None,
            ai_provider=settings.ai.provider,
            ai_model=settings.ai.model,
            openai_api_key_configured=settings.ai.api_key is not None,
            discogs_configured=settings.discogs.token is not None,
            lastfm_configured=settings.lastfm.api_key is not None,
            max_prompt_characters=settings.ai.max_prompt_characters,
        )
