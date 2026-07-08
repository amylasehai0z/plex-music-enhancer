"""Metadata enrichment pipeline tests."""

from __future__ import annotations

from plex_music_enhancer.providers.musicbrainz import MusicBrainzAlbumMetadata
from plex_music_enhancer.services.enrichment import MetadataEnrichmentPipeline
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult


def test_enrichment_pipeline_builds_normalized_album_metadata() -> None:
    matcher = FakeMatcher(
        MatchResult(
            matched=True,
            confidence=96,
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            artist_name="Nina Simone",
            album_title="Pastel Blues",
            first_release_date="1965-10",
            release_year=1965,
            primary_type="Album",
            secondary_types=[],
            score_breakdown={"album_similarity": 100.0},
            warnings=[],
        )
    )
    provider = FakeMusicBrainzProvider(
        MusicBrainzAlbumMetadata(
            mbid="release-group-mbid",
            title="Pastel Blues",
            artist="Nina Simone",
            year=1965,
            genres=["jazz", "soul"],
            tags=["blues"],
            release_type="Album",
        )
    )
    pipeline = MetadataEnrichmentPipeline(matcher=matcher, musicbrainz_provider=provider)

    document = pipeline.enrich_album(
        artist="Nina Simone",
        album="Pastel Blues",
        year=1965,
    )

    assert document.plex.artist == "Nina Simone"
    assert document.musicbrainz.matched is True
    assert document.musicbrainz.release_group_mbid == "release-group-mbid"
    assert document.musicbrainz.genres == ["jazz", "soul"]
    assert document.musicbrainz.tags == ["blues"]
    assert document.metadata.artist == "Nina Simone"
    assert document.metadata.album == "Pastel Blues"
    assert document.metadata.year == 1965
    assert document.metadata.genres == ["jazz", "soul"]
    assert document.metadata.summary is None
    assert document.metadata.sources == ["plex", "musicbrainz"]
    assert document.metadata.confidence == 96
    assert provider.requested_mbids == ["release-group-mbid"]


def test_enrichment_pipeline_handles_unmatched_album() -> None:
    matcher = FakeMatcher(
        MatchResult(
            matched=False,
            confidence=0,
            warnings=["No MusicBrainz release-group candidates found."],
        )
    )
    provider = FakeMusicBrainzProvider(None)
    pipeline = MetadataEnrichmentPipeline(matcher=matcher, musicbrainz_provider=provider)

    document = pipeline.enrich_album(artist="Unknown Artist", album="Unknown Album")

    assert document.musicbrainz.matched is False
    assert document.musicbrainz.warnings == ["No MusicBrainz release-group candidates found."]
    assert document.metadata.artist == "Unknown Artist"
    assert document.metadata.album == "Unknown Album"
    assert document.metadata.sources == ["plex"]
    assert provider.requested_mbids == []


class FakeMatcher:
    """Fake MusicBrainz matcher."""

    def __init__(self, result: MatchResult) -> None:
        self._result = result

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        del artist_name, album_title, release_year
        return self._result


class FakeMusicBrainzProvider:
    """Fake MusicBrainz metadata provider."""

    def __init__(self, result: MusicBrainzAlbumMetadata | None) -> None:
        self._result = result
        self.requested_mbids: list[str] = []

    def get_album_metadata(self, mbid: str) -> MusicBrainzAlbumMetadata:
        self.requested_mbids.append(mbid)
        if self._result is None:
            raise AssertionError("get_album_metadata should not be called")

        return self._result
