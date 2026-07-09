"""Runtime configuration for Plex Music Enhancer."""

from __future__ import annotations

from functools import lru_cache
from os import environ
from pathlib import Path
from typing import Annotated

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_trailing_slash(value: object) -> object:
    """Normalize URL-like values before Pydantic validates them."""
    if isinstance(value, str):
        return value.rstrip("/")
    return value


NormalizedHttpUrl = Annotated[AnyHttpUrl, BeforeValidator(_strip_trailing_slash)]


class AISettings(BaseModel):
    """AI provider configuration."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(
        default="dummy",
        description="Configured AI provider name.",
    )
    model: str = Field(
        default="gpt-5.5",
        description="Configured AI model name.",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Optional AI provider API key.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description="Timeout, in seconds, for AI provider requests.",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum retries for transient AI provider failures.",
    )
    max_prompt_characters: int = Field(
        default=20000,
        gt=0,
        description="Maximum rendered prompt length sent to AI providers.",
    )


class DiscogsSettings(BaseModel):
    """Optional Discogs provider configuration."""

    model_config = ConfigDict(frozen=True)

    token: SecretStr | None = Field(
        default=None,
        description="Optional Discogs personal access token.",
    )
    timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=60,
        description="Timeout, in seconds, for Discogs API requests.",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum retries for transient Discogs API failures.",
    )
    rate_limit_seconds: float = Field(
        default=1.0,
        ge=0,
        le=10,
        description="Minimum delay between Discogs API requests.",
    )


class LastFMSettings(BaseModel):
    """Optional Last.fm provider configuration."""

    model_config = ConfigDict(frozen=True)

    api_key: SecretStr | None = Field(
        default=None,
        description="Optional Last.fm API key.",
    )
    timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=60,
        description="Timeout, in seconds, for Last.fm API requests.",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum retries for transient Last.fm API failures.",
    )
    rate_limit_seconds: float = Field(
        default=0.25,
        ge=0,
        le=10,
        description="Minimum delay between Last.fm API requests.",
    )


class QualitySettings(BaseModel):
    """Editorial quality assurance configuration."""

    model_config = ConfigDict(frozen=True)

    minimum_quality_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Optional minimum editorial QA score required before apply.",
    )
    verification_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum fact verification confidence required before apply.",
    )


class PerformanceSettings(BaseModel):
    """Production performance and scalability configuration."""

    model_config = ConfigDict(frozen=True)

    max_workers: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Maximum worker threads for independent provider lookups.",
    )
    provider_timeout: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description="Default provider timeout in seconds.",
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default retry attempts for transient operations.",
    )
    cache_expiration_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Default knowledge cache expiration in days.",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Preferred processing batch size for large libraries.",
    )
    database_location: Path = Field(
        default=Path.home() / ".plex-enhancer" / "processing.sqlite3",
        description="SQLite processing-state database location.",
    )
    quality_threshold: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Optional quality threshold used by incremental processing.",
    )
    incremental_mode: bool = Field(
        default=True,
        description="Skip albums whose metadata and generation inputs have not changed.",
    )

    @field_validator("database_location")
    @classmethod
    def _expand_database_location(cls, value: Path) -> Path:
        """Expand user-home markers for database paths."""
        return value.expanduser()


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env` files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PLEX_ENHANCER_",
        env_nested_delimiter="__",
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
    ai: AISettings = Field(default_factory=AISettings)
    discogs: DiscogsSettings = Field(default_factory=DiscogsSettings)
    lastfm: LastFMSettings = Field(default_factory=LastFMSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)

    def __init__(self, **values: object) -> None:
        """Create settings with deterministic dotenv behavior during tests."""
        if "_env_file" not in values and _running_under_pytest():
            values["_env_file"] = None

        super().__init__(**values)
        default_prompt_budget = AISettings().max_prompt_characters
        legacy_prompt_budget = environ.get("AI_PROMPT_MAX_CHARS") or _dotenv_value(
            "AI_PROMPT_MAX_CHARS",
            values.get("_env_file", ".env"),
        )
        if self.ai.max_prompt_characters == default_prompt_budget and legacy_prompt_budget:
            ai_values = self.ai.model_dump()
            ai_values["max_prompt_characters"] = int(legacy_prompt_budget)
            self.ai = AISettings(**ai_values)

    @property
    def has_plex_configuration(self) -> bool:
        """Return whether the required Plex connection settings are present."""
        return self.plex_url is not None and self.plex_token is not None


def _running_under_pytest() -> bool:
    """Return whether the current process is executing a pytest test case."""
    return "PYTEST_CURRENT_TEST" in environ


def _dotenv_value(key: str, env_file: object) -> str | None:
    """Return one simple key from a dotenv file when dotenv loading is enabled."""
    if env_file is None:
        return None
    path = Path(str(env_file))
    if not path.exists():
        return None
    prefix = f"{key}="
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip().strip("\"'")
    return None


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
