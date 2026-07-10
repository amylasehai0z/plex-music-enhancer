"""Typed models for the local knowledge cache."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CacheKind(StrEnum):
    """Supported top-level knowledge cache directories."""

    ARTISTS = "artists"
    ALBUMS = "albums"


class KnowledgeCacheEntry(BaseModel):
    """Serialized cache entry stored as JSON."""

    model_config = ConfigDict(frozen=True)

    cached_at: datetime
    source: str
    payload: dict[str, Any]
    provider_version: str | None = None
    schema_version: str = "1"
    prompt_version: str | None = None


class CacheEntryInfo(BaseModel):
    """Metadata for one cache file."""

    model_config = ConfigDict(frozen=True)

    kind: CacheKind
    source: str
    key: str
    path: Path
    cached_at: datetime
    expired: bool


class CacheStats(BaseModel):
    """Summary statistics for the knowledge cache."""

    model_config = ConfigDict(frozen=True)

    root: Path
    total_entries: int = 0
    fresh_entries: int = 0
    expired_entries: int = 0
    by_kind: dict[CacheKind, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
