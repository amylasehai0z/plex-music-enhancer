"""Metadata provider tests."""

from __future__ import annotations

from collections.abc import Callable

import httpx
from pydantic import SecretStr

from plex_music_enhancer.providers import (
    AlbumMetadata,
    ArtistMetadata,
    DiscogsProvider,
    LastFMProvider,
    ProviderManager,
    WikipediaProvider,
)
from plex_music_enhancer.providers.discogs import normalize_credit_role
from plex_music_enhancer.providers.lastfm import normalize_biography, normalize_tags
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
                    "tags": [{"name": "soul"}],
                    "artist-credit": [{"name": "Nina Simone"}],
                    "label-info": [
                        {"label": {"name": "Philips Records"}, "catalog-number": "PHS 600-187"}
                    ],
                    "barcode": "123456789012",
                    "country": "US",
                    "relations": [
                        {"type": "producer", "artist": {"name": "Hal Mooney"}},
                        {"type": "producer", "artist": {"name": "Hal Mooney"}},
                        {"type": "executive producer", "artist": {"name": "Executive Example"}},
                        {"type": "composer", "artist": {"name": "Nina Simone"}},
                        {"type": "lyricist", "artist": {"name": "Oscar Brown Jr."}},
                        {"type": "arranger", "artist": {"name": "Horace Ott"}},
                        {"type": "orchestrator", "artist": {"name": "Orchestrator Example"}},
                        {"type": "conductor", "artist": {"name": "Conductor Example"}},
                        {"type": "mixing engineer", "artist": {"name": "Mix Engineer"}},
                        {"type": "mastering engineer", "artist": {"name": "Master Engineer"}},
                        {"type": "sound engineer", "artist": {"name": "Sound Engineer"}},
                        {"type": "recording studio", "place": {"name": "RCA Studio B"}},
                        {"type": "recording location", "place": {"name": "New York"}},
                        {"type": "featured artist", "artist": {"name": "Featured Example"}},
                        {"type": "guest musician", "artist": {"name": "Guest Example"}},
                        {"type": "orchestra", "artist": {"name": "Studio Orchestra"}},
                        {"type": "choir", "artist": {"name": "Session Choir"}},
                        {"type": "publisher", "label": {"name": "Publishing Example"}},
                        {"type": "certification", "label": {"name": "Gold"}},
                        {"type": "chart position", "url": {"resource": "Billboard 200 #8"}},
                    ],
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
        tags=["soul"],
        release_type="Album, Compilation",
        catalog_number="PHS 600-187",
        barcode="123456789012",
        release_country="US",
        first_release_date="1965-10",
        producers=["Hal Mooney"],
        executive_producers=["Executive Example"],
        composers=["Nina Simone"],
        lyricists=["Oscar Brown Jr."],
        arrangers=["Horace Ott"],
        orchestrators=["Orchestrator Example"],
        conductors=["Conductor Example"],
        mixing_engineers=["Mix Engineer"],
        mastering_engineers=["Master Engineer"],
        sound_engineers=["Sound Engineer"],
        labels=["Philips Records"],
        recording_locations=["New York"],
        studios=["RCA Studio B"],
        guest_musicians=["Guest Example"],
        featured_artists=["Featured Example"],
        orchestras=["Studio Orchestra"],
        choir="Session Choir",
        choirs=["Session Choir"],
        publisher="Publishing Example",
        publishers=["Publishing Example"],
        certifications=["Gold"],
        chart_positions=["Billboard 200 #8"],
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


