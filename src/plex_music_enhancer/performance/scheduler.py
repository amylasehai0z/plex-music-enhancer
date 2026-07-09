"""Smart provider scheduling with bounded concurrency."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class ProviderTask[ResultT]:
    """One provider lookup scheduled by the enrichment pipeline."""

    name: str
    operation: Callable[[], ResultT]
    should_run: Callable[[], bool] = lambda: True
    priority: int = 100


@dataclass(frozen=True)
class SchedulerResult[ResultT]:
    """Result of one provider task."""

    name: str
    value: ResultT | None
    duration_seconds: float
    skipped: bool = False
    error: str | None = None


class ProviderScheduler:
    """Run independent provider lookups concurrently when safe."""

    def __init__(self, *, max_workers: int = 4) -> None:
        """Create a scheduler with bounded concurrency."""
        self.max_workers = max(1, max_workers)

    def run[ResultT](
        self,
        tasks: list[ProviderTask[ResultT]],
    ) -> dict[str, SchedulerResult[ResultT]]:
        """Run selected provider tasks and return keyed results."""
        ordered = sorted(tasks, key=lambda task: task.priority)
        results: dict[str, SchedulerResult[ResultT]] = {}
        runnable: list[ProviderTask[ResultT]] = []

        for task in ordered:
            if not task.should_run():
                results[task.name] = SchedulerResult(
                    name=task.name,
                    value=None,
                    duration_seconds=0.0,
                    skipped=True,
                )
                continue
            runnable.append(task)

        if not runnable:
            return results

        workers = min(self.max_workers, len(runnable))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="provider") as executor:
            futures = {executor.submit(_run_task, task): task for task in runnable}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    results[task.name] = future.result()
                except Exception as exc:  # pragma: no cover - _run_task captures normal failures.
                    results[task.name] = SchedulerResult(
                        name=task.name,
                        value=None,
                        duration_seconds=0.0,
                        error=str(exc) or exc.__class__.__name__,
                    )

        return results


def _run_task[ResultT](task: ProviderTask[ResultT]) -> SchedulerResult[ResultT]:
    """Execute one provider task and capture its duration/error."""
    start = perf_counter()
    try:
        value = task.operation()
    except Exception as exc:
        return SchedulerResult(
            name=task.name,
            value=None,
            duration_seconds=perf_counter() - start,
            error=str(exc) or exc.__class__.__name__,
        )

    return SchedulerResult(
        name=task.name,
        value=value,
        duration_seconds=perf_counter() - start,
    )
