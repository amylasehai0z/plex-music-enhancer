"""Performance and scalability infrastructure tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep

from pydantic import BaseModel

from plex_music_enhancer.cache import CacheKind, KnowledgeCacheStore
from plex_music_enhancer.config import Settings
from plex_music_enhancer.performance import (
    BenchmarkService,
    IncrementalProcessor,
    ProcessingDatabase,
    ProcessingRecord,
    ProviderScheduler,
    ProviderTask,
    RetryPolicy,
    build_fingerprint,
    retry_call,
)


class _CachedModel(BaseModel):
    """Tiny cached model."""

    value: str


class _AlbumSource:
    """Fake benchmark album source."""

    def scan_albums(self, *, library: str | None = None) -> list[object]:
        """Return fake albums."""
        return [object(), object()] if library == "Music" else [object()]


def test_provider_scheduler_runs_tasks_and_skips_unneeded_work() -> None:
    """Scheduler should run selected providers and report skipped providers."""
    scheduler = ProviderScheduler(max_workers=2)

    results = scheduler.run(
        [
            ProviderTask(name="wikipedia", operation=lambda: "ok"),
            ProviderTask(name="discogs", operation=lambda: "unused", should_run=lambda: False),
        ]
    )

    assert results["wikipedia"].value == "ok"
    assert results["discogs"].skipped is True


def test_provider_scheduler_uses_bounded_concurrency() -> None:
    """Independent tasks should be able to overlap."""
    scheduler = ProviderScheduler(max_workers=2)

    results = scheduler.run(
        [
            ProviderTask(name="a", operation=lambda: _delayed("a")),
            ProviderTask(name="b", operation=lambda: _delayed("b")),
        ]
    )

    assert {result.value for result in results.values()} == {"a", "b"}
    assert sum(result.duration_seconds for result in results.values()) >= 0.02


def test_retry_call_retries_transient_failures() -> None:
    """Retry helper should retry configured transient failures."""
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise TimeoutError("temporary")
        return "done"

    result = retry_call(
        operation,
        policy=RetryPolicy(attempts=3, initial_delay_seconds=0),
        sleeper=lambda _: None,
    )

    assert result == "done"
    assert attempts == 2


def test_processing_database_persists_records(tmp_path: Path) -> None:
    """Processing database should persist and reload records."""
    database = ProcessingDatabase(tmp_path / "processing.sqlite3")
    record = _processing_record(album_identifier="album-1")

    database.upsert_record(record)

    loaded = database.get_record("album-1")
    assert loaded is not None
    assert loaded.metadata_hash == "metadata"
    assert database.pending_after_crash() == []


def test_incremental_processor_skips_unchanged_successful_records(tmp_path: Path) -> None:
    """Incremental processor should skip unchanged successful albums."""
    database = ProcessingDatabase(tmp_path / "processing.sqlite3")
    fingerprint = build_fingerprint(
        album_identifier="album-1",
        artist_identifier="artist-1",
        source_metadata={"summary": "A"},
        provider_versions={"musicbrainz": "1"},
        prompt_version="1.0",
        model="gpt-test",
        cache_version="1",
        quality_threshold=80,
        configuration={"max_workers": 4},
    )
    database.upsert_record(
        _processing_record(
            album_identifier="album-1",
            artist_identifier="artist-1",
            metadata_hash=fingerprint.metadata_hash,
            generation_hash=fingerprint.generation_hash,
            provider_versions=fingerprint.provider_versions,
            prompt_version=fingerprint.prompt_version,
            model=fingerprint.model,
            cache_version=fingerprint.cache_version,
        )
    )

    assert IncrementalProcessor(database).should_process(fingerprint) is False


def test_incremental_processor_processes_changed_records(tmp_path: Path) -> None:
    """Changed fingerprints should be regenerated."""
    database = ProcessingDatabase(tmp_path / "processing.sqlite3")
    database.upsert_record(_processing_record(album_identifier="album-1"))
    fingerprint = build_fingerprint(
        album_identifier="album-1",
        artist_identifier=None,
        source_metadata={"summary": "changed"},
        provider_versions={"musicbrainz": "2"},
        prompt_version="1.1",
        model="gpt-test",
        cache_version="2",
        quality_threshold=90,
        configuration={"max_workers": 8},
    )

    assert IncrementalProcessor(database).should_process(fingerprint) is True


def test_cache_schema_version_invalidates_entries(tmp_path: Path) -> None:
    """Cache entries should expire automatically after schema upgrades."""
    old_store = KnowledgeCacheStore(root=tmp_path, schema_version="1")
    old_store.write(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album",
        payload=_CachedModel(value="ok").model_dump(),
    )

    upgraded_store = KnowledgeCacheStore(root=tmp_path, schema_version="2")
    entry = upgraded_store.read(kind=CacheKind.ALBUMS, source="musicbrainz", key="album")

    assert entry is not None
    assert upgraded_store.is_expired(entry) is True


def test_cache_partial_clear_removes_only_matching_entries(tmp_path: Path) -> None:
    """Cache clear should support partial cleanup."""
    store = KnowledgeCacheStore(root=tmp_path)
    store.write(kind=CacheKind.ALBUMS, source="musicbrainz", key="a", payload={})
    store.write(kind=CacheKind.ALBUMS, source="wikipedia", key="a", payload={})

    removed = store.clear(source="musicbrainz")

    assert removed == 1
    assert len(store.list_entries()) == 1


def test_benchmark_service_reports_scan_and_cache_metrics(tmp_path: Path) -> None:
    """Benchmark should produce a serializable read-only report."""
    service = BenchmarkService(
        album_source=_AlbumSource(),
        cache_store=KnowledgeCacheStore(root=tmp_path),
    )

    report = service.run(library="Music")

    assert report.albums_scanned == 2
    assert "plex_scan" in report.provider_timings
    assert report.recommendations


def test_performance_settings_can_be_configured() -> None:
    """Performance settings should be available from the main settings model."""
    settings = Settings(
        performance={
            "max_workers": 8,
            "retry_attempts": 4,
            "batch_size": 250,
            "incremental_mode": False,
        }
    )

    assert settings.performance.max_workers == 8
    assert settings.performance.retry_attempts == 4
    assert settings.performance.batch_size == 250
    assert settings.performance.incremental_mode is False


def _delayed(value: str) -> str:
    """Return a value after a tiny delay."""
    sleep(0.02)
    return value


def _processing_record(
    *,
    album_identifier: str,
    artist_identifier: str | None = None,
    metadata_hash: str = "metadata",
    generation_hash: str = "generation",
    provider_versions: str = "providers",
    prompt_version: str | None = "1.0",
    model: str | None = "gpt-test",
    cache_version: str = "1",
) -> ProcessingRecord:
    """Return a processing record."""
    return ProcessingRecord(
        album_identifier=album_identifier,
        artist_identifier=artist_identifier,
        generation_timestamp=datetime.now(UTC) - timedelta(seconds=1),
        provider_versions=provider_versions,
        metadata_hash=metadata_hash,
        generation_hash=generation_hash,
        quality_score=90,
        generation_status="SUCCESS",
        prompt_version=prompt_version,
        model=model,
        cache_version=cache_version,
        processing_duration_seconds=1.0,
        errors=None,
    )
