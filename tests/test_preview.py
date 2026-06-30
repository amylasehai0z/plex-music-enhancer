"""Enrichment preview service tests."""

from __future__ import annotations

from typing import Any

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.services import EnrichmentPreviewService
from plex_music_enhancer.services.enrichment import (
    AlbumMetadata,
    AlbumMetadataDocument,
    MusicBrainzEnrichmentMetadata,
    PlexAlbumMetadata,
)


class FakeGenre:
    """Fake Plex genre tag."""

    def __init__(self, tag: str) -> None:
        self.tag = tag


class FakeAlbum:
    """Fake Plex album."""

    def __init__(self) -> None:
        self.title = "Pastel Blues"
        self.parentTitle = "Nina Simone"
        self.summary = "Current Plex summary"
        self.year = 1965
        self.genres = [FakeGenre("Jazz"), FakeGenre("Soul")]


class FakeArtist:
    """Fake Plex artist."""

    title = "Nina Simone"

    def albums(self) -> list[FakeAlbum]:
        """Return fake albums."""
        return [FakeAlbum()]


class FakeSection:
    """Fake Plex music section."""

    type = "artist"

    def all(self) -> list[FakeArtist]:
        """Return fake artists."""
        return [FakeArtist()]


class FakeLibrary:
    """Fake Plex library accessor."""

    def sections(self) -> list[FakeSection]:
        """Return fake sections."""
        return [FakeSection()]


class FakePlexServer:
    """Fake Plex server."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        self.library = FakeLibrary()


class FakePipeline:
    """Fake enrichment pipeline."""

    def enrich_album(
        self,
        *,
        artist: str,
        album: str,
        year: int | None = None,
        summary: str | None = None,
    ) -> AlbumMetadataDocument:
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        assert year == 1965
        assert summary == "Current Plex summary"
        return AlbumMetadataDocument(
            plex=PlexAlbumMetadata(
                artist=artist,
                album=album,
                year=year,
                summary=summary,
            ),
            musicbrainz=MusicBrainzEnrichmentMetadata(
                matched=True,
                confidence=95,
                artist_mbid="artist-mbid",
                release_group_mbid="release-group-mbid",
                release_mbid="release-mbid",
                release_date="1965-10",
                primary_type="Album",
                genres=["jazz", "soul"],
                tags=["blues"],
            ),
            metadata=AlbumMetadata(
                artist=artist,
                album=album,
                year=year,
                genres=["jazz", "soul"],
                summary=None,
                sources=["plex", "musicbrainz"],
                confidence=95,
            ),
        )


class FailingPipeline:
    """Fake failing enrichment pipeline."""

    def enrich_album(self, **kwargs: Any) -> AlbumMetadataDocument:
        """Raise a provider failure."""
        del kwargs
        raise RuntimeError("MusicBrainz unavailable")


def _service(pipeline: object) -> EnrichmentPreviewService:
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")
    return EnrichmentPreviewService(url, SecretStr("secret-token"), pipeline=pipeline)  # type: ignore[arg-type]


def test_preview_service_reads_plex_album_and_enrichment(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.services.preview.PlexServer", FakePlexServer)

    document = _service(FakePipeline()).preview_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert document.plex.title == "Pastel Blues"
    assert document.plex.artist == "Nina Simone"
    assert document.plex.current_summary == "Current Plex summary"
    assert document.plex.year == 1965
    assert document.plex.genres == ["Jazz", "Soul"]
    assert document.provider.reachable is True
    assert document.provider.match_found is True
    assert document.provider.metadata_available is True
    assert document.ready_for_ai_enrichment is True


def test_preview_service_reports_provider_failure_without_modifying_plex(monkeypatch) -> None:
    monkeypatch.setattr("plex_music_enhancer.services.preview.PlexServer", FakePlexServer)

    document = _service(FailingPipeline()).preview_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert document.provider.reachable is False
    assert document.provider.match_found is False
    assert document.provider.metadata_available is False
    assert document.provider.error == "MusicBrainz unavailable"
    assert document.ready_for_ai_enrichment is False
