"""Safe apply workflow tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.apply import ApplyService, AuditStore, BackupStore
from plex_music_enhancer.apply.service import (
    _PlexAlbumLoader,
    plex_metadata_path,
    plex_metadata_url,
)
from plex_music_enhancer.enrichment import (
    AlbumContext,
    ArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.quality import QualityLevel
from plex_music_enhancer.quality import QualityReport as QAReport
from plex_music_enhancer.review import QualityReport, ReviewDocument
from plex_music_enhancer.services import ArtistPreviewDocument, EnrichmentPreviewDocument


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


def test_apply_service_writes_and_verifies_artist_biography(tmp_path: Path) -> None:
    """Artist apply must write the biography to Plex and verify the reloaded artist."""
    artist_item = FakeAlbum(summary="Englische Plex-Biografie.")
    service = _apply_service(
        tmp_path=tmp_path,
        album=artist_item,
        document=_artist_review_document(),
    )

    result = service.apply_artist_summary(artist="Bonnie Tyler")

    assert result.status == "SUCCESS"
    assert result.artist == "Bonnie Tyler"
    assert result.album == "artist"
    assert result.rating_key == "100"
    assert result.write_successful is True
    assert result.verification_passed is True
    assert result.audit_stored is True
    assert artist_item.calls == ["batchEdits", "editSummary", "saveEdits", "reload"]
    assert artist_item.summary == _german_summary()


def test_apply_service_reports_failed_artist_verification(tmp_path: Path) -> None:
    """Artist apply must not report success when Plex reload keeps the old biography."""
    artist_item = FakeAlbum(
        summary="Englische Plex-Biografie.",
        reload_summary="Englische Plex-Biografie.",
    )
    service = _apply_service(
        tmp_path=tmp_path,
        album=artist_item,
        document=_artist_review_document(),
    )

    result = service.apply_artist_summary(artist="Bonnie Tyler")

    assert result.status == "FAILED"
    assert result.write_successful is True
    assert result.verification_passed is False
    assert result.verification is not None
    assert result.verification.actual_summary == "Englische Plex-Biografie."
    assert "verification failed" in result.message


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
    assert "Attempted URL: http://localhost:32400/library/metadata/42" in result.message
    assert "Underlying exception: Save failed" in result.message


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


def test_apply_service_does_not_write_when_backup_fails(tmp_path: Path) -> None:
    """Backup failures should stop before Plex mutation."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(
        tmp_path=tmp_path,
        album=album,
        backup_store=FailingBackupStore(directory=tmp_path / "exports" / "backups"),
    )

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.backup_created is False
    assert result.write_successful is False
    assert result.audit_stored is False
    assert "Plex wurde nicht geändert." in result.message
    assert "Backup konnte nicht erstellt werden" in result.message
    assert str(tmp_path / "exports" / "backups") in result.message
    assert album.calls == []


def test_apply_service_reports_audit_failure_after_write(tmp_path: Path) -> None:
    """Audit failures should return a structured failure result."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(
        tmp_path=tmp_path,
        album=album,
        audit_store=FailingAuditStore(directory=tmp_path / "exports" / "audit"),
    )

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.backup_created is True
    assert result.write_successful is True
    assert result.verification_passed is True
    assert result.audit_stored is False
    assert result.audit_path is None
    assert "Audit storage failed" in result.message


def test_apply_service_blocks_below_configured_qa_score(tmp_path: Path) -> None:
    """Configured QA thresholds should block writes before backup unless forced."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(
        tmp_path=tmp_path,
        album=album,
        minimum_quality_score=90,
        qa_score=82,
    )

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.backup_created is False
    assert "Generated summary does not yet meet the required editorial quality." in result.message
    assert album.calls == []


