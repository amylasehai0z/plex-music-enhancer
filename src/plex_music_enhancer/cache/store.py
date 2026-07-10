"""JSON file store for the local knowledge cache."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from typing import Any

from plex_music_enhancer.cache.models import (
    CacheEntryInfo,
    CacheKind,
    CacheStats,
    KnowledgeCacheEntry,
)
from plex_music_enhancer.utils.files import write_text_atomic

DEFAULT_CACHE_ROOT = Path.home() / ".plex-enhancer" / "cache"
DEFAULT_CACHE_TTL = timedelta(days=30)
DEFAULT_CACHE_SCHEMA_VERSION = "1"


class KnowledgeCacheStore:
    """Read and write local knowledge cache entries."""

    def __init__(
        self,
        *,
        root: Path = DEFAULT_CACHE_ROOT,
        ttl: timedelta = DEFAULT_CACHE_TTL,
        schema_version: str = DEFAULT_CACHE_SCHEMA_VERSION,
    ) -> None:
        """Create a cache store."""
        self.root = root
        self.ttl = ttl
        self.schema_version = schema_version

    def read(self, *, kind: CacheKind, source: str, key: str) -> KnowledgeCacheEntry | None:
        """Read a cache entry when present and valid JSON."""
        path = self.path_for(kind=kind, source=source, key=key)
        if not path.exists():
            return None

        try:
            return KnowledgeCacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def write(
        self,
        *,
        kind: CacheKind,
        source: str,
        key: str,
        payload: dict[str, Any],
        provider_version: str | None = None,
        prompt_version: str | None = None,
    ) -> Path:
        """Write a cache entry and return its path."""
        path = self.path_for(kind=kind, source=source, key=key)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = KnowledgeCacheEntry(
            cached_at=datetime.now(UTC),
            source=source,
            payload=payload,
            provider_version=provider_version,
            schema_version=self.schema_version,
            prompt_version=prompt_version,
        )
        write_text_atomic(path, entry.model_dump_json(indent=2))
        return path

    def is_expired(self, entry: KnowledgeCacheEntry) -> bool:
        """Return whether an entry is older than the configured TTL."""
        return (
            datetime.now(UTC) - entry.cached_at > self.ttl
            or entry.schema_version != self.schema_version
        )

    def clear(self, *, source: str | None = None, expired_only: bool = False) -> int:
        """Remove cache entries and return the number removed."""
        entries = self.list_entries()
        if source is None and not expired_only and self.root.exists():
            rmtree(self.root)
            return len(entries)

        removed = 0
        for entry in entries:
            if source is not None and entry.source != source:
                continue
            if expired_only and not entry.expired:
                continue
            entry.path.unlink(missing_ok=True)
            removed += 1
        return removed

    def list_entries(self) -> list[CacheEntryInfo]:
        """Return metadata for every valid cache entry."""
        entries: list[CacheEntryInfo] = []
        for kind in CacheKind:
            entries.extend(self._list_kind(kind))
        return sorted(entries, key=lambda entry: (entry.kind.value, entry.source, entry.key))

    def stats(self) -> CacheStats:
        """Return cache statistics."""
        entries = self.list_entries()
        by_kind = dict.fromkeys(CacheKind, 0)
        by_source: dict[str, int] = {}
        expired_entries = 0

        for entry in entries:
            by_kind[entry.kind] += 1
            by_source[entry.source] = by_source.get(entry.source, 0) + 1
            if entry.expired:
                expired_entries += 1

        return CacheStats(
            root=self.root,
            total_entries=len(entries),
            fresh_entries=len(entries) - expired_entries,
            expired_entries=expired_entries,
            by_kind=by_kind,
            by_source=by_source,
        )

    def path_for(self, *, kind: CacheKind, source: str, key: str) -> Path:
        """Return the cache path for a source/key pair."""
        return self.root / kind.value / f"{_safe_source(source)}-{_digest(key)}.json"

    def _list_kind(self, kind: CacheKind) -> Iterable[CacheEntryInfo]:
        """Yield entry info for one cache kind."""
        directory = self.root / kind.value
        if not directory.exists():
            return []

        entries: list[CacheEntryInfo] = []
        for path in directory.glob("*.json"):
            try:
                entry = KnowledgeCacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
            except ValueError:
                continue

            source = entry.source
            entries.append(
                CacheEntryInfo(
                    kind=kind,
                    source=source,
                    key=path.stem.removeprefix(f"{_safe_source(source)}-"),
                    path=path,
                    cached_at=entry.cached_at,
                    expired=self.is_expired(entry),
                )
            )
        return entries


def _digest(key: str) -> str:
    """Return a stable digest for a cache key."""
    return sha256(key.strip().casefold().encode("utf-8")).hexdigest()


def _safe_source(source: str) -> str:
    """Return a filesystem-safe source label."""
    return "".join(character if character.isalnum() else "-" for character in source).strip("-")
