"""Metadata provider tests."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from plex_music_enhancer.providers import (
    AlbumMetadata,
    ArtistMetadata,
    ProviderManager,
    WikipediaProvider,
)
from plex_music_enhancer.providers.musicbrainz import (
    MusicBrainzAlbumMetadata,
    MusicBrainzAlbumSearchResult,
    MusicBrainzArtistMetadata,
    MusicBrainzArtistSearchResult,
    MusicBrainzClient,
    MusicBrainzProvider,
)
from plex_music_enhancer.providers.wikipedia import WikipediaSummary


def test_musicbrainz_provider_searches_artists_and_albums(tmp_path: object) -> None:
    """MusicBrainz provider should parse official web service JSON responses."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/ws/2/artist":
            return httpx.Response(
                200,
                json={
                    "artists": [
                        {
                            "id": "artist-mbid",
                            "name": "Nina Simone",
                            "sort-name": "Simone, Nina",
                            "country": "US",
                            "disambiguation": "American singer and pianist",
                            "tags": [{"name": "jazz"}, {"name": "soul"}],
                            "aliases": [{"name": "Eunice Kathleen Waymon", "locale": "en"}],
                            "life-span": {"begin": "1933-02-21", "end": "2003-04-21"},
                        }
                    ]
                },
            )

        if request.url.path == "/ws/2/release-group":
            return httpx.Response(
                200,
                json={
                    "release-groups": [
                        {
                            "id": "release-group-mbid",
                            "title": "Pastel Blues",
                            "first-release-date": "1965-10",
                            "primary-type": "Album",
                            "secondary-types": ["Compilation"],
                        }
                    ]
                },
            )

        if request.url.path == "/ws/2/release":
            return httpx.Response(200, json={"releases": [{"id": "release-mbid"}]})

        raise AssertionError(f"Unexpected request: {request.url}")

    client = MusicBrainzClient(http_client=_client(handler), rate_limit_seconds=0)
    provider = MusicBrainzProvider(client=client, cache_directory=tmp_path)  # type: ignore[arg-type]

    artists = provider.search_artist("Nina Simone")
    albums = provider.search_album("Nina Simone", "Pastel Blues")

    assert artists == [
        MusicBrainzArtistSearchResult(
            mbid="artist-mbid",
            name="Nina Simone",
            sort_name="Simone, Nina",
            country="US",
            disambiguation="American singer and pianist",
            tags=["jazz", "soul"],
            aliases=[{"name": "Eunice Kathleen Waymon", "locale": "en"}],
            life_span={"begin": "1933-02-21", "end": "2003-04-21"},
        )
    ]
    assert albums == [
        MusicBrainzAlbumSearchResult(
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            title="Pastel Blues",
            first_release_date="1965-10",
            primary_type="Album",
            secondary_types=["Compilation"],
        )
    ]
    assert requests[0].headers["user-agent"].startswith("plex-music-enhancer/")


def test_musicbrainz_provider_fetches_and_caches_metadata(tmp_path: object) -> None:
    """MusicBrainz detail requests should be cached by MBID."""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request.url.path == "/ws/2/artist/artist-mbid":
            return httpx.Response(
                200,
                json={
                    "id": "artist-mbid",
                    "name": "Nina Simone",
                    "country": "US",
                    "genres": [{"name": "jazz"}],
                    "aliases": [{"name": "Eunice Kathleen Waymon"}],
                    "life-span": {"begin": "1933-02-21", "end": "2003-04-21"},
                },
            )

        raise AssertionError(f"Unexpected request: {request.url}")

    client = MusicBrainzClient(http_client=_client(handler), rate_limit_seconds=0)
    provider = MusicBrainzProvider(client=client, cache_directory=tmp_path)  # type: ignore[arg-type]

    first = provider.get_artist_metadata("artist-mbid")
    second = provider.get_artist_metadata("artist-mbid")

    assert first == MusicBrainzArtistMetadata(
        mbid="artist-mbid",
        name="Nina Simone",
        biography=None,
        country="US",
        genres=["jazz"],
        begin_date="1933-02-21",
        end_date="2003-04-21",
        aliases=[{"name": "Eunice Kathleen Waymon"}],
    )
    assert second == first
    assert request_count == 1


