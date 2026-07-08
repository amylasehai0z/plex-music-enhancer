"""Safe apply workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.apply import ApplyService, AuditStore, BackupStore
from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.review import QualityReport, ReviewDocument
from plex_music_enhancer.services import EnrichmentPreviewDocument


def test_apply_service_writes_verifies_backs_up_and_audits(tmp_path: Path) -> None:
    """A successful apply should write, verify, and store safety records."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(tmp_path=tmp_path, album=album)

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "SUCCESS"
    assert result.backup_created is True
    assert result.write_successful is True
    assert result.verification_passed is True
    assert result.audit_stored is True
    assert result.backup_path is not None
    assert result.audit_path is not None
    assert Path(result.backup_path).exists()
    assert Path(result.audit_path).exists()
    assert album.calls == ["batchEdits", "editSummary", "saveEdits", "reload"]
    assert album.summary == _german_summary()


def test_apply_service_keeps_backup_when_write_fails(tmp_path: Path) -> None:
    """A failed Plex write should keep the backup and store a failed audit."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.", fail_save=True)
    service = _apply_service(tmp_path=tmp_path, album=album)

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.backup_created is True
    assert result.write_successful is False
    assert result.verification_passed is False
    assert result.audit_stored is True
    assert result.backup_path is not None
    assert result.audit_path is not None
    assert Path(result.backup_path).exists()
    assert Path(result.audit_path).exists()
    assert "Save failed" in result.message


def test_apply_service_reports_failed_verification(tmp_path: Path) -> None:
    """A mismatched summary after reload must not be reported as success."""
    album = FakeAlbum(
        summary="Aktuelle Plex-Zusammenfassung.",
        reload_summary="Unexpected Plex summary",
    )
    service = _apply_service(tmp_path=tmp_path, album=album)

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.write_successful is True
    assert result.verification_passed is False
    assert result.verification is not None
    assert result.verification.actual_summary == "Unexpected Plex summary"
    assert "verification failed" in result.message


def test_apply_service_does_not_write_when_quality_fails(tmp_path: Path) -> None:
    """Quality failures should stop before backup or Plex mutation."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(tmp_path=tmp_path, album=album, quality_status="FAILED")

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.backup_created is False
    assert result.write_successful is False
    assert result.audit_stored is False
    assert album.calls == []


def test_backup_store_creates_backup_file(tmp_path: Path) -> None:
    """BackupStore should persist the previous summary under exports/backups style paths."""
    store = BackupStore(directory=tmp_path / "exports" / "backups")

    backup = store.create_backup(_review_document())

    path = Path(backup.path)
    assert path.exists()
    assert path.parent == tmp_path / "exports" / "backups"
    assert backup.previous_summary == "Aktuelle Plex-Zusammenfassung."
    assert '"previousSummary": "Aktuelle Plex-Zusammenfassung."' in path.read_text()


def test_audit_store_creates_audit_file(tmp_path: Path) -> None:
    """AuditStore should persist complete apply attempt records."""
    store = AuditStore(directory=tmp_path / "exports" / "audit")

    record = store.create_record(
        status="SUCCESS",
        artist="Nina Simone",
        album="Pastel Blues",
        rating_key="42",
        provider="openai",
        model="gpt-5.5",
        prompt_name="album_summary",
        prompt_version="1.0",
        quality_status="PASS",
        backup_path="exports/backups/backup.json",
        write_successful=True,
        verification_passed=True,
        expected_summary=_german_summary(),
        verified_summary=_german_summary(),
        message="Summary written and verified successfully.",
    )

    path = Path(record.path)
    assert path.exists()
    assert path.parent == tmp_path / "exports" / "audit"
    assert record.status == "SUCCESS"
    assert '"verificationPassed": true' in path.read_text()


