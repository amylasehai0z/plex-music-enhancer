"""Operational metrics collection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field


class MetricsSnapshot(BaseModel):
    """Serializable performance metrics snapshot."""

    model_config = ConfigDict(frozen=True)

    counters: dict[str, int] = Field(default_factory=dict)
    timings: dict[str, list[float]] = Field(default_factory=dict)
    averages: dict[str, float] = Field(default_factory=dict)
    cache_hit_rate: float | None = None


class MetricsCollector:
    """Collect counters and latency samples."""

    def __init__(self) -> None:
        """Create an empty metrics collector."""
        self._counters: dict[str, int] = defaultdict(int)
        self._timings: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, amount: int = 1) -> None:
        """Increment a named counter."""
        self._counters[name] += amount

    def observe(self, name: str, duration_seconds: float) -> None:
        """Record one latency sample."""
        self._timings[name].append(duration_seconds)

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        """Measure a block duration."""
        start = perf_counter()
        try:
            yield
        finally:
            self.observe(name, perf_counter() - start)

    def snapshot(self) -> MetricsSnapshot:
        """Return a serializable snapshot."""
        timings = {name: list(values) for name, values in self._timings.items()}
        averages = {
            name: round(sum(values) / len(values), 4) for name, values in timings.items() if values
        }
        hits = self._counters.get("cache_hits", 0)
        misses = self._counters.get("cache_misses", 0)
        total_cache = hits + misses
        return MetricsSnapshot(
            counters=dict(self._counters),
            timings=timings,
            averages=averages,
            cache_hit_rate=round(hits / total_cache, 4) if total_cache else None,
        )
