"""Progress persistence for batch review jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from re import sub

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.utils.files import write_text_atomic


class BatchJobProgress(BaseModel):
    """Persistent progress for one batch review job."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    job_id: str = Field(alias="jobId", serialization_alias="jobId")
    created_at: datetime = Field(alias="createdAt", serialization_alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt", serialization_alias="updatedAt")
    library: str | None = None
    missing_only: bool = Field(alias="missingOnly", serialization_alias="missingOnly")
    completed_rating_keys: list[str] = Field(
        default_factory=list,
        alias="completedRatingKeys",
        serialization_alias="completedRatingKeys",
    )

    def mark_completed(self, rating_key: str) -> BatchJobProgress:
        """Return progress with a completed rating key recorded."""
        completed = list(dict.fromkeys([*self.completed_rating_keys, rating_key]))
        return self.model_copy(
            update={
                "updated_at": datetime.now(tz=UTC),
                "completed_rating_keys": completed,
            }
        )


class BatchProgressStore:
    """Load and store batch review progress files."""

    def __init__(self, directory: Path | str = Path("exports/jobs")) -> None:
        """Create a progress store."""
        self._directory = Path(directory)

    def path_for(self, *, library: str | None, missing_only: bool) -> Path:
        """Return the stable progress path for a batch review selection."""
        filter_name = "missing" if missing_only else "all"
        filename = f"batch-review-{_safe_segment(library or 'all')}-{filter_name}.json"
        return self._directory / filename

    def load_or_create(
        self,
        *,
        library: str | None,
        missing_only: bool,
        resume: bool,
    ) -> BatchJobProgress:
        """Load resumable progress or create a fresh job."""
        path = self.path_for(library=library, missing_only=missing_only)
        if resume and path.exists():
            return BatchJobProgress.model_validate_json(path.read_text(encoding="utf-8"))

        now = datetime.now(tz=UTC)
        return BatchJobProgress(
            job_id=path.stem,
            created_at=now,
            updated_at=now,
            library=library,
            missing_only=missing_only,
        )

    def save(self, progress: BatchJobProgress) -> Path:
        """Persist progress and return the written path."""
        path = self.path_for(library=progress.library, missing_only=progress.missing_only)
        write_text_atomic(path, progress.model_dump_json(indent=2, by_alias=True) + "\n")
        return path


def _safe_segment(value: str) -> str:
    """Return a filesystem-safe path segment."""
    return sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "unknown"
