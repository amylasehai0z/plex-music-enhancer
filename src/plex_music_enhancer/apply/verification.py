"""Plex summary write and verification helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SUMMARY_FIELD = "summary"


class PlexWriteError(Exception):
    """Raised when a Plex summary write cannot be completed."""


class VerificationResult(BaseModel):
    """Result of reloading an album and verifying the expected summary."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    passed: bool
    expected_summary: str = Field(serialization_alias="expectedSummary")
    actual_summary: str | None = Field(serialization_alias="actualSummary")


def write_album_summary(album: Any, summary: str) -> None:
    """Write an album summary through the supported plexapi batch edit workflow."""
    batch_edits = getattr(album, "batchEdits", None)
    edit_summary = getattr(album, "editSummary", None)
    save_edits = getattr(album, "saveEdits", None)

    if not callable(batch_edits):
        raise PlexWriteError("album.batchEdits() is not available on this Plex album object.")
    if not callable(edit_summary):
        raise PlexWriteError("album.editSummary() is not available on this Plex album object.")
    if not callable(save_edits):
        raise PlexWriteError("album.saveEdits() is not available on this Plex album object.")

    batch_edits()
    edit_summary(summary)
    save_edits()


def verify_album_summary(album: Any, expected_summary: str) -> VerificationResult:
    """Reload an album from Plex and verify its summary."""
    reloaded_album = reload_album(album)
    actual_summary = _optional_string(getattr(reloaded_album, SUMMARY_FIELD, None))
    return VerificationResult(
        passed=(actual_summary or "") == expected_summary,
        expected_summary=expected_summary,
        actual_summary=actual_summary,
    )


def reload_album(album: Any) -> Any:
    """Reload an album object from Plex."""
    reload_method = getattr(album, "reload", None)
    if not callable(reload_method):
        raise PlexWriteError("Album could not be reloaded from Plex after writing.")

    result = reload_method()
    return album if result is None else result


def _optional_string(value: object) -> str | None:
    """Return a populated string value."""
    if value is None:
        return None

    text = str(value)
    return text or None