def test_apply_service_force_overrides_qa_threshold(tmp_path: Path) -> None:
    """Force should not override the hard v1.0.1 publishability floor."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(
        tmp_path=tmp_path,
        album=album,
        minimum_quality_score=90,
        force_quality=True,
        qa_score=82,
    )

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "FAILED"
    assert result.backup_created is False
    assert "Generated summary does not yet meet the required editorial quality." in result.message


def test_apply_service_allows_editorial_warnings_with_high_score(tmp_path: Path) -> None:
    """Editorial warnings should not block a high-scoring publishable summary."""
    album = FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")
    service = _apply_service(
        tmp_path=tmp_path,
        album=album,
        quality_status="WARNINGS",
        qa_score=91,
    )

    result = service.apply_album_summary(artist="Nina Simone", album="Pastel Blues")

    assert result.status == "SUCCESS"
    assert result.backup_created is True
    assert album.calls == ["batchEdits", "editSummary", "saveEdits", "reload"]


def test_plex_metadata_url_handles_base_without_trailing_slash() -> None:
    """Plex metadata URLs must not concatenate rating keys onto the port."""
    assert (
        plex_metadata_url("http://192.168.178.10:32400", "5069")
        == "http://192.168.178.10:32400/library/metadata/5069"
    )


def test_plex_metadata_url_handles_base_with_trailing_slash() -> None:
    """Trailing slashes in the configured Plex base URL should be harmless."""
    assert (
        plex_metadata_url("http://192.168.178.10:32400/", "5069")
        == "http://192.168.178.10:32400/library/metadata/5069"
    )


def test_plex_metadata_path_supports_album_and_artist_keys() -> None:
    """Album and artist rating keys use the same Plex metadata endpoint shape."""
    assert plex_metadata_path("5069") == "/library/metadata/5069"
    assert plex_metadata_path("100") == "/library/metadata/100"
    assert plex_metadata_path("/library/metadata/5069") == "/library/metadata/5069"


def test_plex_album_loader_fetches_metadata_path_without_trailing_slash(monkeypatch) -> None:
    """The loader should pass a proper Plex metadata path to plexapi."""
    fake_server = RecordingPlexServer()
    monkeypatch.setattr("plex_music_enhancer.apply.service.PlexServer", fake_server.factory)

    loader = _PlexAlbumLoader("http://192.168.178.10:32400", SecretStr("secret-token"))
    album = loader("5069")

    assert isinstance(album, FakeAlbum)
    assert fake_server.base_url == "http://192.168.178.10:32400"
    assert fake_server.fetched_keys == ["/library/metadata/5069"]


def test_plex_album_loader_fetches_metadata_path_with_trailing_slash(monkeypatch) -> None:
    """The loader should normalize a Plex base URL that already has a slash."""
    fake_server = RecordingPlexServer()
    monkeypatch.setattr("plex_music_enhancer.apply.service.PlexServer", fake_server.factory)

    loader = _PlexAlbumLoader("http://192.168.178.10:32400/", SecretStr("secret-token"))
    loader("5069")

    assert fake_server.base_url == "http://192.168.178.10:32400"
    assert fake_server.fetched_keys == ["/library/metadata/5069"]


def test_plex_album_loader_reports_attempted_url_and_underlying_exception(monkeypatch) -> None:
    """Malformed plexapi URL errors should include actionable diagnostics."""
    fake_server = RecordingPlexServer(fetch_error=ValueError("Failed to parse: bad-url"))
    monkeypatch.setattr("plex_music_enhancer.apply.service.PlexServer", fake_server.factory)
    loader = _PlexAlbumLoader("http://192.168.178.10:32400", SecretStr("secret-token"))

    try:
        loader("5069")
    except Exception as exc:
        message = str(exc)
    else:
        raise AssertionError("loader should raise")

    assert "Attempted URL: http://192.168.178.10:32400/library/metadata/5069" in message
    assert "Underlying exception: Failed to parse: bad-url" in message


def test_backup_store_creates_backup_file(tmp_path: Path) -> None:
    """BackupStore should persist the previous summary under exports/backups style paths."""
    store = BackupStore(directory=tmp_path / "exports" / "backups")

    backup = store.create_backup(_review_document())

    path = Path(backup.path)
    assert path.exists()
    assert path.parent == tmp_path / "exports" / "backups"
    assert backup.previous_summary == "Aktuelle Plex-Zusammenfassung."
    assert backup.proposed_summary == _german_summary()
    assert backup.source == "album_summary"
    assert '"previousSummary": "Aktuelle Plex-Zusammenfassung."' in path.read_text()


def test_backup_store_defaults_to_persistent_config_exports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Default backups must use the configured persistent runtime path, not cwd."""
    config_dir = tmp_path / "config"
    monkeypatch.setenv("PLEX_ENHANCER_CONFIG", str(config_dir))
    monkeypatch.delenv("PLEX_ENHANCER_EXPORTS", raising=False)
    store = BackupStore()

    backup = store.create_backup(_artist_review_document())

    path = Path(backup.path)
    assert path.parent == config_dir / "exports" / "backups"
    assert path.name.startswith("artist_100_")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["ratingKey"] == "100"
    assert payload["artist"] == "Bonnie Tyler"
    assert payload["previousSummary"] == "Englische Plex-Biografie."
    assert payload["proposedSummary"] == _german_summary()
    assert payload["source"] == "artist_biography"


