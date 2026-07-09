"""Progress and throughput helpers for long-running operations."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class ProgressSnapshot:
    """Current progress for a long-running processing job."""

    completed: int
    total: int
    remaining: int
    elapsed_seconds: float
    items_per_hour: float
    eta_seconds: float | None
    current_provider: str | None = None


class ThroughputTracker:
    """Track progress, throughput and ETA."""

    def __init__(self, *, total: int) -> None:
        """Create a tracker for a known total count."""
        self.total = max(0, total)
        self.completed = 0
        self._start = perf_counter()

    def advance(self, amount: int = 1) -> None:
        """Advance completed items."""
        self.completed = min(self.total, self.completed + amount)

    def snapshot(self, *, current_provider: str | None = None) -> ProgressSnapshot:
        """Return current progress metrics."""
        elapsed = max(0.0001, perf_counter() - self._start)
        rate_per_second = self.completed / elapsed if self.completed else 0.0
        remaining = max(0, self.total - self.completed)
        eta = remaining / rate_per_second if rate_per_second else None
        return ProgressSnapshot(
            completed=self.completed,
            total=self.total,
            remaining=remaining,
            elapsed_seconds=round(elapsed, 3),
            items_per_hour=round(rate_per_second * 3600, 2),
            eta_seconds=round(eta, 2) if eta is not None else None,
            current_provider=current_provider,
        )
