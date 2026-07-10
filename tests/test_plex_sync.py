"""Plex library synchronization tests."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr

from plex_music_enhancer.config import Settings
from plex_music_enhancer.plex.sync import PlexLibrarySyncService, PlexSyncStore


class FakeTrack:
    """Fake Plex track."""

    def __init__(self, index: int) -> None:
        """Create a fake track."""
        self.ratingKey = str(300 + index)
        self.title = f"Track {index}"
        self.grandparentTitle = "Nina Simone"
        self.parentTitle = "Pastel Blues"
        self.guid = f"plex://track/{index}"
        self.duration = 180000
        self.index = index


class FakeAlbum:
    """Fake Plex album."""

    def __init__(self) -> None:
        """Create a fake Plex album."""
        self.ratingKey = "200"
        self.title = "Pastel Blues"
        self.parentTitle = "Nina Simone"
        self.guid = "plex://album/200"
        self.year = 1965
        self.summary = "Album summary."
        self.genres = [_FakeTag("Jazz"), _FakeTag("Jazz")]
        self.thumb = "/library/metadata/200/thumb"


class FakeArtist:
    """Fake Plex artist."""

    def __init__(self) -> None:
        """Create a fake Plex artist."""
        self.ratingKey = "100"
        self.title = "Nina Simone"
        self.guid = "plex://artist/100"
        self.summary = "An influential artist biography."


class _FakeTag:
    """Fake Plex tag."""

    def __init__(self, tag: str) -> None:
        """Create a fake tag."""
        self.tag = tag


class FakeMusicSection:
    """Fake Plex music section."""

    title = "Music"
    key = "42"
    uuid = "music-uuid"
    scanner = "Plex Music"
    agent = "tv.plex.agents.music"
    type = "artist"

    def all(self) -> list[FakeArtist]:
        """Return fake artists."""
        return [FakeArtist()]

    def albums(self) -> list[FakeAlbum]:
        """Return fake albums."""
        return [FakeAlbum(), FakeAlbum()]

    def searchTracks(self) -> list[FakeTrack]:  # noqa: N802
        """Return fake tracks."""
        return [FakeTrack(1), FakeTrack(2), FakeTrack(3)]


class FakeMovieSection:
    """Fake non-music Plex section."""

    type = "movie"


class FakeLibrary:
    """Fake Plex library accessor."""

    def sections(self) -> list[object]:
        """Return fake Plex library sections."""
        return [FakeMusicSection(), FakeMovieSection()]


class FakePlexServer:
    """Fake Plex server."""

    def __init__(self, url: str, token: str) -> None:
        """Create a fake Plex server."""
        self.url = url
        self.token = token
        self.library = FakeLibrary()


class FailingPlexServer:
    """Fake failing Plex server."""

    def __init__(self, url: str, token: str) -> None:
        """Raise a Plex-like connection failure."""
        raise RuntimeError("Plex is unavailable")


def test_plex_sync_persists_music_library_snapshot(monkeypatch, tmp_path: Path) -> None:
    """Sync should collect and persist Plex artists, albums and tracks."""
    monkeypatch.setattr("plex_music_enhancer.plex.sync.PlexServer", FakePlexServer)
    service = PlexLibrarySyncService(
        settings=_settings(), store=PlexSyncStore(tmp_path / "sync.json")
    )

    status = service.sync_now()

    assert status.running is False
    assert status.progress == 100
    assert status.libraries == 1
    assert status.artists == 1
    assert status.albums == 2
    assert status.tracks == 3
    assert status.last_sync is not None

    restarted = PlexLibrarySyncService(
        settings=_settings(), store=PlexSyncStore(tmp_path / "sync.json")
    )
    persisted_status = restarted.status()
    assert persisted_status.artists == 1
    assert persisted_status.albums == 2
    assert persisted_status.tracks == 3
    snapshot = restarted.snapshot()
    assert snapshot is not None
    assert snapshot.artists[0].summary_present is True
    assert snapshot.albums[0].summary_present is True
    assert snapshot.albums[0].genres == ["Jazz"]
    assert snapshot.albums[0].cover_url == "/library/metadata/200/thumb"


def test_plex_sync_reports_failures_without_exposing_token(monkeypatch, tmp_path: Path) -> None:
    """Sync failures should be surfaced without leaking Plex credentials."""
    monkeypatch.setattr("plex_music_enhancer.plex.sync.PlexServer", FailingPlexServer)
    service = PlexLibrarySyncService(
        settings=_settings(), store=PlexSyncStore(tmp_path / "sync.json")
    )

    status = service.sync_now()

    assert status.running is False
    assert status.error == "Plex is unavailable"
    assert "secret-token" not in str(status.model_dump())
    assert not (tmp_path / "sync.json").exists()


def _settings() -> Settings:
    """Return configured fake settings."""
    return Settings(
        _env_file=None,
        plex_url="http://localhost:32400",
        plex_token=SecretStr("secret-token"),
    )
