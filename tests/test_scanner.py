"""Plex scanner tests."""

from __future__ import annotations

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.plex.scanner import PlexMusicScanner


class FakeTag:
    """Fake Plex tag."""

    def __init__(self, tag: str) -> None:
        """Create a fake Plex tag."""
        self.tag = tag


class FakeAlbum:
    """Fake Plex album."""

    def __init__(self) -> None:
        """Create a fake Plex album."""
        self.ratingKey = "200"
        self.title = "Pastel Blues"
        self.parentTitle = "Nina Simone"
        self.guid = "plex://album/200"
        self.year = 1965
        self.originallyAvailableAt = "1965-10-01"
        self.summary = "Album summary"
        self.genres = [FakeTag("Jazz")]
        self.styles = [FakeTag("Vocal Jazz")]
        self.moods = [FakeTag("Reflective")]
        self.leafCount = 9
        self.thumb = "/library/metadata/200/thumb"
        self.art = "/library/metadata/200/art"


class FakeArtist:
    """Fake Plex artist."""

    def __init__(self) -> None:
        """Create a fake Plex artist."""
        self.ratingKey = "100"
        self.title = "Nina Simone"
        self.guid = "plex://artist/100"
        self.summary = "Artist summary"
        self.genres = [FakeTag("Jazz"), FakeTag("Soul")]
        self.countries = [FakeTag("United States")]
        self.art = "/library/metadata/100/art"
        self.thumb = "/library/metadata/100/thumb"

    def albums(self) -> list[FakeAlbum]:
        """Return fake artist albums."""
        return [FakeAlbum(), FakeAlbum()]


class FakeSection:
    """Fake Plex library section."""

    def __init__(
        self,
        *,
        title: str,
        key: str,
        uuid: str,
        scanner: str,
        agent: str,
        section_type: str,
        artist_count: int,
        album_count: int,
        track_count: int,
    ) -> None:
        """Create a fake Plex library section."""
        self.title = title
        self.key = key
        self.uuid = uuid
        self.scanner = scanner
        self.agent = agent
        self.type = section_type
        self._artist_count = artist_count
        self._album_count = album_count
        self._track_count = track_count

    def all(self) -> list[object]:
        """Return fake artists."""
        return [FakeArtist()] * self._artist_count

    def albums(self) -> list[FakeAlbum]:
        """Return fake albums."""
        return [FakeAlbum()] * self._album_count

    def searchTracks(self) -> list[object]:  # noqa: N802
        """Return fake tracks."""
        return [object()] * self._track_count


class FakeLibrary:
    """Fake Plex library accessor."""

    def sections(self) -> list[FakeSection]:
        """Return fake Plex sections."""
        return [
            FakeSection(
                title="Music",
                key="42",
                uuid="music-uuid",
                scanner="Plex Music",
                agent="tv.plex.agents.music",
                section_type="artist",
                artist_count=3,
                album_count=7,
                track_count=99,
            ),
            FakeSection(
                title="Movies",
                key="7",
                uuid="movie-uuid",
                scanner="Plex Movie",
                agent="tv.plex.agents.movie",
                section_type="movie",
                artist_count=0,
                album_count=0,
                track_count=0,
            ),
        ]


class FakePlexServer:
    """Fake Plex server."""

    def __init__(self, url: str, token: str) -> None:
        """Create a fake Plex server."""
        self.url = url
        self.token = token
        self.library = FakeLibrary()


def test_scanner_collects_music_library_statistics(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.scanner.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexMusicScanner(url, SecretStr("secret-token")).scan()

    assert len(result.libraries) == 1
    assert result.libraries[0].library_title == "Music"
    assert result.libraries[0].library_id == "42"
    assert result.libraries[0].library_uuid == "music-uuid"
    assert result.libraries[0].scanner == "Plex Music"
    assert result.libraries[0].agent == "tv.plex.agents.music"
    assert result.libraries[0].artist_count == 3
    assert result.libraries[0].album_count == 7
    assert result.libraries[0].track_count == 99


def test_scanner_collects_artist_exports(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.scanner.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")
    seen_artists: list[str] = []

    result = PlexMusicScanner(url, SecretStr("secret-token")).scan_artists(seen_artists.append)

    assert len(result.artists) == 3
    assert seen_artists == ["Nina Simone", "Nina Simone", "Nina Simone"]
    assert result.artists[0].rating_key == "100"
    assert result.artists[0].title == "Nina Simone"
    assert result.artists[0].guid == "plex://artist/100"
    assert result.artists[0].summary == "Artist summary"
    assert result.artists[0].genres == ["Jazz", "Soul"]
    assert result.artists[0].country == "United States"
    assert result.artists[0].artwork_url == "/library/metadata/100/art"
    assert result.artists[0].thumb_url == "/library/metadata/100/thumb"
    assert result.artists[0].album_count == 2


def test_scanner_collects_album_exports(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.scanner.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexMusicScanner(url, SecretStr("secret-token")).scan_albums()

    assert len(result.albums) == 7
    assert result.albums[0].rating_key == "200"
    assert result.albums[0].title == "Pastel Blues"
    assert result.albums[0].parent_artist == "Nina Simone"
    assert result.albums[0].guid == "plex://album/200"
    assert result.albums[0].year == 1965
    assert result.albums[0].originally_available_at == "1965-10-01"
    assert result.albums[0].summary == "Album summary"
    assert result.albums[0].genres == ["Jazz"]
    assert result.albums[0].styles == ["Vocal Jazz"]
    assert result.albums[0].moods == ["Reflective"]
    assert result.albums[0].leaf_count == 9
    assert result.albums[0].thumb == "/library/metadata/200/thumb"
    assert result.albums[0].artwork == "/library/metadata/200/art"
