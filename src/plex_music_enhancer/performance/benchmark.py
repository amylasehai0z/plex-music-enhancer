"""Performance benchmark diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from resource import RUSAGE_SELF, getrusage
from time import perf_counter, process_time

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.cache import CacheStats, KnowledgeCacheStore


class BenchmarkReport(BaseModel):
    """Serializable benchmark diagnostics."""

    model_config = ConfigDict(frozen=True)

    library: str | None = None
    albums_scanned: int = Field(default=0, serialization_alias="albumsScanned")
    scan_duration_seconds: float = Field(default=0.0, serialization_alias="scanDurationSeconds")
    throughput_per_hour: float = Field(default=0.0, serialization_alias="throughputPerHour")
    cpu_time_seconds: float = Field(default=0.0, serialization_alias="cpuTimeSeconds")
    memory_mb: float = Field(default=0.0, serialization_alias="memoryMb")
    cache_entries: int = Field(default=0, serialization_alias="cacheEntries")
    cache_expired_entries: int = Field(default=0, serialization_alias="cacheExpiredEntries")
    cache_hit_ratio_estimate: float | None = Field(
        default=None,
        serialization_alias="cacheHitRatioEstimate",
    )
    provider_timings: dict[str, float] = Field(
        default_factory=dict,
        serialization_alias="providerTimings",
    )
    slowest_operations: list[str] = Field(
        default_factory=list,
        serialization_alias="slowestOperations",
    )
    recommendations: list[str] = Field(default_factory=list)


class BenchmarkAlbumSource:
    """Protocol-like source of albums for benchmark scans."""

    def scan_albums(self, *, library: str | None = None) -> list[object]:
        """Return albums to benchmark."""
        raise NotImplementedError


@dataclass(frozen=True)
class BenchmarkService:
    """Run read-only performance diagnostics."""

    album_source: BenchmarkAlbumSource
    cache_store: KnowledgeCacheStore

    def run(self, *, library: str | None = None) -> BenchmarkReport:
        """Benchmark library scanning and local cache health."""
        wall_start = perf_counter()
        cpu_start = process_time()
        albums = self.album_source.scan_albums(library=library)
        scan_duration = perf_counter() - wall_start
        cpu_time = process_time() - cpu_start
        cache_stats = self.cache_store.stats()
        album_count = len(albums)
        throughput = album_count / scan_duration * 3600 if scan_duration > 0 else 0.0
        return BenchmarkReport(
            library=library,
            albums_scanned=album_count,
            scan_duration_seconds=round(scan_duration, 4),
            throughput_per_hour=round(throughput, 2),
            cpu_time_seconds=round(cpu_time, 4),
            memory_mb=_memory_mb(),
            cache_entries=cache_stats.total_entries,
            cache_expired_entries=cache_stats.expired_entries,
            cache_hit_ratio_estimate=_cache_hit_ratio(cache_stats),
            provider_timings={"plex_scan": round(scan_duration, 4)},
            slowest_operations=["plex_scan"] if album_count else [],
            recommendations=_recommendations(album_count, scan_duration, cache_stats),
        )


def _cache_hit_ratio(stats: CacheStats) -> float | None:
    """Return a coarse cache freshness ratio."""
    if stats.total_entries == 0:
        return None
    return round(stats.fresh_entries / stats.total_entries, 4)


def _recommendations(
    album_count: int,
    scan_duration: float,
    cache_stats: CacheStats,
) -> list[str]:
    """Return deterministic benchmark recommendations."""
    recommendations: list[str] = []
    if album_count and scan_duration / album_count > 0.05:
        recommendations.append("Plex library scanning is slow; consider smaller batch limits.")
    if cache_stats.expired_entries:
        recommendations.append("Expired cache entries are present; refresh or clear stale entries.")
    if cache_stats.total_entries == 0:
        recommendations.append("Knowledge cache is empty; first large run will be slower.")
    if not recommendations:
        recommendations.append("No immediate performance issues detected.")
    return recommendations


def _memory_mb() -> float:
    """Return current process memory usage in MiB."""
    usage = getrusage(RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports KiB. The project currently targets developer desktops,
    # but this keeps CI values readable on either platform.
    return round((usage / 1024 / 1024) if usage > 10_000_000 else (usage / 1024), 2)
