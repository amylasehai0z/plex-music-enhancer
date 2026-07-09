"""Album context enrichment pipeline tests."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from plex_music_enhancer.cache import KnowledgeCacheService
from plex_music_enhancer.cache.store import KnowledgeCacheStore
from plex_music_enhancer.enrichment import EnrichmentPipeline, EnrichmentPipelineError
from plex_music_enhancer.enrichment.models import (
    DiscogsAlbumContext,
    DiscogsArtistContext,
    LastFMAlbumContext,
    LastFMArtistContext,
)
from plex_music_enhancer.knowledge import KnowledgeRelationType
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
        discogs_provider=FakeDiscogsProvider(),
        lastfm_provider=FakeLastFMProvider(),
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
    assert context.producer == "Hal Mooney"
    assert context.producers == ["Hal Mooney", "Discogs Producer"]
    assert context.composers == ["Nina Simone"]
    assert context.lyricists == ["Oscar Brown Jr."]
    assert context.label == "Philips Records"
    assert context.labels == ["Philips Records", "Discogs Label"]
    assert context.catalog_number == "PHS 600-187"
    assert context.barcode == "123456789012"
    assert context.release_country == "US"
    assert context.first_release_date == "1965-10"
    assert context.recording_period == "1964-1965"
    assert context.recording_location == "New York"
    assert context.studio == "RCA Studio B"
    assert context.studios == ["RCA Studio B"]
    assert context.genres == ["jazz", "Soul"]
    assert context.secondary_genres == ["vocal jazz"]
    assert context.tags == ["blues", "Vinyl, LP"]
    assert context.release_date == "1965-10"
    assert context.chart_positions == ["Billboard 200 #8"]
    assert context.certifications == ["Gold"]
    assert context.notable_singles == ["Sinnerman"]
    assert context.guest_musicians == ["Guitarist Example", "Discogs Guest"]
    assert context.executive_producers == ["Executive Example"]
    assert context.arrangers == ["Horace Ott"]
    assert context.orchestrators == ["Orchestrator Example"]
    assert context.conductors == ["Conductor Example"]
    assert context.mixing_engineers == ["Mix Engineer", "Discogs Mixer"]
    assert context.mastering_engineers == ["Master Engineer", "Discogs Mastering"]
    assert context.sound_engineers == ["Sound Engineer", "Discogs Engineer"]
    assert context.featured_artists == ["Featured Example", "Discogs Guitarist"]
    assert context.orchestra == "Studio Orchestra"
    assert context.choir == "Session Choir"
    assert context.publisher == "Publishing Example"
    assert context.artist_history == "American singer, pianist, and civil rights artist."
    assert context.career_phase == "mature phase"
    assert context.discography_position == "2. studio album in available discography"
    assert context.album_sequence_number == 2
    assert context.previous_album == "I Put a Spell on You"
    assert context.previous_album_year == 1965
    assert context.next_album == "Let It All Out"
    assert context.next_album_year == 1966
    assert context.years_active == "1954-2003"
    assert context.current_lineup == ["Nina Simone"]
    assert context.lineup_changes == "Solo artist with changing studio ensembles."
    assert context.commercial_peak == "Mid-1960s Philips period"
    assert (
        context.genre_evolution == "Continued the move from jazz standards toward blues and soul."
    )
    assert context.major_influences == ["jazz", "blues", "gospel"]
    assert context.historical_context == "Recorded during Simone's Philips Records period."
    assert context.is_debut_album is False
    assert context.is_final_album is False
    assert context.is_live_album is False
    assert context.is_compilation is False
    assert context.is_soundtrack is False
    assert context.track_count == 3
    assert context.total_duration == "15:00"
    assert context.opening_track == "Be My Husband"
    assert context.closing_track == "Sinnerman"
    assert context.longest_track == "Sinnerman"
    assert context.shortest_track == "Be My Husband"
    assert context.instrumental_tracks == ["Chilly Winds Don't Blow"]
    assert context.cover_versions == ["Strange Fruit"]
    assert context.notable_tracks == ["Sinnerman", "Strange Fruit"]
    assert context.singles == ["Sinnerman"]
    assert context.hit_singles == ["Sinnerman"]
    assert context.promotional_singles == ["Chilly Winds Don't Blow"]
    assert context.concept_album is True
    assert context.continuous_mix is False
    assert context.album_highlights == ["Extended performance of Sinnerman"]
    assert context.signature_song == "Sinnerman"
    assert context.best_known_song == "Sinnerman"
    assert context.stylistic_highlights == ["blues-gospel intensity"]
    assert context.experimental_elements == ["long-form closing track"]
    assert context.recurring_themes == ["spiritual tension", "civil rights-era unease"]
    assert context.critical_consensus == "Often praised for its intensity and range."
    assert context.commercial_summary == "Includes one of Simone's best-known recordings."
    assert context.legacy_summary == "Sinnerman later became one of Simone's signature recordings."
    assert context.discogs.label == "Discogs Label"
    assert context.discogs.catalog_number == "DG-001"
    assert context.discogs.producer == ["Discogs Producer"]
    assert context.discogs.engineer == ["Discogs Engineer"]
    assert context.discogs.mastering == ["Discogs Mastering"]
    assert context.discogs.mixed_by == ["Discogs Mixer"]
    assert context.discogs.personnel == ["Discogs Guitarist"]
    assert context.discogs.notes == "Discogs release notes."
    assert context.lastfm.summary == "Last.fm album summary."
    assert context.lastfm.tags == ["vocal jazz", "soul"]
    assert context.lastfm.listeners == 1234
    assert context.lastfm_artist.biography == "Last.fm artist biography."
    assert context.lastfm_artist.tags == ["jazz singer"]
    assert context.lastfm_artist.similar_artists == ["Billie Holiday"]
    assert any(
        relation.type == KnowledgeRelationType.ALBUM_PRODUCER
        for relation in context.knowledge_graph.relations
    )
    assert "Career phase: mature phase; 2. studio album in available discography." in (
        context.knowledge_graph.summaries
    )
    assert context.wikipedia.language == "en"
    assert context.wikipedia.page_url == "https://en.wikipedia.org/wiki/Pastel_Blues"
    assert context.pipeline.collected_sources == [
        "plex",
        "musicbrainz",
        "wikipedia",
        "discogs",
        "lastfm",
    ]
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
        discogs_provider=DisabledDiscogsProvider(),
        lastfm_provider=DisabledLastFMProvider(),
        plex_server_factory=lambda url, token: FakePlexServer(),
    )

    context = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")

    assert context.pipeline.collected_sources == ["plex"]
    assert "musicbrainz.release_group_mbid" in context.pipeline.missing_fields
    assert "wikipedia.extract" in context.pipeline.missing_fields
    assert "No MusicBrainz artist candidates found." in context.pipeline.warnings
    assert "Wikipedia metadata was not available." in context.pipeline.warnings
    assert context.pipeline.ready_for_generation is False


def test_enrichment_pipeline_does_not_duplicate_successful_wikipedia_lookup() -> None:
    """Detailed Wikipedia results should avoid a second provider-manager lookup."""
    provider_manager = CountingProviderManager()
    wikipedia_provider = CountingWikipediaProvider()
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=FakeMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=provider_manager,
        wikipedia_provider=wikipedia_provider,
        discogs_provider=DisabledDiscogsProvider(),
        lastfm_provider=DisabledLastFMProvider(),
        plex_server_factory=lambda url, token: FakePlexServer(),
    )

    context = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")

    assert context.wikipedia.extract == "Wikipedia summary"
    assert wikipedia_provider.album_calls == 1
    assert provider_manager.album_calls == 0


def test_enrichment_pipeline_requires_exactly_one_plex_album() -> None:
    """Pipeline should fail clearly when Plex cannot identify exactly one album."""
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=FakeMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=FakeProviderManager(),
        wikipedia_provider=FakeWikipediaProvider(),
        discogs_provider=DisabledDiscogsProvider(),
        lastfm_provider=DisabledLastFMProvider(),
        plex_server_factory=lambda url, token: EmptyPlexServer(),
    )

    try:
        pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")
    except EnrichmentPipelineError as exc:
        assert 'No Plex album named "Pastel Blues"' in str(exc)
    else:
        raise AssertionError("Expected EnrichmentPipelineError.")


def test_enrichment_pipeline_caches_discogs_album_context(tmp_path) -> None:
    """Successful Discogs pipeline lookups should use the shared knowledge cache."""
    discogs_provider = CountingDiscogsProvider()
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=FakeMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=FakeProviderManager(),
        wikipedia_provider=FakeWikipediaProvider(),
        discogs_provider=discogs_provider,
        lastfm_provider=DisabledLastFMProvider(),
        knowledge_cache=KnowledgeCacheService(KnowledgeCacheStore(root=tmp_path)),
        plex_server_factory=lambda url, token: FakePlexServer(),
    )

    first = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")
    second = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")

    assert first.discogs.label == "Cached Discogs Label"
    assert second.discogs == first.discogs
    assert discogs_provider.album_calls == 1


def test_enrichment_pipeline_caches_lastfm_context(tmp_path) -> None:
    """Successful Last.fm pipeline lookups should use the shared knowledge cache."""
    lastfm_provider = CountingLastFMProvider()
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("secret-token"),
        matcher=FakeMatcher(),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        provider_manager=FakeProviderManager(),
        wikipedia_provider=FakeWikipediaProvider(),
        discogs_provider=DisabledDiscogsProvider(),
        lastfm_provider=lastfm_provider,
        knowledge_cache=KnowledgeCacheService(KnowledgeCacheStore(root=tmp_path)),
        plex_server_factory=lambda url, token: FakePlexServer(),
    )

    first = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")
    second = pipeline.collect_album_context(artist="Nina Simone", album="Pastel Blues")

    assert first.lastfm.summary == "Cached Last.fm album summary."
    assert second.lastfm == first.lastfm
    assert lastfm_provider.album_calls == 1
    assert lastfm_provider.artist_calls == 1


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
            catalog_number="PHS 600-187",
            barcode="123456789012",
            release_country="US",
            first_release_date="1965-10",
            recording_locations=["New York"],
            studios=["RCA Studio B"],
            featured_artists=["Featured Example"],
            guest_musicians=["Guest Example"],
            orchestras=["Studio Orchestra"],
            choir="Session Choir",
            choirs=["Session Choir"],
            publisher="Publishing Example",
            publishers=["Publishing Example"],
            secondary_genres=["vocal jazz"],
            certifications=["Gold"],
            chart_positions=["Billboard 200 #8"],
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


class CountingProviderManager(FakeProviderManager):
    """Provider manager that records fallback calls."""

    def __init__(self) -> None:
        """Create a counting fake."""
        self.album_calls = 0

    def get_album_metadata(self, artist: str, album: str) -> AlbumMetadata:
        """Return normalized provider metadata."""
        self.album_calls += 1
        return super().get_album_metadata(artist, album)


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


class CountingWikipediaProvider(FakeWikipediaProvider):
    """Wikipedia provider that records detailed lookup calls."""

    def __init__(self) -> None:
        """Create a counting fake."""
        self.album_calls = 0

    def lookup_album(self, artist: str, album: str) -> WikipediaSummary:
        """Return detailed Wikipedia summary metadata."""
        self.album_calls += 1
        return super().lookup_album(artist, album)


class EmptyWikipediaProvider:
    """Wikipedia provider with no match."""

    name = "wikipedia"

    def lookup_album(self, artist: str, album: str) -> None:
        """Return no Wikipedia metadata."""
        del artist, album
        return None


class FakeDiscogsProvider:
    """Fake configured Discogs provider."""

    configured = True

    def lookup_album(self, artist: str, album: str) -> DiscogsAlbumContext:
        """Return Discogs album credits."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return DiscogsAlbumContext(
            label="Discogs Label",
            labels=["Discogs Label"],
            catalog_number="DG-001",
            catalog_numbers=["DG-001"],
            country="US",
            formats=["Vinyl, LP"],
            producer=["Discogs Producer"],
            engineer=["Discogs Engineer"],
            mastering=["Discogs Mastering"],
            mixed_by=["Discogs Mixer"],
            personnel=["Discogs Guitarist"],
            guest_musicians=["Discogs Guest"],
            credits=["Discogs Unknown (Liner Notes)"],
            notes="Discogs release notes.",
        )

    def lookup_artist(self, artist: str) -> DiscogsArtistContext:
        """Return Discogs artist context."""
        assert artist == "Nina Simone"
        return DiscogsArtistContext(profile="Discogs artist profile.", aliases=["Eunice Waymon"])


