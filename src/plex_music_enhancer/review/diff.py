"""Summary diff utilities."""

from __future__ import annotations

from difflib import unified_diff


def unified_summary_diff(current: str, proposed: str) -> str:
    """Return a unified diff between current and proposed summaries."""
    current_lines = _lines(current)
    proposed_lines = _lines(proposed)
    diff_lines = unified_diff(
        current_lines,
        proposed_lines,
        fromfile="current summary",
        tofile="generated summary",
        lineterm="",
    )
    return "\n".join(diff_lines)


def _lines(value: str) -> list[str]:
    """Return split lines, preserving an empty line for empty text."""
    if not value:
        return [""]

    return value.splitlines()
