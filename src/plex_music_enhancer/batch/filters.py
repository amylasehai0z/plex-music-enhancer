"""Album filters for batch review."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class AlbumSummaryCandidate(Protocol):
    """Minimal album fields needed by batch filters."""

    rating_key: str
    current_summary: str | None


def is_missing_summary(candidate: AlbumSummaryCandidate) -> bool:
    """Return whether an album has no usable current summary."""
    return not (candidate.current_summary or "").strip()


def filter_album_candidates(
    candidates: Iterable[AlbumSummaryCandidate],
    *,
    missing_only: bool,
    limit: int | None,
    completed_rating_keys: set[str] | None = None,
) -> list[AlbumSummaryCandidate]:
    """Filter album candidates by summary status, resume progress, and limit."""
    completed = completed_rating_keys or set()
    filtered: list[AlbumSummaryCandidate] = []
    for candidate in candidates:
        if candidate.rating_key in completed:
            continue
        if missing_only and not is_missing_summary(candidate):
            continue

        filtered.append(candidate)
        if limit is not None and len(filtered) >= limit:
            break

    return filtered