class FakeReviewService:
    """Fake review service for apply orchestration tests."""

    def __init__(self, document: ReviewDocument) -> None:
        """Create a fake review service."""
        self._document = document

    def create_review(self, *, artist: str, album: str) -> ReviewDocument:
        """Return a fixed review document."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return self._document


class FakeAlbum:
    """Fake mutable Plex album object."""

    def __init__(
        self,
        *,
        summary: str,
        reload_summary: str | None = None,
        fail_save: bool = False,
    ) -> None:
        """Create a fake album."""
        self.summary = summary
        self.ratingKey = "42"
        self.calls: list[str] = []
        self._pending_summary: str | None = None
        self._reload_summary = reload_summary
        self._fail_save = fail_save

    def batchEdits(self) -> None:  # noqa: N802
        """Start fake batch editing."""
        self.calls.append("batchEdits")

    def editSummary(self, summary: str) -> None:  # noqa: N802
        """Set a pending fake summary."""
        self.calls.append("editSummary")
        self._pending_summary = summary

    def saveEdits(self) -> None:  # noqa: N802
        """Persist the pending fake summary."""
        self.calls.append("saveEdits")
        if self._fail_save:
            raise RuntimeError("Save failed")
        if self._pending_summary is not None:
            self.summary = self._pending_summary

    def reload(self) -> FakeAlbum:
        """Reload the fake album."""
        self.calls.append("reload")
        if self._reload_summary is not None:
            return FakeAlbum(summary=self._reload_summary)
        return self


def _apply_service(
    *,
    tmp_path: Path,
    album: FakeAlbum,
    quality_status: str = "PASS",
) -> ApplyService:
    """Create an apply service with fake dependencies."""
    return ApplyService(
        review_service=FakeReviewService(_review_document(status=quality_status)),  # type: ignore[arg-type]
        base_url="http://localhost:32400",
        token=SecretStr("secret-token"),
        backup_store=BackupStore(directory=tmp_path / "exports" / "backups"),
        audit_store=AuditStore(directory=tmp_path / "exports" / "audit"),
        album_loader=lambda rating_key: album,
    )


def _review_document(*, status: str = "PASS") -> ReviewDocument:
    """Return a review document fixture."""
    return ReviewDocument(
        preview=_preview_document(),
        current_summary="Aktuelle Plex-Zusammenfassung.",
        proposed_summary=_german_summary() if status == "PASS" else "",
        diff="--- current summary\n+++ generated summary\n",
        quality=QualityReport(
            status=status,  # type: ignore[arg-type]
            checks={
                "not_empty": status == "PASS",
                "language_is_german": status == "PASS",
                "length_in_range": status == "PASS",
                "no_markdown": True,
                "no_bullet_lists": True,
                "no_placeholder_text": True,
            },
            warnings=[],
            failures=[] if status == "PASS" else ["Summary is empty."],
            word_count=90 if status == "PASS" else 0,
        ),
    )


def _preview_document() -> EnrichmentPreviewDocument:
    """Return preview document fixture."""
    return EnrichmentPreviewDocument(
        context=_album_context(),
        rendered_prompt=RenderedPrompt(
            name="album_summary",
            version="1.0",
            rendered_text="Prompt",
            variables={"artist": "Nina Simone", "album": "Pastel Blues", "language": "de"},
            template="Template",
        ),
        generated_summary=GeneratedSummary(
            language="de",
            text=_german_summary(),
            provider="openai",
            model="gpt-5.5",
            prompt_name="album_summary",
            prompt_version="1.0",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=0.9,
            source_count=3,
            metadata={"prompt_tokens": 100, "completion_tokens": 40},
        ),
        generation_time_seconds=0.25,
    )


def _album_context() -> AlbumContext:
    """Return album context fixture."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Aktuelle Plex-Zusammenfassung.",
            genres=["Jazz", "Soul"],
            styles=[],
            moods=[],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            genres=["jazz"],
            tags=["blues"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(
            language="de",
            title="Pastel Blues",
            extract="Wikipedia summary",
            page_url="https://de.wikipedia.org/wiki/Pastel_Blues",
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )


def _german_summary() -> str:
    """Return deterministic German prose."""
    words = [
        "Das",
        "Album",
        "ist",
        "eine",
        "sachliche",
        "Sammlung",
        "verifizierbarer",
        "Angaben",
        "und",
        "beschreibt",
        "die",
        "musikalische",
        "Einordnung",
        "mit",
        "ruhigem",
        "Ton",
        "und",
        "neutraler",
        "Sprache",
    ]
    return " ".join(words[index % len(words)] for index in range(90)) + "."
