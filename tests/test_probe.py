"""Plex write verification probe tests."""

from __future__ import annotations

from typing import Any

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.plex.probe import TEST_SUMMARY_PREFIX, PlexWriteProbe


class FakeAlbum:
    """Fake Plex album that supports reversible summary writes."""

    def __init__(self, *, summary: str = "Album summary") -> None:
        """Create a fake album."""
        self.ratingKey = "200"
        self.title = "Pastel Blues"
        self.summary = summary
        self.calls: list[tuple[str, str | None]] = []
        self._batch_mode = False
        self._pending_summary: str | None = None

    def batchEdits(self) -> FakeAlbum:  # noqa: N802
        """Enable fake Plex batch edit mode."""
        self.calls.append(("batchEdits", None))
        self._batch_mode = True
        return self

    def editSummary(self, value: str) -> FakeAlbum:  # noqa: N802
        """Queue or update the fake summary."""
        self.calls.append(("editSummary", value))
        if self._batch_mode:
            self._pending_summary = value
        else:
            self.summary = value
        return self

    def saveEdits(self) -> None:  # noqa: N802
        """Record a fake Plex edit save."""
        if not self._batch_mode:
            raise RuntimeError("Batch editing mode not enabled. Must call batchEdits() first.")

        self.calls.append(("saveEdits", None))
        self.summary = self._pending_summary or ""
        self._pending_summary = None
        self._batch_mode = False

    def reload(self) -> FakeAlbum:
        """Return the fake album after a reload."""
        self.calls.append(("reload", None))
        return self


class FakeArtist:
    """Fake Plex artist containing albums."""

    title = "Nina Simone"

    def __init__(self, album: Any) -> None:
        """Create a fake artist."""
        self._album = album

    def albums(self) -> list[Any]:
        """Return albums for the artist."""
        return [self._album]


class FakeSection:
    """Fake Plex music library."""

    type = "artist"
    title = "Music"

    def __init__(self, album: Any) -> None:
        """Create a fake section."""
        self._album = album

    def all(self) -> list[FakeArtist]:
        """Return fake artists."""
        return [FakeArtist(self._album)]


class FakeLibrary:
    """Fake Plex library accessor."""

    def __init__(self, album: Any) -> None:
        """Create a fake library."""
        self._album = album

    def sections(self) -> list[FakeSection]:
        """Return fake sections."""
        return [FakeSection(self._album)]


class FakePlexServer:
    """Fake Plex server."""

    album: Any = FakeAlbum()

    def __init__(self, url: str, token: str) -> None:
        """Create a fake server."""
        self.url = url
        self.token = token
        self.library = FakeLibrary(self.album)

    def fetchItem(self, rating_key: str) -> Any:  # noqa: N802
        """Reload an item from the fake server."""
        assert rating_key == "200"
        return self.album


class FailingEditSummaryAlbum(FakeAlbum):
    """Fake album whose editSummary call fails."""

    def editSummary(self, value: str) -> FakeAlbum:  # noqa: N802
        """Raise from editSummary."""
        raise RuntimeError(f"server rejected editSummary({value})")


class IgnoredSummaryAlbum(FakeAlbum):
    """Fake album that accepts calls but does not persist the temporary summary."""

    def editSummary(self, value: str) -> FakeAlbum:  # noqa: N802
        """Ignore only the temporary summary write."""
        if value.startswith(f"{TEST_SUMMARY_PREFIX}_"):
            self.calls.append(("editSummary", value))
            return self

        return super().editSummary(value)

    def saveEdits(self) -> None:  # noqa: N802
        """Save only non-temporary pending summary values."""
        if self._pending_summary is None:
            self.calls.append(("saveEdits", None))
            self._batch_mode = False
            return

        super().saveEdits()


