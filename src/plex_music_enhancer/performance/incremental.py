"""Incremental processing decisions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from plex_music_enhancer.performance.database import ProcessingDatabase, ProcessingRecord


@dataclass(frozen=True)
class ProcessingFingerprint:
    """Deterministic fingerprint for one processing decision."""

    album_identifier: str
    artist_identifier: str | None
    metadata_hash: str
    generation_hash: str
    provider_versions: str
    prompt_version: str | None
    model: str | None
    cache_version: str
    quality_threshold: int | None
    configuration_hash: str


class IncrementalProcessor:
    """Decide whether one album needs regeneration."""

    def __init__(self, database: ProcessingDatabase) -> None:
        """Create an incremental processor."""
        self._database = database

    def should_process(self, fingerprint: ProcessingFingerprint) -> bool:
        """Return whether an album should be processed."""
        existing = self._database.get_record(fingerprint.album_identifier)
        if existing is None:
            return True
        if existing.generation_status != "SUCCESS":
            return True
        return not _matches(existing, fingerprint)


def build_fingerprint(
    *,
    album_identifier: str,
    artist_identifier: str | None,
    source_metadata: dict[str, Any],
    provider_versions: dict[str, str],
    prompt_version: str | None,
    model: str | None,
    cache_version: str,
    quality_threshold: int | None,
    configuration: dict[str, Any],
) -> ProcessingFingerprint:
    """Build a deterministic processing fingerprint."""
    metadata_hash = stable_hash(source_metadata)
    configuration_hash = stable_hash(configuration)
    generation_hash = stable_hash(
        {
            "metadata": metadata_hash,
            "prompt_version": prompt_version,
            "model": model,
            "quality_threshold": quality_threshold,
            "configuration": configuration_hash,
        }
    )
    return ProcessingFingerprint(
        album_identifier=album_identifier,
        artist_identifier=artist_identifier,
        metadata_hash=metadata_hash,
        generation_hash=generation_hash,
        provider_versions=stable_hash(provider_versions),
        prompt_version=prompt_version,
        model=model,
        cache_version=cache_version,
        quality_threshold=quality_threshold,
        configuration_hash=configuration_hash,
    )


def stable_hash(value: Any) -> str:
    """Return a stable hash for JSON-like values."""
    from json import dumps

    return sha256(dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _matches(record: ProcessingRecord, fingerprint: ProcessingFingerprint) -> bool:
    """Return whether a persisted record matches the current fingerprint."""
    return (
        record.metadata_hash == fingerprint.metadata_hash
        and record.generation_hash == fingerprint.generation_hash
        and record.provider_versions == fingerprint.provider_versions
        and record.prompt_version == fingerprint.prompt_version
        and record.model == fingerprint.model
        and record.cache_version == fingerprint.cache_version
    )
