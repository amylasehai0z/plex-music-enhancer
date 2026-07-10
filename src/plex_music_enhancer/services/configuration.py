"""Application-level configuration access."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Protocol

from pydantic import SecretStr

from plex_music_enhancer.config import AISettings, DiscogsSettings, LastFMSettings, Settings
from plex_music_enhancer.contracts import ConfigurationContract
from plex_music_enhancer.utils.files import write_text_atomic


class _SettingsFactory(Protocol):
    """Callable settings factory used for dependency injection."""

    def __call__(self) -> Settings:
        """Return application settings."""


@dataclass(frozen=True)
class ConfigurationService:
    """Expose sanitized runtime configuration to frontends and diagnostics."""

    settings_factory: _SettingsFactory = Settings
    store: PersistentConfigurationStore | None = None

    def snapshot(self) -> ConfigurationContract:
        """Return a frontend-safe configuration snapshot without secrets."""
        return _snapshot(self.settings_factory())

    def update(self, update: ConfigurationUpdate) -> ConfigurationContract:
        """Persist a validated runtime configuration update and return a safe snapshot."""
        store = self.store or PersistentConfigurationStore.default()
        current = self.settings_factory()
        candidate = update.apply(current)
        store.save(update.to_environment(candidate))
        return _snapshot(candidate)


@dataclass(frozen=True)
class ConfigurationUpdate:
    """Validated configuration update from the web API."""

    plex_url: str | None = None
    plex_token: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    openai_api_key: str | None = None
    discogs_token: str | None = None
    lastfm_api_key: str | None = None
    provided_fields: frozenset[str] = frozenset()

    def apply(self, current: Settings) -> Settings:
        """Return settings with this update applied, raising validation errors early."""
        ai_values = current.ai.model_dump()
        discogs_values = current.discogs.model_dump()
        lastfm_values = current.lastfm.model_dump()

        if "ai_provider" in self.provided_fields:
            ai_values["provider"] = self.ai_provider or AISettings().provider
        if "ai_model" in self.provided_fields:
            ai_values["model"] = self.ai_model or AISettings().model
        if "openai_api_key" in self.provided_fields:
            ai_values["api_key"] = _secret_or_none(self.openai_api_key)
        if "discogs_token" in self.provided_fields:
            discogs_values["token"] = _secret_or_none(self.discogs_token)
        if "lastfm_api_key" in self.provided_fields:
            lastfm_values["api_key"] = _secret_or_none(self.lastfm_api_key)

        values = {
            "plex_url": str(current.plex_url) if current.plex_url is not None else None,
            "plex_token": current.plex_token,
            "request_timeout_seconds": current.request_timeout_seconds,
            "log_level": current.log_level,
            "ai": AISettings(**ai_values),
            "discogs": DiscogsSettings(**discogs_values),
            "lastfm": LastFMSettings(**lastfm_values),
            "quality": current.quality,
            "performance": current.performance,
        }
        if "plex_url" in self.provided_fields:
            values["plex_url"] = self.plex_url or None
        if "plex_token" in self.provided_fields:
            values["plex_token"] = _secret_or_none(self.plex_token)
        return Settings(_env_file=None, **values)

    def to_environment(self, settings: Settings) -> dict[str, str | None]:
        """Return environment variable updates for fields explicitly provided by the UI."""
        updates: dict[str, str | None] = {}
        if "plex_url" in self.provided_fields:
            updates["PLEX_ENHANCER_PLEX_URL"] = (
                str(settings.plex_url).rstrip("/") if settings.plex_url is not None else None
            )
        if "plex_token" in self.provided_fields:
            updates["PLEX_ENHANCER_PLEX_TOKEN"] = _secret_value(settings.plex_token)
        if "ai_provider" in self.provided_fields:
            updates["PLEX_ENHANCER_AI__PROVIDER"] = settings.ai.provider
        if "ai_model" in self.provided_fields:
            updates["PLEX_ENHANCER_AI__MODEL"] = settings.ai.model
        if "openai_api_key" in self.provided_fields:
            updates["PLEX_ENHANCER_AI__API_KEY"] = _secret_value(settings.ai.api_key)
        if "discogs_token" in self.provided_fields:
            updates["PLEX_ENHANCER_DISCOGS__TOKEN"] = _secret_value(settings.discogs.token)
        if "lastfm_api_key" in self.provided_fields:
            updates["PLEX_ENHANCER_LASTFM__API_KEY"] = _secret_value(settings.lastfm.api_key)
        return updates


@dataclass(frozen=True)
class PersistentConfigurationStore:
    """Persist runtime configuration in the container configuration volume."""

    path: Path

    @classmethod
    def default(cls) -> PersistentConfigurationStore:
        """Return the store configured by PLEX_ENHANCER_CONFIG or `/config/.env`."""
        return cls(_runtime_config_path())

    def save(self, updates: dict[str, str | None]) -> None:
        """Persist selected environment updates and mirror them into the running process."""
        if not updates:
            return
        existing_lines = (
            self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        )
        remaining = updates.copy()
        updated_lines: list[str] = []

        for line in existing_lines:
            key = _parse_env_key(line)
            if key in remaining:
                value = remaining.pop(key)
                if value is not None:
                    updated_lines.append(f"{key}={_quote_env_value(value)}")
                continue
            updated_lines.append(line)

        for key, value in remaining.items():
            if value is not None:
                updated_lines.append(f"{key}={_quote_env_value(value)}")

        write_text_atomic(self.path, "\n".join(updated_lines).rstrip() + "\n")
        for key, value in updates.items():
            if value is None:
                environ.pop(key, None)
            else:
                environ[key] = value


def configuration_update_from_payload(payload: dict[str, object]) -> ConfigurationUpdate:
    """Build a typed configuration update from an API payload."""
    aliases = {
        "plexUrl": "plex_url",
        "plexToken": "plex_token",
        "aiProvider": "ai_provider",
        "aiModel": "ai_model",
        "openaiApiKey": "openai_api_key",
        "discogsToken": "discogs_token",
        "lastfmApiKey": "lastfm_api_key",
    }
    values: dict[str, str | None] = {}
    provided_fields: set[str] = set()
    for alias, field in aliases.items():
        if alias not in payload:
            continue
        raw_value = payload[alias]
        if raw_value is None:
            values[field] = None
        elif isinstance(raw_value, str):
            stripped = raw_value.strip()
            values[field] = stripped or None
        else:
            msg = f"{alias} must be a string or null."
            raise ValueError(msg)
        provided_fields.add(field)
    return ConfigurationUpdate(**values, provided_fields=frozenset(provided_fields))


def _mask_secret(secret: SecretStr | None) -> str | None:
    """Return a stable display mask without exposing the secret."""
    value = _secret_value(secret)
    if value is None:
        return None
    suffix = value[-4:] if len(value) >= 4 else "****"
    return f"************{suffix}"


def _snapshot(settings: Settings) -> ConfigurationContract:
    """Return a frontend-safe configuration snapshot without secrets."""
    return ConfigurationContract(
        plex_configured=settings.has_plex_configuration,
        plex_url=str(settings.plex_url) if settings.plex_url is not None else None,
        plex_token_configured=settings.plex_token is not None,
        plex_token_masked=_mask_secret(settings.plex_token),
        ai_provider=settings.ai.provider,
        ai_model=settings.ai.model,
        openai_api_key_configured=settings.ai.api_key is not None,
        openai_api_key_masked=_mask_secret(settings.ai.api_key),
        discogs_configured=settings.discogs.token is not None,
        discogs_token_masked=_mask_secret(settings.discogs.token),
        lastfm_configured=settings.lastfm.api_key is not None,
        lastfm_api_key_masked=_mask_secret(settings.lastfm.api_key),
        max_prompt_characters=settings.ai.max_prompt_characters,
    )


def _secret_or_none(value: str | None) -> SecretStr | None:
    """Return a SecretStr for non-empty values."""
    return SecretStr(value) if value else None


def _secret_value(secret: SecretStr | None) -> str | None:
    """Return the raw secret value for persistence only."""
    return secret.get_secret_value() if secret is not None else None


def _runtime_config_path() -> Path:
    """Return the persistent runtime dotenv path."""
    raw_path = environ.get("PLEX_ENHANCER_CONFIG", "/config")
    path = Path(raw_path).expanduser()
    if path.suffix == ".env":
        return path
    if path.exists() and path.is_file():
        return path
    return path / ".env"


def _parse_env_key(line: str) -> str | None:
    """Return the key for a simple dotenv assignment line."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _separator, _value = stripped.partition("=")
    return key.strip()


def _quote_env_value(value: str) -> str:
    """Return a shell-compatible dotenv value."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    return f'"{escaped}"'


__all__ = [
    "ConfigurationService",
    "ConfigurationUpdate",
    "PersistentConfigurationStore",
    "configuration_update_from_payload",
]
