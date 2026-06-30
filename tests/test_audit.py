"""Plex metadata audit tests."""

from __future__ import annotations

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.plex.audit import (
    PlexMetadataAuditor,
    SummaryLanguage,
    SummaryPresence,
)


class FakeArtist:
    """Fake Plex artist."""

    def __init__(self, rating_key: str, title: str, summary: str | None) -> None:
        """Create a fake artist."""
        self.ratingKey = rating_key
        self.title = title
        self.summary = summary


class FakeAlbum:
    """Fake Plex album."""

    def __init__(
        self,
        rating_key: str,
        title: str,
        parent_title: str,
        summary: str | None,
    ) -> None:
        """Create a fake album."""
        self.ratingKey = rating_key
        self.title = title
        self.parentTitle = parent_title
        self.summary = summary


class FakeSection:
    """Fake Plex music library."""

    key = "42"
    title = "Music"
    type = "artist"

    def all(self) -> list[FakeArtist]:
        """Return fake artists."""
        return [
            FakeArtist("100", "Nina Simone", "The artist was an American singer."),
            FakeArtist("101", "Missing Artist", None),
        ]

    def albums(self) -> list[FakeAlbum]:
        """Return fake albums."""
        return [
            FakeAlbum("200", "English Album", "Nina Simone", "The album was recorded in 1965."),
            FakeAlbum(
                "201", "German Album", "Nina Simone", "Das Album wurde in Berlin aufgenommen."
            ),
            FakeAlbum("202", "Missing Album", "Nina Simone", ""),
        ]


class FakeLibrary:
    """Fake Plex library accessor."""

    def sections(self) -> list[FakeSection]:
        """Return fake sections."""
        return [FakeSection()]


class FakePlexServer:
    """Fake Plex server."""

    def __init__(self, url: str, token: str) -> None:
        """Create fake server."""
        self.url = url
        self.token = token
        self.library = FakeLibrary()


def test_metadata_auditor_collects_library_statistics(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.plex.audit.PlexServer", FakePlexServer)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    report = PlexMetadataAuditor(url, SecretStr("secret-token")).audit()

    assert report.statistics.artist_total == 2
    assert report.statistics.artist_biography_present == 1
    assert report.statistics.artist_biography_missing == 1
    assert report.statistics.album_total == 3
    assert report.statistics.album_summary_present == 2
    assert report.statistics.album_summary_missing == 1
    assert report.statistics.languages == {"german": 1, "english": 1, "other": 0}
    assert report.artists[0].biography == SummaryPresence.PRESENT
    assert report.artists[1].biography == SummaryPresence.MISSING
    assert report.albums[0].language == SummaryLanguage.ENGLISH
    assert report.albums[1].language == SummaryLanguage.GERMAN
    assert report.albums[2].language == SummaryLanguage.UNKNOWN
