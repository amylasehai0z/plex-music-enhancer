"""Audit records for Plex apply operations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from re import sub
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.runtime_paths import runtime_audit_dir
from plex_music_enhancer.utils.files import write_text_atomic

ApplyStatus = Literal["SUCCESS", "FAILED"]


class ApplyAuditRecord(BaseModel):
    """Immutable audit record for one apply attempt."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    created_at: datetime = Field(serialization_alias="createdAt")
    status: ApplyStatus
    artist: str
    album: str
    rating_key: str = Field(serialization_alias="ratingKey")
    provider: str
    model: str
    prompt_name: str = Field(serialization_alias="promptName")
    prompt_version: str = Field(serialization_alias="promptVersion")
    quality_status: str = Field(serialization_alias="qualityStatus")
    backup_path: str | None = Field(default=None, serialization_alias="backupPath")
    write_successful: bool = Field(serialization_alias="writeSuccessful")
    verification_passed: bool = Field(serialization_alias="verificationPassed")
    expected_summary: str = Field(serialization_alias="expectedSummary")
    verified_summary: str | None = Field(default=None, serialization_alias="verifiedSummary")
    message: str
    path: str


class AuditStore:
    """Persist apply audit records as JSON documents."""

    def __init__(self, directory: Path | str | None = None) -> None:
        """Create an audit store."""
        self._directory = Path(directory) if directory is not None else runtime_audit_dir()

    @property
    def directory(self) -> Path:
        """Return the directory where audit records are written."""
        return self._directory

    def create_record(
        self,
        *,
        status: ApplyStatus,
        artist: str,
        album: str,
        rating_key: str,
        provider: str,
        model: str,
        prompt_name: str,
        prompt_version: str,
        quality_status: str,
        backup_path: str | None,
        write_successful: bool,
        verification_passed: bool,
        expected_summary: str,
        verified_summary: str | None,
        message: str,
    ) -> ApplyAuditRecord:
        """Create and store an apply audit record."""
        now = datetime.now(tz=UTC)
        path = self._audit_path(
            artist=artist,
            album=album,
            rating_key=rating_key,
            created_at=now,
        )
        record = ApplyAuditRecord(
            created_at=now,
            status=status,
            artist=artist,
            album=album,
            rating_key=rating_key,
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            quality_status=quality_status,
            backup_path=backup_path,
            write_successful=write_successful,
            verification_passed=verification_passed,
            expected_summary=expected_summary,
            verified_summary=verified_summary,
            message=message,
            path=str(path),
        )
        write_text_atomic(path, record.model_dump_json(indent=2, by_alias=True) + "\n")
        return record

    def _audit_path(
        self,
        *,
        artist: str,
        album: str,
        rating_key: str,
        created_at: datetime,
    ) -> Path:
        """Return a deterministic, collision-resistant audit path."""
        timestamp = created_at.strftime("%Y%m%d%H%M%S%f")
        filename = (
            f"apply-{_safe_segment(artist)}-{_safe_segment(album)}-"
            f"{_safe_segment(rating_key)}-{timestamp}.json"
        )
        return self._directory / filename


def _safe_segment(value: str) -> str:
    """Return a filesystem-safe path segment."""
    return sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "unknown"
