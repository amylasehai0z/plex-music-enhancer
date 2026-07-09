"""Unified deterministic retry helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import sleep


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for transient operations."""

    attempts: int = 3
    initial_delay_seconds: float = 0.25
    backoff_factor: float = 2.0
    max_delay_seconds: float = 5.0
    retry_exceptions: tuple[type[Exception], ...] = (TimeoutError, ConnectionError, OSError)

    def delay_for(self, attempt_index: int) -> float:
        """Return bounded exponential delay for a zero-based retry attempt."""
        delay = self.initial_delay_seconds * (self.backoff_factor**attempt_index)
        return min(delay, self.max_delay_seconds)


def retry_call[ResultT](
    operation: Callable[[], ResultT],
    *,
    policy: RetryPolicy | None = None,
    on_retry: Callable[[Exception, int, float], None] | None = None,
    sleeper: Callable[[float], None] = sleep,
) -> ResultT:
    """Run an operation with exponential backoff for transient failures."""
    active_policy = policy or RetryPolicy()
    attempts = max(1, active_policy.attempts)
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            return operation()
        except active_policy.retry_exceptions as exc:
            last_error = exc
            if attempt >= attempts - 1:
                break
            delay = active_policy.delay_for(attempt)
            if on_retry is not None:
                on_retry(exc, attempt + 1, delay)
            sleeper(delay)

    if last_error is not None:
        raise last_error

    raise RuntimeError("Retry operation failed without an exception.")