def test_backup_store_honors_explicit_exports_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """An explicit export directory should override the config-derived default."""
    exports_dir = tmp_path / "persistent" / "exports"
    monkeypatch.setenv("PLEX_ENHANCER_CONFIG", str(tmp_path / "config"))
    monkeypatch.setenv("PLEX_ENHANCER_EXPORTS", str(exports_dir))

    backup = BackupStore().create_backup(_review_document())

    assert Path(backup.path).parent == exports_dir / "backups"


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
        assert artist in {"Nina Simone", "Bonnie Tyler"}
        assert album in {"Pastel Blues", "artist"}
        return self._document

    def create_artist_review(self, *, artist: str) -> ReviewDocument:
        """Return a fixed artist review document."""
        assert artist == "Bonnie Tyler"
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


class RecordingPlexServer:
    """Record how _PlexAlbumLoader calls plexapi."""

    def __init__(self, fetch_error: Exception | None = None) -> None:
        """Create a recording fake Plex server factory."""
        self.fetch_error = fetch_error
        self.base_url: str | None = None
        self.token: str | None = None
        self.fetched_keys: list[str] = []

    def factory(self, base_url: str, token: str) -> RecordingPlexServer:
        """Return this object like a PlexServer constructor."""
        self.base_url = base_url
        self.token = token
        return self

    def fetchItem(self, key: str) -> FakeAlbum:  # noqa: N802
        """Record the fetched key and return a fake album."""
        self.fetched_keys.append(key)
        if self.fetch_error is not None:
            raise self.fetch_error
        return FakeAlbum(summary="Aktuelle Plex-Zusammenfassung.")


class FailingBackupStore(BackupStore):
    """Backup store that fails deterministically."""

    def create_backup(self, review: ReviewDocument):
        """Raise instead of writing a backup."""
        del review
        raise OSError("disk full")


class FailingAuditStore(AuditStore):
    """Audit store that fails deterministically."""

    def create_record(self, **kwargs):  # type: ignore[no-untyped-def]
        """Raise instead of writing an audit record."""
        del kwargs
        raise OSError("audit path unavailable")


