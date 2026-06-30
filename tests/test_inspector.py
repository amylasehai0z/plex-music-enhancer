"""Plex metadata inspector tests."""

from __future__ import annotations

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.plex.inspector import InspectTarget, PlexMetadataInspector


class FakeMedia:
    """Fake Plex media object."""

    def __init__(self) -> None:
        """Create fake media."""
        self.audioCodec = "flac"
        self.duration = 123000


class FakeTrack:
    """Fake Plex track."""

    def __init__(self) -> None:
        """Create a fake Plex track."""
        self.ratingKey = "300"
        self.title = "Sinnerman"
        self.guid = "plex://track/300"
        self.summary = "Track summary"
        self.thumb = "/library/metadata/300/thumb"
        self.media = [FakeMedia()]


class FakeAlbum:
    """Fake Plex album."""

    def __init__(self) -> None:
        """Create a fake Plex album."""
        self.ratingKey = "200"
        self.title = "Pastel Blues"
        self.guid = "plex://album/200"
        self.art = "/library/metadata/200/art"
        self.media = [FakeMedia()]

    def tracks(self) -> list[FakeTrack]:
        """Return fake tracks."""
        return [FakeTrack()]


class FakeArtist:
    """Fake Plex artist."""

    def __init__(self) -> None:
        """Create a fake Plex artist."""
        self.ratingKey = "100"
        self.title = "Nina Simone"
        self.guid = "plex://artist/100"
        self.summary = "Artist summary"
        self.thumb = "/library/metadata/100/thumb"
        self.media = []

    def albums(self) -> list[FakeAlbum]:
        """Return fake albums."""
        return [FakeAlbum()]


class FakeSection:
    """Fake Plex library section."""

    key = "42"
    title = "Music"
    type = "artist"
    guid = "plex://library/42"
    thumb = "/library/sections/42/thumb"
    media: list[object] = []

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

    def __init__(self, url: str, token: str) -> None:
        """Create fake Plex server."""
        self.url = url
        self.token = token
        self.library = FakeLibrary()

    def fetchItem(self, key: str) -> object:  # noqa: N802
        """Return fake Plex object by key."""
        if key == "100":
            return FakeArtist()
        if key == "200":
            return FakeAlbum()
        return FakeTrack()


def test_inspector_finds_artist_by_id(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.inspector.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexMetadataInspector(url, SecretStr("secret-token")).inspect(
        InspectTarget.ARTIST,
        rating_key="100",
        name=None,
    )

    assert result.object_type == "artist"
    assert result.rating_key == "100"
    assert result.guid == "plex://artist/100"
    assert result.title == "Nina Simone"
    assert result.attributes["summary"] == "Artist summary"
    assert result.images[0].kind == "thumb"
    assert result.children[0].kind == "album"
    assert result.children[0].title == "Pastel Blues"


def test_inspector_finds_album_by_name(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.inspector.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexMetadataInspector(url, SecretStr("secret-token")).inspect(
        InspectTarget.ALBUM,
        rating_key=None,
        name="Pastel Blues",
    )

    assert result.object_type == "album"
    assert result.rating_key == "200"
    assert result.media[0]["audioCodec"] == "flac"
    assert result.children[0].kind == "track"
    assert result.children[0].title == "Sinnerman"
