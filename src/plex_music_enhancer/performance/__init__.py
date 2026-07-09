"""Performance and scalability infrastructure."""

from plex_music_enhancer.performance.benchmark import BenchmarkReport, BenchmarkService
from plex_music_enhancer.performance.database import ProcessingDatabase, ProcessingRecord
from plex_music_enhancer.performance.incremental import (
    IncrementalProcessor,
    ProcessingFingerprint,
    build_fingerprint,
)
from plex_music_enhancer.performance.metrics import MetricsCollector, MetricsSnapshot
from plex_music_enhancer.performance.progress import ProgressSnapshot, ThroughputTracker
from plex_music_enhancer.performance.retry import RetryPolicy, retry_call
from plex_music_enhancer.performance.scheduler import (
    ProviderScheduler,
    ProviderTask,
    SchedulerResult,
)

__all__ = [
    "BenchmarkReport",
    "BenchmarkService",
    "IncrementalProcessor",
    "MetricsCollector",
    "MetricsSnapshot",
    "ProcessingDatabase",
    "ProcessingFingerprint",
    "ProcessingRecord",
    "ProgressSnapshot",
    "ProviderScheduler",
    "ProviderTask",
    "RetryPolicy",
    "SchedulerResult",
    "ThroughputTracker",
    "build_fingerprint",
    "retry_call",
]
