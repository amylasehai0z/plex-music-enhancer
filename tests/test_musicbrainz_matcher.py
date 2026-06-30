"""MusicBrainz matcher tests."""

from __future__ import annotations

from plex_music_enhancer.providers.musicbrainz import (
    MusicBrainzAlbumSearchResult,
    MusicBrainzArtistSearchResult,
)
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult, MusicBrainzMatcher


def test_matcher_returns_high_confidence_release_group_match(tmp_path) -> None:
    provider = FakeMusicBrainzProvider(
        artists=[
            MusicBrainzArtistSearchResult(
                mbid="artist-mbid",
                name="Nina Simone",
                sort_name="Simone, Nina",
                disambiguation="American singer and pianist",
                score=100,
            )
        ],
        albums=[
            MusicBrainzAlbumSearchResult(
                release_group_mbid="release-group-mbid",
                release_mbid="release-mbid",
                title="Pastel Blues",
                artist_name="Nina Simone",
                first_release_date="1965-10",
                primary_type="Album",
                score=100,
            )
        ],
    )
    matcher = MusicBrainzMatcher(provider, cache_directory=tmp_path)

    result = matcher.match_album(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        release_year=1965,
    )

    assert result == MatchResult(
        matched=True,
        confidence=100,
        artist_mbid="artist-mbid",
        release_group_mbid="release-group-mbid",
        release_mbid="release-mbid",
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        first_release_date="1965-10",
        release_year=1965,
        primary_type="Album",
        secondary_types=[],
        score_breakdown={
            "artist_candidate": 98.0,
            "artist_similarity": 100.0,
            "album_similarity": 100.0,
            "release_year": 100.0,
            "release_type": 100.0,
            "musicbrainz_score": 100.0,
        },
        warnings=[],
    )


def test_matcher_selects_artist_by_alias(tmp_path) -> None:
    provider = FakeMusicBrainzProvider(
        artists=[
            MusicBrainzArtistSearchResult(
                mbid="wrong-artist",
                name="Simone",
                disambiguation="tribute band",
                score=80,
            ),
            MusicBrainzArtistSearchResult(
                mbid="artist-mbid",
                name="Nina Simone",
                aliases=[{"name": "Eunice Kathleen Waymon"}],
                score=90,
            ),
        ],
        albums=[
            MusicBrainzAlbumSearchResult(
                release_group_mbid="release-group-mbid",
                title="Pastel Blues",
                artist_name="Nina Simone",
                first_release_date="1965",
                primary_type="Album",
                score=95,
            )
        ],
    )
    matcher = MusicBrainzMatcher(provider, cache_directory=tmp_path)

    result = matcher.match_album(
        artist_name="Eunice Kathleen Waymon",
        album_title="Pastel Blues",
        release_year=1965,
    )

    assert result.matched is True
    assert result.artist_mbid == "artist-mbid"


def test_matcher_rejects_weak_album_matches(tmp_path) -> None:
    provider = FakeMusicBrainzProvider(
        artists=[
            MusicBrainzArtistSearchResult(
                mbid="artist-mbid",
                name="Nina Simone",
                score=100,
            )
        ],
        albums=[
            MusicBrainzAlbumSearchResult(
                release_group_mbid="weak-release-group",
                title="Wild Is the Wind",
                artist_name="Nina Simone",
                first_release_date="1966",
                primary_type="Album",
                score=60,
            )
        ],
    )
    matcher = MusicBrainzMatcher(provider, cache_directory=tmp_path)

    result = matcher.match_album(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        release_year=1965,
    )

    assert result.matched is False
    assert result.release_group_mbid == "weak-release-group"
    assert result.confidence < 75
    assert "below the confidence threshold" in result.warnings[0]


def test_matcher_prefers_better_year_and_release_type(tmp_path) -> None:
    provider = FakeMusicBrainzProvider(
        artists=[
            MusicBrainzArtistSearchResult(
                mbid="artist-mbid",
                name="Nina Simone",
                score=100,
            )
        ],
        albums=[
            MusicBrainzAlbumSearchResult(
                release_group_mbid="single-mbid",
                title="Pastel Blues",
                artist_name="Nina Simone",
                first_release_date="1978",
                primary_type="Single",
                score=100,
            ),
            MusicBrainzAlbumSearchResult(
                release_group_mbid="album-mbid",
                title="Pastel Blues",
                artist_name="Nina Simone",
                first_release_date="1965-10",
                primary_type="Album",
                score=90,
            ),
        ],
    )
    matcher = MusicBrainzMatcher(provider, cache_directory=tmp_path)

    result = matcher.match_album(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        release_year=1965,
    )

    assert result.matched is True
    assert result.release_group_mbid == "album-mbid"
    assert result.score_breakdown["release_year"] == 100.0
    assert result.score_breakdown["release_type"] == 100.0


def test_matcher_uses_cache(tmp_path) -> None:
    provider = FakeMusicBrainzProvider(
        artists=[
            MusicBrainzArtistSearchResult(
                mbid="artist-mbid",
                name="Nina Simone",
                score=100,
            )
        ],
        albums=[
            MusicBrainzAlbumSearchResult(
                release_group_mbid="release-group-mbid",
                title="Pastel Blues",
                artist_name="Nina Simone",
                first_release_date="1965",
                primary_type="Album",
                score=100,
            )
        ],
    )
    matcher = MusicBrainzMatcher(provider, cache_directory=tmp_path)

    first = matcher.match_album(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        release_year=1965,
    )
    second = matcher.match_album(
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        release_year=1965,
    )

    assert second == first
    assert provider.artist_calls == 1
    assert provider.album_calls == 1


class FakeMusicBrainzProvider:
    """Fake MusicBrainz provider for matcher tests."""

    def __init__(
        self,
        *,
        artists: list[MusicBrainzArtistSearchResult],
        albums: list[MusicBrainzAlbumSearchResult],
    ) -> None:
        self._artists = artists
        self._albums = albums
        self.artist_calls = 0
        self.album_calls = 0

    def search_artist(
        self,
        name: str,
        *,
        limit: int = 5,
    ) -> list[MusicBrainzArtistSearchResult]:
        del name, limit
        self.artist_calls += 1
        return self._artists

    def search_album(
        self,
        artist: str,
        album: str,
        *,
        limit: int = 5,
    ) -> list[MusicBrainzAlbumSearchResult]:
        del artist, album, limit
        self.album_calls += 1
        return self._albums
