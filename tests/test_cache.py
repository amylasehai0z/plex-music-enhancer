"""Knowledge cache tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict

from plex_music_enhancer.cache import CacheKind, KnowledgeCacheEntry, KnowledgeCacheService
from plex_music_enhancer.cache.store import KnowledgeCacheStore


class CachedPayload(BaseModel):
    """Small typed payload for cache tests."""

    model_config = ConfigDict(frozen=True)

    title: str


def test_knowledge_cache_returns_fresh_hit(tmp_path) -> None:
    """Fresh entries should be returned without refreshing."""
    service = KnowledgeCacheService(KnowledgeCacheStore(root=tmp_path))
    service.set_model(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album-key",
        value=CachedPayload(title="Pastel Blues"),
    )

    cached = service.get_model(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album-key",
        model_type=CachedPayload,
    )

    assert cached == CachedPayload(title="Pastel Blues")


def test_knowledge_cache_reports_miss(tmp_path) -> None:
    """Missing entries should return None."""
    service = KnowledgeCacheService(KnowledgeCacheStore(root=tmp_path))

    cached = service.get_model(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="missing",
        model_type=CachedPayload,
    )

    assert cached is None


def test_knowledge_cache_ignores_expired_entries(tmp_path) -> None:
    """Expired entries should be treated as misses."""
    store = KnowledgeCacheStore(root=tmp_path, ttl=timedelta(days=30))
    service = KnowledgeCacheService(store)
    service.set_model(
        kind=CacheKind.ARTISTS,
        source="wikipedia",
        key="artist-key",
        value=CachedPayload(title="Nina Simone"),
    )
    path = store.path_for(kind=CacheKind.ARTISTS, source="wikipedia", key="artist-key")
    expired_entry = KnowledgeCacheEntry(
        cached_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="wikipedia",
        payload={"title": "Nina Simone"},
    )
    path.write_text(expired_entry.model_dump_json(indent=2), encoding="utf-8")

    cached = service.get_model(
        kind=CacheKind.ARTISTS,
        source="wikipedia",
        key="artist-key",
        model_type=CachedPayload,
    )

    assert cached is None


def test_knowledge_cache_refreshes_and_reuses_value(tmp_path) -> None:
    """Misses should refresh once and persist the refreshed value."""
    service = KnowledgeCacheService(KnowledgeCacheStore(root=tmp_path))
    refresh_calls = 0

    def refresh() -> CachedPayload:
        nonlocal refresh_calls
        refresh_calls += 1
        return CachedPayload(title="Pastel Blues")

    first = service.get_or_refresh(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album-key",
        model_type=CachedPayload,
        refresh=refresh,
    )
    second = service.get_or_refresh(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album-key",
        model_type=CachedPayload,
        refresh=refresh,
    )

    assert first == CachedPayload(title="Pastel Blues")
    assert second == CachedPayload(title="Pastel Blues")
    assert refresh_calls == 1


def test_knowledge_cache_clear_removes_entries(tmp_path) -> None:
    """Clearing the cache should remove all entries."""
    store = KnowledgeCacheStore(root=tmp_path)
    service = KnowledgeCacheService(store)
    service.set_model(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album-key",
        value=CachedPayload(title="Pastel Blues"),
    )

    removed = store.clear()

    assert removed == 1
    assert store.list_entries() == []
