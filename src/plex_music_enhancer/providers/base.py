"""Common metadata provider interfaces and models."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ArtistMetadata(BaseModel):
    """Normalized artist metadata gathered from one or more providers."""

    model_config = ConfigDict(frozen=True)

    title: str
    artist: str | None = None
    summary: str | None = None
    language: str | None = None
    source: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class AlbumMetadata(BaseModel):
    """Normalized album metadata gathered from one or more providers."""

    model_config = ConfigDict(frozen=True)

    title: str
    artist: str
    summary: str | None = None
    language: str | None = None
    source: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class MetadataProvider(Protocol):
    """Common synchronous interface for read-only metadata providers."""

    @property
    def name(self) -> str:
        """Return a stable provider name for attribution."""

    def search_artist(self, artist: str, *, limit: int = 5) -> list[ArtistMetadata]:
        """Search for artist metadata candidates."""

    def search_album(self, artist: str, album: str, *, limit: int = 5) -> list[AlbumMetadata]:
        """Search for album metadata candidates."""

    def get_artist_summary(self, artist: str, *, language: str = "en") -> ArtistMetadata | None:
        """Return an artist summary when the provider has one."""

    def get_album_summary(
        self,
        artist: str,
        album: str,
        *,
        language: str = "en",
    ) -> AlbumMetadata | None:
        """Return an album summary when the provider has one."""