class FailingSaveEditsAlbum(FakeAlbum):
    """Fake album whose saveEdits raises if batchEdits was not called."""

    def batchEdits(self) -> FakeAlbum:  # noqa: N802
        """Pretend batchEdits is unavailable."""
        raise RuntimeError("batchEdits unavailable")


class SaveWithoutBatchAlbum(FakeAlbum):
    """Fake album used to prove saveEdits guards against missing batch mode."""

    def editSummary(self, value: str) -> FakeAlbum:  # noqa: N802
        """Record a summary without enabling batch mode."""
        self.calls.append(("editSummary", value))
        return self


def _probe() -> PlexWriteProbe:
    """Create a configured test probe."""
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")
    return PlexWriteProbe(url, SecretStr("secret-token"))


def test_write_probe_dry_run_does_not_modify_album(monkeypatch) -> None:
    album = FakeAlbum()
    FakePlexServer.album = album
    monkeypatch.setattr("plex_music_enhancer.plex.probe.PlexServer", FakePlexServer)

    report = _probe().verify_album_summary(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        execute=False,
    )

    assert report.status == "DRY_RUN"
    assert report.executed is False
    assert report.library == "Music"
    assert report.rating_key == "200"
    assert report.title == "Pastel Blues"
    assert report.current_summary == "Album summary"
    assert report.available_edit_methods == [
        "batchEdits",
        "editSummary",
        "saveEdits",
        "reload",
    ]
    assert report.edit_summary_exists is True
    assert report.original_summary_length == len("Album summary")
    assert album.summary == "Album summary"
    assert album.calls == []


def test_write_probe_execute_writes_and_restores_album_summary(monkeypatch) -> None:
    album = FakeAlbum()
    FakePlexServer.album = album
    monkeypatch.setattr("plex_music_enhancer.plex.probe.PlexServer", FakePlexServer)

    report = _probe().verify_album_summary(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        execute=True,
    )

    assert report.status == "SUCCESS"
    assert report.temporary_summary_verified is True
    assert report.original_summary_restored is True
    assert report.temporary_summary is not None
    assert report.temporary_summary.startswith(f"{TEST_SUMMARY_PREFIX}_")
    assert report.summary_after_reload == report.temporary_summary
    assert report.restore_status == "RESTORED"
    assert report.final_verification is True
    assert album.summary == "Album summary"
    assert album.calls[0][0] == "batchEdits"
    assert album.calls[1][0] == "editSummary"
    assert album.calls[1][1] is not None
    assert album.calls[1][1].startswith(f"{TEST_SUMMARY_PREFIX}_")
    assert album.calls == [
        ("batchEdits", None),
        album.calls[1],
        ("saveEdits", None),
        ("batchEdits", None),
        ("editSummary", "Album summary"),
        ("saveEdits", None),
    ]


def test_write_probe_execute_reports_read_only_when_edit_summary_raises(monkeypatch) -> None:
    album = FailingEditSummaryAlbum()
    FakePlexServer.album = album
    monkeypatch.setattr("plex_music_enhancer.plex.probe.PlexServer", FakePlexServer)

    report = _probe().verify_album_summary(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        execute=True,
    )

    assert report.status == "READ_ONLY"
    assert report.temporary_summary_verified is False
    assert report.original_summary_restored is None
    assert report.exception is not None
    assert "RuntimeError" in report.exception
    assert "server rejected editSummary" in report.exception
    assert album.summary == "Album summary"


def test_write_probe_execute_reports_failed_when_temp_summary_is_not_stored(monkeypatch) -> None:
    album = IgnoredSummaryAlbum()
    FakePlexServer.album = album
    monkeypatch.setattr("plex_music_enhancer.plex.probe.PlexServer", FakePlexServer)

    report = _probe().verify_album_summary(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        execute=True,
    )

    assert report.status == "FAILED"
    assert report.temporary_summary_verified is False
    assert report.original_summary_restored is True
    assert report.restore_status == "RESTORED"
    assert report.final_verification is True
    assert album.summary == "Album summary"
