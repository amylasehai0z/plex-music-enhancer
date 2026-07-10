"""High-level local knowledge cache service."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from plex_music_enhancer.cache.models import CacheKind, KnowledgeCacheEntry
from plex_music_enhancer.cache.store import KnowledgeCacheStore


class KnowledgeCacheService:
    """Cache typed provider results while transparently refreshing expired entries."""

    def __init__(self, store: KnowledgeCacheStore | None = None) -> None:
        """Create a knowledge cache service."""
        self.store = store or KnowledgeCacheStore()

    def get_model[ModelT: BaseModel](
        self,
        *,
        kind: CacheKind,
        source: str,
        key: str,
        model_type: type[ModelT],
    ) -> ModelT | None:
        """Return a fresh cached model when available."""
        entry = self.store.read(kind=kind, source=source, key=key)
        if entry is None or self.store.is_expired(entry):
            return None
        return _model_from_entry(entry, model_type)

    def set_model(
        self,
        *,
        kind: CacheKind,
        source: str,
        key: str,
        value: BaseModel,
        provider_version: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        """Store a model in the cache."""
        self.store.write(
            kind=kind,
            source=source,
            key=key,
            payload=value.model_dump(mode="json"),
            provider_version=provider_version,
            prompt_version=prompt_version,
        )

    def get_or_refresh[ModelT: BaseModel](
        self,
        *,
        kind: CacheKind,
        source: str,
        key: str,
        model_type: type[ModelT],
        refresh: Callable[[], ModelT | None],
    ) -> ModelT | None:
        """Return a cached model or refresh and persist it."""
        cached = self.get_model(kind=kind, source=source, key=key, model_type=model_type)
        if cached is not None:
            return cached

        value = refresh()
        if value is not None:
            self.set_model(kind=kind, source=source, key=key, value=value)
        return value


def _model_from_entry[ModelT: BaseModel](
    entry: KnowledgeCacheEntry,
    model_type: type[ModelT],
) -> ModelT | None:
    """Validate a cached payload as the requested model type."""
    try:
        return model_type.model_validate(entry.payload)
    except ValueError:
        return None