class DisabledDiscogsProvider:
    """Fake disabled Discogs provider."""

    configured = False

    def lookup_album(self, artist: str, album: str) -> DiscogsAlbumContext:
        """Return no Discogs album context."""
        del artist, album
        return DiscogsAlbumContext()

    def lookup_artist(self, artist: str) -> DiscogsArtistContext:
        """Return no Discogs artist context."""
        del artist
        return DiscogsArtistContext()


class CountingDiscogsProvider(FakeDiscogsProvider):
    """Fake Discogs provider that records album calls."""

    def __init__(self) -> None:
        """Create a counting fake."""
        self.album_calls = 0

    def lookup_album(self, artist: str, album: str) -> DiscogsAlbumContext:
        """Return cacheable Discogs album context."""
        self.album_calls += 1
        del artist, album
        return DiscogsAlbumContext(label="Cached Discogs Label", labels=["Cached Discogs Label"])


class FakeLastFMProvider:
    """Fake configured Last.fm provider."""

    configured = True

    def lookup_album(self, artist: str, album: str) -> LastFMAlbumContext:
        """Return Last.fm album context."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return LastFMAlbumContext(
            summary="Last.fm album summary.",
            wiki="Last.fm album background.",
            tags=["vocal jazz", "soul"],
            listeners=1234,
            playcount=5678,
            url="https://www.last.fm/music/Nina+Simone/Pastel+Blues",
        )

    def lookup_artist(self, artist: str) -> LastFMArtistContext:
        """Return Last.fm artist context."""
        assert artist == "Nina Simone"
        return LastFMArtistContext(
            biography="Last.fm artist biography.",
            short_biography="Last.fm short biography.",
            tags=["jazz singer"],
            similar_artists=["Billie Holiday"],
            listeners=9999,
            playcount=8888,
            url="https://www.last.fm/music/Nina+Simone",
        )


class DisabledLastFMProvider:
    """Fake disabled Last.fm provider."""

    configured = False

    def lookup_album(self, artist: str, album: str) -> LastFMAlbumContext:
        """Return no Last.fm album context."""
        del artist, album
        return LastFMAlbumContext()

    def lookup_artist(self, artist: str) -> LastFMArtistContext:
        """Return no Last.fm artist context."""
        del artist
        return LastFMArtistContext()


class CountingLastFMProvider(FakeLastFMProvider):
    """Fake Last.fm provider that records calls."""

    def __init__(self) -> None:
        """Create a counting fake."""
        self.album_calls = 0
        self.artist_calls = 0

    def lookup_album(self, artist: str, album: str) -> LastFMAlbumContext:
        """Return cacheable Last.fm album context."""
        self.album_calls += 1
        del artist, album
        return LastFMAlbumContext(summary="Cached Last.fm album summary.", tags=["soul"])

    def lookup_artist(self, artist: str) -> LastFMArtistContext:
        """Return cacheable Last.fm artist context."""
        self.artist_calls += 1
        del artist
        return LastFMArtistContext(biography="Cached Last.fm artist biography.", tags=["jazz"])


class FakePlexServer:
    """Fake Plex server with one music album."""

    @property
    def library(self) -> FakeLibrary:
        """Return fake Plex library."""
        return FakeLibrary(
            [
                FakeSection(
                    [
                        FakeArtist(
                            [
                                FakeAlbum(
                                    rating_key="41",
                                    title="I Put a Spell on You",
                                    year=1965,
                                ),
                                FakeAlbum(),
                                FakeAlbum(
                                    rating_key="43",
                                    title="Let It All Out",
                                    year=1966,
                                ),
                            ]
                        )
                    ]
                )
            ]
        )


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
    artistHistory = "American singer, pianist, and civil rights artist."  # noqa: N815
    yearsActive = "1954-2003"  # noqa: N815
    currentLineup = ["Nina Simone"]  # noqa: N815
    lineupChanges = "Solo artist with changing studio ensembles."  # noqa: N815
    majorInfluences = ["jazz", "blues", "gospel"]  # noqa: N815
    historicalContext = "Recorded during Simone's Philips Records period."  # noqa: N815

    def __init__(self, albums: list[Any]) -> None:
        """Create a fake artist."""
        self._albums = albums

    def albums(self) -> list[Any]:
        """Return albums."""
        return self._albums


class FakeAlbum:
    """Fake Plex album."""

    def __init__(
        self,
        *,
        rating_key: str = "42",
        title: str = "Pastel Blues",
        year: int = 1965,
    ) -> None:
        """Create a fake Plex album."""
        self.ratingKey = rating_key  # noqa: N815
        self.parentTitle = "Nina Simone"  # noqa: N815
        self.title = title
        self.year = year
        self.summary = "Current Plex summary"
        self.genres = ["Jazz", "Soul"]
        self.styles = ["Vocal Jazz"]
        self.moods = ["Melancholy"]
        self.producers = ["Hal Mooney"]
        self.composers = ["Nina Simone"]
        self.lyricists = ["Oscar Brown Jr."]
        self.label = "Philips Records"
        self.recordingPeriod = "1964-1965"  # noqa: N815
        self.recordingLocation = "New York"  # noqa: N815
        self.studios = ["RCA Studio B"]
        self.notableSingles = ["Sinnerman"]  # noqa: N815
        self.guestMusicians = ["Guitarist Example"]  # noqa: N815
        self.careerPhase = "mature phase"  # noqa: N815
        self.commercialPeak = "Mid-1960s Philips period"  # noqa: N815
        self.genreEvolution = (  # noqa: N815
            "Continued the move from jazz standards toward blues and soul."
        )
        self.coverVersions = ["Strange Fruit"]  # noqa: N815
        self.notableTracks = ["Sinnerman", "Strange Fruit"]  # noqa: N815
        self.singles = ["Sinnerman"]
        self.hitSingles = ["Sinnerman"]  # noqa: N815
        self.promotionalSingles = ["Chilly Winds Don't Blow"]  # noqa: N815
        self.conceptAlbum = True  # noqa: N815
        self.albumHighlights = ["Extended performance of Sinnerman"]  # noqa: N815
        self.signatureSong = "Sinnerman"  # noqa: N815
        self.bestKnownSong = "Sinnerman"  # noqa: N815
        self.stylisticHighlights = ["blues-gospel intensity"]  # noqa: N815
        self.experimentalElements = ["long-form closing track"]  # noqa: N815
        self.recurringThemes = ["spiritual tension", "civil rights-era unease"]  # noqa: N815
        self.criticalConsensus = "Often praised for its intensity and range."  # noqa: N815
        self.commercialSummary = "Includes one of Simone's best-known recordings."  # noqa: N815
        self.legacySummary = (  # noqa: N815
            "Sinnerman later became one of Simone's signature recordings."
        )

    def tracks(self) -> list[FakeTrack]:
        """Return fake Plex tracks."""
        return [
            FakeTrack(index=1, title="Be My Husband", duration=120_000),
            FakeTrack(
                index=2,
                title="Chilly Winds Don't Blow",
                duration=180_000,
                instrumental=True,
            ),
            FakeTrack(index=3, title="Sinnerman", duration=600_000),
        ]


class FakeTrack:
    """Fake Plex track."""

    def __init__(
        self,
        *,
        index: int,
        title: str,
        duration: int,
        instrumental: bool = False,
    ) -> None:
        """Create a fake Plex track."""
        self.index = index
        self.title = title
        self.duration = duration
        self.instrumental = instrumental