def test_musicbrainz_provider_fetches_album_metadata(tmp_path: object) -> None:
    """MusicBrainz provider should parse release-group metadata."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ws/2/release-group/release-group-mbid":
            return httpx.Response(
                200,
                json={
                    "id": "release-group-mbid",
                    "title": "Pastel Blues",
                    "first-release-date": "1965-10",
                    "primary-type": "Album",
                    "secondary-types": ["Compilation"],
                    "genres": [{"name": "jazz"}],
                    "artist-credit": [{"name": "Nina Simone"}],
                },
            )

        raise AssertionError(f"Unexpected request: {request.url}")

    client = MusicBrainzClient(http_client=_client(handler), rate_limit_seconds=0)
    provider = MusicBrainzProvider(client=client, cache_directory=tmp_path)  # type: ignore[arg-type]

    metadata = provider.get_album_metadata("release-group-mbid")

    assert metadata == MusicBrainzAlbumMetadata(
        mbid="release-group-mbid",
        title="Pastel Blues",
        artist="Nina Simone",
        year=1965,
        genres=["jazz"],
        release_type="Album, Compilation",
    )


def test_musicbrainz_client_retries_transient_failures() -> None:
    """MusicBrainz client should retry transient server errors."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "try again"})

        return httpx.Response(200, json={"artists": []})

    client = MusicBrainzClient(http_client=_client(handler), rate_limit_seconds=0, retries=1)

    assert client.get_json("/artist", params={"query": "artist"}) == {"artists": []}
    assert attempts == 2


def test_wikipedia_provider_prefers_german_artist_summaries(tmp_path: object) -> None:
    """Wikipedia provider should prefer German summaries when available."""

    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/w/rest.php/v1/search/title"
        ):
            return httpx.Response(200, json={"pages": [{"title": "Nina Simone"}]})

        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/api/rest_v1/page/summary/Nina Simone"
        ):
            return httpx.Response(
                200,
                json={
                    "title": "Nina Simone",
                    "pageid": 123,
                    "extract": "Nina Simone war eine US-amerikanische Saengerin.",
                    "lang": "de",
                    "content_urls": {
                        "desktop": {"page": "https://de.wikipedia.org/wiki/Nina_Simone"}
                    },
                    "thumbnail": {"source": "https://example.test/nina.jpg"},
                },
            )

        raise AssertionError(f"Unexpected request: {request.url}")

    provider = WikipediaProvider(client=_client(handler), cache_directory=tmp_path)  # type: ignore[arg-type]

    summary = provider.lookup_artist("Nina Simone")
    metadata = provider.get_artist_summary("Nina Simone")

    assert summary == WikipediaSummary(
        title="Nina Simone",
        page_id=123,
        language="de",
        extract="Nina Simone war eine US-amerikanische Saengerin.",
        url="https://de.wikipedia.org/wiki/Nina_Simone",
        thumbnail="https://example.test/nina.jpg",
    )
    assert metadata == ArtistMetadata(
        title="Nina Simone",
        artist="Nina Simone",
        summary="Nina Simone war eine US-amerikanische Saengerin.",
        language="de",
        source=["wikipedia"],
        confidence=0.85,
    )


def test_wikipedia_provider_falls_back_to_english_album_summaries(tmp_path: object) -> None:
    """Wikipedia provider should fall back to English when German has no article."""

    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/w/rest.php/v1/search/title"
        ):
            return httpx.Response(200, json={"pages": []})

        if (
            request.url.host == "en.wikipedia.org"
            and request.url.path == "/w/rest.php/v1/search/title"
        ):
            return httpx.Response(200, json={"pages": [{"title": "Pastel Blues"}]})

        if (
            request.url.host == "en.wikipedia.org"
            and request.url.path == "/api/rest_v1/page/summary/Pastel Blues"
        ):
            return httpx.Response(
                200,
                json={
                    "title": "Pastel Blues",
                    "pageid": 456,
                    "extract": "Pastel Blues is a studio album by Nina Simone.",
                    "lang": "en",
                    "content_urls": {
                        "desktop": {"page": "https://en.wikipedia.org/wiki/Pastel_Blues"}
                    },
                },
            )

        raise AssertionError(f"Unexpected request: {request.url}")

    provider = WikipediaProvider(client=_client(handler), cache_directory=tmp_path)  # type: ignore[arg-type]

    summary = provider.lookup_album("Nina Simone", "Pastel Blues")
    metadata = provider.get_album_summary("Nina Simone", "Pastel Blues")

    assert summary == WikipediaSummary(
        title="Pastel Blues",
        page_id=456,
        language="en",
        extract="Pastel Blues is a studio album by Nina Simone.",
        url="https://en.wikipedia.org/wiki/Pastel_Blues",
        thumbnail=None,
    )
    assert metadata == AlbumMetadata(
        title="Pastel Blues",
        artist="Nina Simone",
        summary="Pastel Blues is a studio album by Nina Simone.",
        language="en",
        source=["wikipedia"],
        confidence=0.85,
    )


