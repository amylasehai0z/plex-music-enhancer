"""Backup storage for Plex summary apply operations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from re import sub

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.review import ReviewDocument
from plex_music_enhancer.runtime_paths import runtime_backups_dir
from plex_music_enhancer.utils.files import write_text_atomic


class SummaryBackup(BaseModel):
    """Stored copy of the current Plex summary before applying a generated summary."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    created_at: datetime = Field(serialization_alias="createdAt")
    artist: str
    album: str
    rating_key: str = Field(serialization_alias="ratingKey")
    previous_summary: str = Field(serialization_alias="previousSummary")
    proposed_summary: str = Field(serialization_alias="proposedSummary")
    provider: str
    model: str
    source: str
    path: str


class BackupStore:
    """Persist apply backups as JSON documents."""

    def __init__(self, directory: Path | str | None = None) -> None:
        """Create a backup store."""
        self._directory = Path(directory) if directory is not None else runtime_backups_dir()

    @property
    def directory(self) -> Path:
        """Return the directory where backup records are written."""
        return self._directory

    def create_backup(self, review: ReviewDocument) -> SummaryBackup:
        """Create a backup file for the current Plex album summary."""
        now = datetime.now(tz=UTC)
        context = review.preview.context
        generated = review.preview.generated_summary
        artist = context.plex.artist
        album = getattr(context.plex, "album", "artist")
        path = self._backup_path(
            artist=artist,
            album=album,
            rating_key=context.plex.rating_key,
            created_at=now,
        )
        backup = SummaryBackup(
            created_at=now,
            artist=artist,
            album=album,
            rating_key=context.plex.rating_key,
            previous_summary=review.current_summary,
            proposed_summary=review.proposed_summary,
            provider=generated.provider,
            model=generated.model,
            source=generated.prompt_name,
            path=str(path),
        )
        write_text_atomic(path, backup.model_dump_json(indent=2, by_alias=True) + "\n")
        return backup

    def _backup_path(
        self,
        *,
        artist: str,
        album: str,
        rating_key: str,
        created_at: datetime,
    ) -> Path:
        """Return a deterministic, collision-resistant backup path."""
        timestamp = created_at.strftime("%Y%m%d%H%M%S%f")
        target = "artist" if album == "artist" else "album"
        filename = f"{target}_{_safe_segment(rating_key)}_{timestamp}.json"
        return self._directory / filename


def _safe_segment(value: str) -> str:
    """Return a filesystem-safe path segment."""
    return sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "unknown"
