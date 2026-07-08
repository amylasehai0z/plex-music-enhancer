"""Album context enrichment pipeline tests."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from plex_music_enhancer.enrichment import EnrichmentPipeline, EnrichmentPipelineError
from plex_music_enhancer.providers.base import AlbumMetadata
from plex_music_enhancer.providers.musicbrainz import MusicBrainzAlbumMetadata
from plex_music_enhancer.providers.wikipedia import WikipediaSummary
from plex_music_enhancer.services import MatchResult


def test_enrichment_pipeline_collects_complete_album_context() -> None:
    """Pipeline should merge Plex, MusicBrainz, and Wikipedia metadata."""
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=FakeMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=FakeProviderManager(),
        wikipedia_provider=FakeWikipediaProvider(),
        plex_server_factory=lambda url, token: FakePlexServer(),
    )

    context = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")

    assert context.plex.rating_key == "42"
    assert context.plex.artist == "Nina Simone"
    assert context.plex.album == "Pastel Blues"
    assert context.plex.year == 1965
    assert context.plex.genres == ["Jazz", "Soul"]
    assert context.plex.styles == ["Vocal Jazz"]
    assert context.plex.moods == ["Melancholy"]
    assert context.musicbrainz.artist_mbid == "artist-mbid"
    assert context.musicbrainz.release_group_mbid == "release-group-mbid"
    assert context.musicbrainz.release_mbid == "release-mbid"
    assert context.musicbrainz.release_date == "1965-10"
    assert context.musicbrainz.genres == ["jazz"]
    assert context.musicbrainz.tags == ["blues"]
    assert context.wikipedia.language == "en"
    assert context.wikipedia.page_url == "https://en.wikipedia.org/wiki/Pastel_Blues"
    assert context.pipeline.collected_sources == ["plex", "musicbrainz", "wikipedia"]
    assert context.pipeline.missing_fields == []
    assert context.pipeline.ready_for_generation is True


def test_enrichment_pipeline_reports_missing_context() -> None:
    """Pipeline should keep partial context and mark generation as not ready."""
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=UnmatchedMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=EmptyProviderManager(),
        wikipedia_provider=EmptyWikipediaProvider(),
        plex_server_factory=lambda url, token: FakePlexServer(),
    )

    context = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")

    assert context.pipeline.collected_sources == ["plex"]
    assert "musicbrainz.release_group_mbid" in context.pipeline.missing_fields
    assert "wikipedia.extract" in context.pipeline.missing_fields
    assert "No MusicBrainz artist candidates found." in context.pipeline.warnings
    assert "Wikipedia metadata was not available." in context.pipeline.warnings
    assert context.pipeline.ready_for_generation is False


def test_enrichment_pipeline_requires_exactly_one_plex_album() -> None:
    """Pipeline should fail clearly when Plex cannot identify exactly one album."""
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=FakeMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=FakeProviderManager(),
        wikipedia_provider=FakeWikipediaProvider(),
        plex_server_factory=lambda url, token: EmptyPlexServer(),
    )

    try:
        pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")
    except EnrichmentPipelineError as exc:
        assert 'No Plex album named "Pastel Blues"' in str(exc)
    else:
        raise AssertionError("Expected EnrichmentPipelineError.")


class FakeMatcher:
    """Fake successful MusicBrainz matcher."""

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        """Return a successful match."""
        assert artist_name == "Nina Simone"
        assert album_title == "Pastel Blues"
        assert release_year == 1965
        return MatchResult(
            matched=True,
            confidence=96,
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            artist_name="Nina Simone",
            album_title="Pastel Blues",
            first_release_date="1965-10",
            release_year=1965,
        )


class UnmatchedMatcher:
    """Fake unmatched MusicBrainz matcher."""

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        """Return an unmatched result."""
        del artist_name, album_title, release_year
        return MatchResult(
            matched=False,
            confidence=0,
            warnings=["No MusicBrainz artist candidates found."],
        )


class FakeMusicBrainzProvider:
    """Fake MusicBrainz metadata provider."""

    def get_album_metadata(self, mbid: str) -> MusicBrainzAlbumMetadata:
        """Return album metadata for a release-group MBID."""
        assert mbid == "release-group-mbid"
        return MusicBrainzAlbumMetadata(
            mbid=mbid,
            title="Pastel Blues",
            artist="Nina Simone",
            year=1965,
            genres=["jazz"],
            tags=["blues"],
            release_type="Album",
        )


class FakeProviderManager:
    """Fake provider manager proving the pipeline uses the shared provider layer."""

    def get_album_metadata(self, artist: str, album: str) -> AlbumMetadata:
        """Return normalized provider metadata."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return AlbumMetadata(
            title="Pastel Blues",
            artist="Nina Simone",
            summary="Wikipedia summary",
            language="en",
            source=["wikipedia"],
            confidence=0.85,
        )


class EmptyProviderManager:
    """Provider manager with no metadata."""

    def get_album_metadata(self, artist: str, album: str) -> AlbumMetadata | None:
        """Return no metadata."""
        del artist, album
        return None


class FakeWikipediaProvider:
    """Fake detailed Wikipedia provider."""

    name = "wikipedia"

    def lookup_album(self, artist: str, album: str) -> WikipediaSummary:
        """Return detailed Wikipedia summary metadata."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return WikipediaSummary(
            title="Pastel Blues",
            page_id=123,
            language="en",
            extract="Wikipedia summary",
            url="https://en.wikipedia.org/wiki/Pastel_Blues",
            thumbnail="https://example.test/pastel.jpg",
        )


class EmptyWikipediaProvider:
    """Wikipedia provider with no match."""

    name = "wikipedia"

    def lookup_album(self, artist: str, album: str) -> None:
        """Return no Wikipedia metadata."""
        del artist, album
        return None


class FakePlexServer:
    """Fake Plex server with one music album."""

    @property
    def library(self) -> FakeLibrary:
        """Return fake Plex library."""
        return FakeLibrary([FakeSection([FakeArtist([FakeAlbum()])])])


class EmptyPlexServer:
    """Fake Plex server without matching albums."""

    @property
    def library(self) -> FakeLibrary:
        """Return empty fake Plex library."""
        return FakeLibrary([FakeSection([])])


class FakeLibrary:
    """Fake Plex library accessor."""

    def __init__(self, sections: list[Any]) -> None:
        """Create a fake library."""
        self._sections = sections

    def sections(self) -> list[Any]:
        """Return sections."""
        return self._sections


class FakeSection:
    """Fake Plex music library section."""

    type = "artist"

    def __init__(self, artists: list[Any]) -> None:
        """Create a fake section."""
        self._artists = artists

    def all(self) -> list[Any]:
        """Return artists."""
        return self._artists


class FakeArtist:
    """Fake Plex artist."""

    title = "Nina Simone"

    def __init__(self, albums: list[Any]) -> None:
        """Create a fake artist."""
        self._albums = albums

    def albums(self) -> list[Any]:
        """Return albums."""
        return self._albums


class FakeAlbum:
    """Fake Plex album."""

    def __init__(self) -> None:
        """Create a fake Plex album."""
        self.ratingKey = "42"
        self.parentTitle = "Nina Simone"
        self.title = "Pastel Blues"
        self.year = 1965
        self.summary = "Current Plex summary"
        self.genres = ["Jazz", "Soul"]
        self.styles = ["Vocal Jazz"]
        self.moods = ["Melancholy"]