def test_wikipedia_provider_uses_cache_for_repeated_lookups(tmp_path: object) -> None:
    """Wikipedia summaries should be cached for repeated provider lookups."""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/w/rest.php/v1/search/title"
        ):
            return httpx.Response(200, json={"pages": [{"title": "Nina Simone"}]})

        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/api/rest_v1/page/summary/Nina Simone"
        ):
            return httpx.Response(
                200,
                json={
                    "title": "Nina Simone",
                    "pageid": 123,
                    "extract": "Nina Simone war eine US-amerikanische Saengerin.",
                    "lang": "de",
                },
            )

        raise AssertionError(f"Unexpected request: {request.url}")

    provider = WikipediaProvider(client=_client(handler), cache_directory=tmp_path)  # type: ignore[arg-type]

    first = provider.lookup_artist("Nina Simone")
    second = provider.lookup_artist("Nina Simone")

    assert second == first
    assert request_count == 2


def test_wikipedia_provider_integrates_with_provider_manager(tmp_path: object) -> None:
    """Provider manager should consume Wikipedia summaries through the common interface."""

    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/w/rest.php/v1/search/title"
        ):
            return httpx.Response(200, json={"pages": [{"title": "Nina Simone"}]})

        if (
            request.url.host == "de.wikipedia.org"
            and request.url.path == "/api/rest_v1/page/summary/Nina Simone"
        ):
            return httpx.Response(
                200,
                json={
                    "title": "Nina Simone",
                    "extract": "Nina Simone war eine US-amerikanische Saengerin.",
                    "lang": "de",
                },
            )

        raise AssertionError(f"Unexpected request: {request.url}")

    manager = ProviderManager(
        [WikipediaProvider(client=_client(handler), cache_directory=tmp_path)]  # type: ignore[arg-type]
    )

    metadata = manager.get_artist_metadata("Nina Simone")

    assert metadata == ArtistMetadata(
        title="Nina Simone",
        artist="Nina Simone",
        summary="Nina Simone war eine US-amerikanische Saengerin.",
        language="de",
        source=["wikipedia"],
        confidence=0.85,
    )


def test_provider_manager_merges_metadata_with_source_attribution() -> None:
    """Provider manager should preserve provider order and combine sources."""
    manager = ProviderManager(
        [
            FakeProvider(
                artist_result=ArtistMetadata(
                    title="Nina Simone",
                    artist="Nina Simone",
                    summary=None,
                    language=None,
                    source=["musicbrainz"],
                    confidence=0.95,
                ),
                album_result=AlbumMetadata(
                    title="Pastel Blues",
                    artist="Nina Simone",
                    summary=None,
                    language=None,
                    source=["musicbrainz"],
                    confidence=0.98,
                ),
            ),
            FakeProvider(
                artist_result=ArtistMetadata(
                    title="Nina Simone",
                    artist="Nina Simone",
                    summary="Artist summary",
                    language="en",
                    source=["wikipedia"],
                    confidence=0.85,
                ),
                album_result=AlbumMetadata(
                    title="Pastel Blues",
                    artist="Nina Simone",
                    summary="Album summary",
                    language="en",
                    source=["wikipedia"],
                    confidence=0.85,
                ),
            ),
        ]
    )

    artist = manager.get_artist_metadata("Nina Simone")
    album = manager.get_album_metadata("Nina Simone", "Pastel Blues")

    assert artist.summary == "Artist summary"
    assert artist.source == ["musicbrainz", "wikipedia"]
    assert artist.confidence == 0.95
    assert album.summary == "Album summary"
    assert album.source == ["musicbrainz", "wikipedia"]
    assert album.confidence == 0.98


class FakeProvider:
    """Fake provider for manager tests."""

    name = "fake"

    def __init__(
        self,
        *,
        artist_result: ArtistMetadata | None,
        album_result: AlbumMetadata | None,
    ) -> None:
        """Create a fake provider."""
        self._artist_result = artist_result
        self._album_result = album_result

    def search_artist(self, artist: str, *, limit: int = 5) -> list[ArtistMetadata]:
        """Return no search fallbacks."""
        del artist, limit
        return []

    def search_album(self, artist: str, album: str, *, limit: int = 5) -> list[AlbumMetadata]:
        """Return no search fallbacks."""
        del artist, album, limit
        return []

    def get_artist_summary(self, artist: str, *, language: str = "en") -> ArtistMetadata | None:
        """Return fake artist metadata."""
        del artist, language
        return self._artist_result

    def get_album_summary(
        self,
        artist: str,
        album: str,
        *,
        language: str = "en",
    ) -> AlbumMetadata | None:
        """Return fake album metadata."""
        del artist, album, language
        return self._album_result


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    """Create an HTTPX client with a mock transport."""
    return httpx.Client(transport=httpx.MockTransport(handler))
