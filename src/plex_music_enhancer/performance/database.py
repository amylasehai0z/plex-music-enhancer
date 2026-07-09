"""SQLite processing-state database."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

ProcessingStatus = Literal["PENDING", "SKIPPED", "SUCCESS", "FAILED"]
DEFAULT_DATABASE_PATH = Path.home() / ".plex-enhancer" / "processing.sqlite3"


@dataclass(frozen=True)
class ProcessingRecord:
    """One persisted processing record."""

    album_identifier: str
    artist_identifier: str | None
    generation_timestamp: datetime
    provider_versions: str
    metadata_hash: str
    generation_hash: str
    quality_score: int | None
    generation_status: ProcessingStatus
    prompt_version: str | None
    model: str | None
    cache_version: str
    processing_duration_seconds: float | None
    errors: str | None


class ProcessingDatabase:
    """Persist album processing state for incremental library runs."""

    def __init__(
        self,
        path: Path = DEFAULT_DATABASE_PATH,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Create the database and schema if required."""
        self.path = path
        self.timeout_seconds = timeout_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def upsert_record(self, record: ProcessingRecord) -> None:
        """Insert or update one processing record."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO processing_records (
                    album_identifier,
                    artist_identifier,
                    generation_timestamp,
                    provider_versions,
                    metadata_hash,
                    generation_hash,
                    quality_score,
                    generation_status,
                    prompt_version,
                    model,
                    cache_version,
                    processing_duration_seconds,
                    errors
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(album_identifier) DO UPDATE SET
                    artist_identifier = excluded.artist_identifier,
                    generation_timestamp = excluded.generation_timestamp,
                    provider_versions = excluded.provider_versions,
                    metadata_hash = excluded.metadata_hash,
                    generation_hash = excluded.generation_hash,
                    quality_score = excluded.quality_score,
                    generation_status = excluded.generation_status,
                    prompt_version = excluded.prompt_version,
                    model = excluded.model,
                    cache_version = excluded.cache_version,
                    processing_duration_seconds = excluded.processing_duration_seconds,
                    errors = excluded.errors
                """,
                _record_values(record),
            )

    def get_record(self, album_identifier: str) -> ProcessingRecord | None:
        """Return one processing record by album identifier."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM processing_records WHERE album_identifier = ?",
                (album_identifier,),
            ).fetchone()
        return _record_from_row(row) if row is not None else None

    def list_records(self) -> list[ProcessingRecord]:
        """Return all processing records."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM processing_records ORDER BY generation_timestamp DESC"
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def pending_after_crash(self) -> list[ProcessingRecord]:
        """Return records that did not complete successfully."""
        return [
            record
            for record in self.list_records()
            if record.generation_status in {"PENDING", "FAILED"}
        ]

    def mark_pending(
        self,
        *,
        album_identifier: str,
        artist_identifier: str | None,
        metadata_hash: str,
        prompt_version: str | None,
        model: str | None,
    ) -> None:
        """Persist a resumable checkpoint before expensive processing starts."""
        self.upsert_record(
            ProcessingRecord(
                album_identifier=album_identifier,
                artist_identifier=artist_identifier,
                generation_timestamp=datetime.now(UTC),
                provider_versions="",
                metadata_hash=metadata_hash,
                generation_hash="",
                quality_score=None,
                generation_status="PENDING",
                prompt_version=prompt_version,
                model=model,
                cache_version="",
                processing_duration_seconds=None,
                errors=None,
            )
        )

    def _initialize(self) -> None:
        """Create the database schema."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_records (
                    album_identifier TEXT PRIMARY KEY,
                    artist_identifier TEXT,
                    generation_timestamp TEXT NOT NULL,
                    provider_versions TEXT NOT NULL,
                    metadata_hash TEXT NOT NULL,
                    generation_hash TEXT NOT NULL,
                    quality_score INTEGER,
                    generation_status TEXT NOT NULL,
                    prompt_version TEXT,
                    model TEXT,
                    cache_version TEXT NOT NULL,
                    processing_duration_seconds REAL,
                    errors TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_processing_status
                ON processing_records(generation_status)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        """Return a configured SQLite connection."""
        connection = sqlite3.connect(self.path, timeout=self.timeout_seconds)
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection


def _record_values(record: ProcessingRecord) -> tuple[object, ...]:
    """Return SQLite values for a processing record."""
    return (
        record.album_identifier,
        record.artist_identifier,
        record.generation_timestamp.isoformat(),
        record.provider_versions,
        record.metadata_hash,
        record.generation_hash,
        record.quality_score,
        record.generation_status,
        record.prompt_version,
        record.model,
        record.cache_version,
        record.processing_duration_seconds,
        record.errors,
    )


def _record_from_row(row: sqlite3.Row) -> ProcessingRecord:
    """Return a typed processing record from a SQLite row."""
    return ProcessingRecord(
        album_identifier=str(row["album_identifier"]),
        artist_identifier=row["artist_identifier"],
        generation_timestamp=datetime.fromisoformat(str(row["generation_timestamp"])),
        provider_versions=str(row["provider_versions"]),
        metadata_hash=str(row["metadata_hash"]),
        generation_hash=str(row["generation_hash"]),
        quality_score=row["quality_score"],
        generation_status=row["generation_status"],
        prompt_version=row["prompt_version"],
        model=row["model"],
        cache_version=str(row["cache_version"]),
        processing_duration_seconds=row["processing_duration_seconds"],
        errors=row["errors"],
    )


def bulk_upsert(database: ProcessingDatabase, records: Iterable[ProcessingRecord]) -> None:
    """Persist a sequence of processing records."""
    for record in records:
        database.upsert_record(record)