def test_discogs_provider_looks_up_album_and_normalizes_credits(tmp_path: object) -> None:
    """Discogs album lookups should parse release details into structured credits."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/database/search":
            return httpx.Response(200, json={"results": [{"id": 123}]})
        if request.url.path == "/releases/123":
            return httpx.Response(
                200,
                json={
                    "labels": [{"name": "Philips Records", "catno": "PHS 600-187"}],
                    "country": "US",
                    "released": "1965-10",
                    "formats": [{"name": "Vinyl", "descriptions": ["LP", "Album"]}],
                    "notes": "Discogs release notes.",
                    "extraartists": [
                        {"name": "Hal Mooney", "role": "Produced By"},
                        {"name": "Engineer Example", "role": "Recording Engineer"},
                        {"name": "Master Example", "role": "Mastered By"},
                        {"name": "Mix Example", "role": "Mixed By"},
                        {"name": "Photo Example", "role": "Photography"},
                        {"name": "Design Example", "role": "Design"},
                        {"name": "Unknown Example", "role": "Liner Notes"},
                    ],
                    "tracklist": [
                        {
                            "extraartists": [
                                {"name": "Guest Example", "role": "Guest Vocals"},
                                {"name": "Guitar Example", "role": "Guitar"},
                            ]
                        }
                    ],
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    provider = DiscogsProvider(
        token=SecretStr("discogs-token"),
        http_client=_client(handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
    )

    album = provider.lookup_album("Nina Simone", "Pastel Blues")

    assert album.label == "Philips Records"
    assert album.catalog_number == "PHS 600-187"
    assert album.country == "US"
    assert album.formats == ["Vinyl, LP, Album"]
    assert album.producer == ["Hal Mooney"]
    assert album.engineer == ["Engineer Example"]
    assert album.mastering == ["Master Example"]
    assert album.mixed_by == ["Mix Example"]
    assert album.photography == ["Photo Example"]
    assert album.design == ["Design Example"]
    assert album.guest_musicians == ["Guest Example"]
    assert album.personnel == ["Guitar Example"]
    assert album.credits == ["Unknown Example (Liner Notes)"]
    assert album.notes == "Discogs release notes."
    assert requests[0].headers["user-agent"].startswith("plex-music-enhancer/")


def test_discogs_provider_looks_up_artist(tmp_path: object) -> None:
    """Discogs artist lookups should parse artist profile metadata."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/database/search":
            return httpx.Response(200, json={"results": [{"id": 456}]})
        if request.url.path == "/artists/456":
            return httpx.Response(
                200,
                json={
                    "profile": "American singer and pianist.",
                    "members": [{"name": "Nina Simone"}],
                    "aliases": [{"name": "Eunice Kathleen Waymon"}],
                    "namevariations": ["Nina Simone"],
                    "genres": ["Jazz"],
                    "styles": ["Soul-Jazz"],
                    "active_years": "1954-2003",
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    provider = DiscogsProvider(
        token=SecretStr("discogs-token"),
        http_client=_client(handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
    )

    artist = provider.lookup_artist("Nina Simone")

    assert artist.profile == "American singer and pianist."
    assert artist.aliases == ["Eunice Kathleen Waymon"]
    assert artist.genres == ["Jazz"]
    assert artist.styles == ["Soul-Jazz"]
    assert artist.active_years == "1954-2003"


def test_discogs_provider_handles_missing_results_and_api_failures(tmp_path: object) -> None:
    """Discogs provider should return empty contexts instead of raising user-facing errors."""

    def missing_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"results": []})

    def failure_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(500, json={"message": "temporary failure"})

    missing = DiscogsProvider(
        token=SecretStr("discogs-token"),
        http_client=_client(missing_handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
    )
    failing = DiscogsProvider(
        token=SecretStr("discogs-token"),
        http_client=_client(failure_handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
        retries=0,
    )

    assert missing.lookup_album("Missing", "Album").model_dump(exclude_defaults=True) == {}
    assert missing.lookup_artist("Missing").model_dump(exclude_defaults=True) == {}
    failed_album = failing.lookup_album("Nina Simone", "Pastel Blues")
    assert failed_album.model_dump(exclude_defaults=True) == {}


def test_discogs_provider_retries_rate_limits_and_uses_cache(tmp_path: object) -> None:
    """Successful Discogs lookups should retry transient responses and be cached."""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(429, json={"message": "slow down"})
        if request.url.path == "/database/search":
            return httpx.Response(200, json={"results": [{"id": 123}]})
        if request.url.path == "/releases/123":
            return httpx.Response(
                200,
                json={"labels": [{"name": "Philips Records", "catno": "PHS 600-187"}]},
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    provider = DiscogsProvider(
        token=SecretStr("discogs-token"),
        http_client=_client(handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
        retries=1,
    )

    first = provider.lookup_album("Nina Simone", "Pastel Blues")
    second = provider.lookup_album("Nina Simone", "Pastel Blues")

    assert first == second
    assert first.label == "Philips Records"
    assert request_count == 3


def test_discogs_credit_role_normalization_is_resilient() -> None:
    """Discogs role normalization should tolerate common naming differences."""
    assert normalize_credit_role("Producer") == "producer"
    assert normalize_credit_role("Produced By") == "producer"
    assert normalize_credit_role("Recording Engineer") == "engineer"
    assert normalize_credit_role("Mastered By") == "mastering"
    assert normalize_credit_role("Mixed By") == "mixed_by"
    assert normalize_credit_role("Photography") == "photography"
    assert normalize_credit_role("Artwork") == "artwork"
    assert normalize_credit_role("Design") == "design"
    assert normalize_credit_role("Liner Notes") is None


def test_lastfm_provider_looks_up_artist(tmp_path: object) -> None:
    """Last.fm artist lookups should parse biography, tags, and similar artists."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.params["method"] == "artist.getinfo"
        return httpx.Response(
            200,
            json={
                "artist": {
                    "url": "https://www.last.fm/music/Nina+Simone",
                    "stats": {"listeners": "1000", "playcount": "5000"},
                    "tags": {
                        "tag": [
                            {"name": " jazz "},
                            {"name": "Soul"},
                            {"name": "jazz"},
                            {"name": ""},
                        ]
                    },
                    "similar": {"artist": [{"name": "Billie Holiday"}]},
                    "bio": {
                        "summary": "Short <a href='https://last.fm'>bio</a>.",
                        "content": "First paragraph.<br><br>Second paragraph.",
                    },
                }
            },
        )

    provider = LastFMProvider(
        api_key=SecretStr("lastfm-key"),
        http_client=_client(handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
    )

    artist = provider.lookup_artist("Nina Simone")

    assert artist.short_biography == "Short bio."
    assert artist.biography == "First paragraph.\n\nSecond paragraph."
    assert artist.tags == ["jazz", "Soul"]
    assert artist.similar_artists == ["Billie Holiday"]
    assert artist.listeners == 1000
    assert artist.playcount == 5000
    assert artist.url == "https://www.last.fm/music/Nina+Simone"
    assert requests[0].headers["user-agent"].startswith("plex-music-enhancer/")


def test_lastfm_provider_looks_up_album(tmp_path: object) -> None:
    """Last.fm album lookups should parse wiki, tags, and community statistics."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["method"] == "album.getinfo"
        return httpx.Response(
            200,
            json={
                "album": {
                    "url": "https://www.last.fm/music/Nina+Simone/Pastel+Blues",
                    "listeners": "900",
                    "playcount": "3000",
                    "tags": {"tag": [{"name": "blues"}, {"name": "Vocal Jazz"}]},
                    "wiki": {
                        "summary": "Album <b>summary</b>.",
                        "content": "Album background.<p>Second paragraph.</p>",
                    },
                }
            },
        )

    provider = LastFMProvider(
        api_key=SecretStr("lastfm-key"),
        http_client=_client(handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
    )

    album = provider.lookup_album("Nina Simone", "Pastel Blues")

    assert album.summary == "Album summary."
    assert album.wiki == "Album background.Second paragraph."
    assert album.tags == ["blues", "Vocal Jazz"]
    assert album.listeners == 900
    assert album.playcount == 3000
    assert album.url == "https://www.last.fm/music/Nina+Simone/Pastel+Blues"


def test_lastfm_provider_handles_missing_data_and_api_failures(tmp_path: object) -> None:
    """Last.fm provider should return empty contexts for missing and failed lookups."""

    def missing_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"error": 6, "message": "not found"})

    def failure_handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(503, json={"message": "temporary failure"})

    missing = LastFMProvider(
        api_key=SecretStr("lastfm-key"),
        http_client=_client(missing_handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
    )
    failing = LastFMProvider(
        api_key=SecretStr("lastfm-key"),
        http_client=_client(failure_handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
        retries=0,
    )

    assert missing.lookup_album("Missing", "Album").model_dump(exclude_defaults=True) == {}
    assert missing.lookup_artist("Missing").model_dump(exclude_defaults=True) == {}
    failed_album = failing.lookup_album("Nina Simone", "Pastel Blues")
    assert failed_album.model_dump(exclude_defaults=True) == {}


def test_lastfm_provider_retries_rate_limits_and_uses_cache(tmp_path: object) -> None:
    """Successful Last.fm lookups should retry transient responses and be cached."""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(429, json={"message": "slow down"})
        return httpx.Response(
            200,
            json={"album": {"tags": {"tag": [{"name": "jazz"}]}, "listeners": "1"}},
        )

    provider = LastFMProvider(
        api_key=SecretStr("lastfm-key"),
        http_client=_client(handler),
        cache_directory=tmp_path,  # type: ignore[arg-type]
        rate_limit_seconds=0,
        retries=1,
    )

    first = provider.lookup_album("Nina Simone", "Pastel Blues")
    second = provider.lookup_album("Nina Simone", "Pastel Blues")

    assert first == second
    assert first.tags == ["jazz"]
    assert request_count == 2


def test_lastfm_normalization_helpers_clean_tags_and_biographies() -> None:
    """Last.fm normalization should remove duplicates, whitespace, and HTML."""
    assert normalize_tags({"tag": [{"name": " pop "}, {"name": "soft rock"}, {"name": "Pop"}]}) == [
        "pop",
        "soft rock",
    ]
    assert normalize_biography("One&nbsp;line.<br><br><a href='x'>Second</a>.") == (
        "One line.\n\nSecond."
    )


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
