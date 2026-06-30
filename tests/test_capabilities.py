"""Plex capability analyzer tests."""

from __future__ import annotations

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.plex.capabilities import PlexCapabilityAnalyzer


class FakeTrack:
    """Fake Plex track."""

    def __init__(self) -> None:
        """Create a fake track."""
        self.ratingKey = "300"
        self.title = "Sinnerman"
        self.summary = "Track summary"
        self.duration = 123000


class FakeAlbum:
    """Fake Plex album."""

    def __init__(self) -> None:
        """Create a fake album."""
        self.ratingKey = "200"
        self.title = "Pastel Blues"
        self.summary = "Album summary"
        self.year = 1965

    def edit(self, **kwargs: object) -> None:
        """Fake plexapi edit method."""


class FakeArtist:
    """Fake Plex artist."""

    def __init__(self) -> None:
        """Create a fake artist."""
        self.ratingKey = "100"
        self.title = "Nina Simone"
        self.summary = "Artist summary"
        self.guid = "plex://artist/100"

    def edit(self, **kwargs: object) -> None:
        """Fake plexapi edit method."""

    def update(self) -> None:
        """Fake plexapi update method."""


class FakeSection:
    """Fake Plex music section."""

    key = "42"
    title = "Music"
    type = "artist"
    agent = "tv.plex.agents.music"
    scanner = "Plex Music"

    def all(self) -> list[FakeArtist]:
        """Return fake artists."""
        return [FakeArtist()]

    def albums(self) -> list[FakeAlbum]:
        """Return fake albums."""
        return [FakeAlbum()]

    def searchTracks(self) -> list[FakeTrack]:  # noqa: N802
        """Return fake tracks."""
        return [FakeTrack()]


class FakeLibrary:
    """Fake Plex library accessor."""

    def sections(self) -> list[FakeSection]:
        """Return fake sections."""
        return [FakeSection()]


class FakePlexServer:
    """Fake Plex server."""

    version = "1.40.0"
    platform = "Linux"

    def __init__(self, url: str, token: str) -> None:
        """Create fake Plex server."""
        self.url = url
        self.token = token
        self.library = FakeLibrary()

    def update(self) -> None:
        """Fake server API capability."""


def test_capability_analyzer_exports_server_library_and_sample_data(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.capabilities.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexCapabilityAnalyzer(url, SecretStr("secret-token")).analyze()

    assert result.plex_server_version == "1.40.0"
    assert result.platform == "Linux"
    assert result.libraries[0].agent == "tv.plex.agents.music"
    assert result.libraries[0].scanner == "Plex Music"
    assert result.api_capabilities == ["update"]
    assert [sample.object_type for sample in result.samples] == ["artist", "album", "track"]
    artist_sample = result.samples[0]
    assert "title" in artist_sample.available_attributes
    assert "summary" in artist_sample.writable_attributes
    assert "guid" in artist_sample.read_only_attributes
    assert artist_sample.api_capabilities == ["edit", "update"]