def _apply_service(
    *,
    tmp_path: Path,
    album: FakeAlbum,
    quality_status: str = "PASS",
    minimum_quality_score: int | None = None,
    force_quality: bool = False,
    qa_score: int | None = None,
    backup_store: BackupStore | None = None,
    audit_store: AuditStore | None = None,
    document: ReviewDocument | None = None,
) -> ApplyService:
    """Create an apply service with fake dependencies."""
    return ApplyService(
        review_service=FakeReviewService(
            document or _review_document(status=quality_status, qa_score=qa_score)
        ),  # type: ignore[arg-type]
        base_url="http://localhost:32400",
        token=SecretStr("secret-token"),
        backup_store=backup_store or BackupStore(directory=tmp_path / "exports" / "backups"),
        audit_store=audit_store or AuditStore(directory=tmp_path / "exports" / "audit"),
        album_loader=lambda rating_key: album,
        minimum_quality_score=minimum_quality_score,
        force_quality=force_quality,
    )


def _review_document(*, status: str = "PASS", qa_score: int | None = None) -> ReviewDocument:
    """Return a review document fixture."""
    proposed_summary = _german_summary() if status != "FAILED" else ""
    return ReviewDocument(
        preview=_preview_document(qa_score=qa_score),
        current_summary="Aktuelle Plex-Zusammenfassung.",
        proposed_summary=proposed_summary,
        diff="--- current summary\n+++ generated summary\n",
        quality=QualityReport(
            status=status,  # type: ignore[arg-type]
            checks={
                "not_empty": status != "FAILED",
                "language_is_german": status != "FAILED",
                "length_in_range": status != "WARNINGS",
                "no_markdown": True,
                "no_bullet_lists": True,
                "no_placeholder_text": True,
                "strong_opening": status != "WARNINGS",
                "natural_transitions": True,
                "varied_sentence_openings": True,
            },
            warnings=[] if status == "PASS" else ["WEAK_OPENING: Summary opens weakly."],
            failures=["Summary is empty."] if status == "FAILED" else [],
            word_count=90 if status != "FAILED" else 0,
        ),
    )


def _preview_document(*, qa_score: int | None = None) -> EnrichmentPreviewDocument:
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
        qa_report=(
            QAReport(
                overall_score=qa_score,
                quality_level=QualityLevel.FAIR,
            )
            if qa_score is not None
            else None
        ),
    )


def _artist_review_document() -> ReviewDocument:
    """Return an artist biography review document fixture."""
    return ReviewDocument(
        preview=ArtistPreviewDocument(
            context=_artist_context(),
            rendered_prompt=RenderedPrompt(
                name="artist_biography",
                version="1.0",
                rendered_text="Prompt",
                variables={"artist": "Bonnie Tyler", "language": "de"},
                template="Template",
            ),
            generated_summary=GeneratedSummary(
                language="de",
                text=_german_summary(),
                provider="openai",
                model="gpt-5.5",
                prompt_name="artist_biography",
                prompt_version="1.0",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                confidence=0.9,
                source_count=3,
                metadata={"prompt_tokens": 100, "completion_tokens": 40},
            ),
            generation_time_seconds=0.25,
        ),
        current_summary="Englische Plex-Biografie.",
        proposed_summary=_german_summary(),
        diff="--- current summary\n+++ generated summary\n",
        quality=QualityReport(
            status="PASS",
            critical_validation="PASS",
            editorial_validation="PASS",
            publishable=True,
            checks={"not_empty": True, "language_is_german": True},
            word_count=90,
        ),
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


def _artist_context() -> ArtistContext:
    """Return artist context fixture."""
    return ArtistContext(
        plex=PlexArtistContext(
            rating_key="100",
            artist="Bonnie Tyler",
            summary="Englische Plex-Biografie.",
            genres=["Pop", "Rock"],
        ),
        musicbrainz=MusicBrainzArtistContext(
            artist_mbid="artist-mbid",
            artist_name="Bonnie Tyler",
            genres=["pop", "rock"],
            confidence=96,
        ),
        wikipedia=WikipediaArtistContext(
            language="de",
            title="Bonnie Tyler",
            extract="Wikipedia biography",
            page_url="https://de.wikipedia.org/wiki/Bonnie_Tyler",
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
