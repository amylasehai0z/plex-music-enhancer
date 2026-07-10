"""Plex summary write and verification helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SUMMARY_FIELD = "summary"


class PlexWriteError(Exception):
    """Raised when a Plex summary write cannot be completed."""


class VerificationResult(BaseModel):
    """Result of reloading Plex metadata and verifying the expected summary."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    passed: bool
    expected_summary: str = Field(serialization_alias="expectedSummary")
    actual_summary: str | None = Field(serialization_alias="actualSummary")


def write_metadata_summary(item: Any, summary: str) -> None:
    """Write a Plex metadata summary through the supported plexapi edit workflow."""
    batch_edits = getattr(item, "batchEdits", None)
    edit_summary = getattr(item, "editSummary", None)
    save_edits = getattr(item, "saveEdits", None)

    if not callable(edit_summary):
        raise PlexWriteError("editSummary() is not available on this Plex metadata object.")

    if callable(batch_edits) and callable(save_edits):
        batch_edits()
        edit_summary(summary)
        save_edits()
        return

    edit_summary(summary)


def write_album_summary(album: Any, summary: str) -> None:
    """Write an album summary through the supported plexapi edit workflow."""
    write_metadata_summary(album, summary)


def verify_metadata_summary(item: Any, expected_summary: str) -> VerificationResult:
    """Reload Plex metadata and verify its summary."""
    reloaded_item = reload_metadata_item(item)
    actual_summary = _optional_string(getattr(reloaded_item, SUMMARY_FIELD, None))
    return VerificationResult(
        passed=(actual_summary or "") == expected_summary,
        expected_summary=expected_summary,
        actual_summary=actual_summary,
    )


def verify_album_summary(album: Any, expected_summary: str) -> VerificationResult:
    """Reload an album from Plex and verify its summary."""
    return verify_metadata_summary(album, expected_summary)


def reload_metadata_item(item: Any) -> Any:
    """Reload a Plex metadata object from Plex."""
    reload_method = getattr(item, "reload", None)
    if not callable(reload_method):
        raise PlexWriteError("Plex metadata could not be reloaded after writing.")

    result = reload_method()
    return item if result is None else result


def reload_album(album: Any) -> Any:
    """Reload an album object from Plex."""
    return reload_metadata_item(album)


def _optional_string(value: object) -> str | None:
    """Return a populated string value."""
    if value is None:
        return None

    text = str(value)
    return text or None
