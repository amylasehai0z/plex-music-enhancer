"""Fact verification and confidence engine tests."""

from __future__ import annotations

from plex_music_enhancer.enrichment import (
    AlbumContext,
    ArtistContext,
    DiscogsAlbumContext,
    DiscogsArtistContext,
    LastFMAlbumContext,
    LastFMArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.verification import (
    FactVerifier,
    VerificationState,
    confidence_for_sources,
)


def test_confidence_calculation_is_deterministic() -> None:
    """Source combinations should map to stable confidence scores."""
    assert confidence_for_sources(sources=["musicbrainz", "discogs", "wikipedia"]) == 1.0
    assert confidence_for_sources(sources=["musicbrainz", "wikipedia"]) == 0.95
    assert confidence_for_sources(sources=["discogs"]) == 0.75
    assert confidence_for_sources(sources=["wikipedia"]) == 0.70
    assert confidence_for_sources(sources=["lastfm"]) == 0.50
    assert confidence_for_sources(sources=["musicbrainz"], conflicting=True) == 0.30
    assert confidence_for_sources(sources=[]) == 0.0


def test_fact_verifier_merges_duplicate_supported_facts() -> None:
    """The same value from multiple providers should become one supported fact."""
    collection = FactVerifier().verify_album(
        _context(producers=["Nick Patrick"], discogs_producers=["Nick Patrick"])
    )

    producers = [
        fact for fact in collection.by_category("producer") if fact.value == "Nick Patrick"
    ]

    assert len(producers) == 1
    assert producers[0].supporting_sources == ["musicbrainz", "discogs"]
    assert producers[0].verification_state == VerificationState.VERIFIED


def test_fact_verifier_detects_conflicting_metadata() -> None:
    """Conflicting single-value categories should be exposed, not hidden."""
    collection = FactVerifier().verify_album(
        _context(labels=["Philips Records"], discogs_labels=["RCA Victor"])
    )

    labels = collection.by_category("label")

    assert {fact.value for fact in labels} == {"Philips Records", "RCA Victor"}
    assert all(fact.verification_state == VerificationState.CONFLICTING for fact in labels)
    assert all(fact.confidence_score == 0.30 for fact in labels)
    assert {fact.category for fact in collection.conflicts} == {"label"}


def test_fact_verifier_marks_lastfm_only_facts_as_weak() -> None:
    """Community-only Last.fm metadata should be available but low confidence."""
    collection = FactVerifier().verify_album(
        _context(
            genres=[],
            musicbrainz_genres=[],
            plex_genres=[],
            lastfm_tags=["adult contemporary"],
        )
    )

    genre = collection.by_category("genres")[0]

    assert genre.value == "adult contemporary"
    assert genre.supporting_sources == ["lastfm"]
    assert genre.verification_state == VerificationState.WEAK
    assert genre.confidence_score == 0.50


def test_fact_verifier_reports_missing_categories() -> None:
    """Unavailable factual areas should be listed as missing context."""
    collection = FactVerifier().verify_album(_context(recording_location=None))

    assert "recording_location" in collection.missing_facts
    assert collection.by_category("recording_location")[0].verification_state == (
        VerificationState.UNKNOWN
    )


def test_fact_verifier_verifies_artist_facts() -> None:
    """Artist facts should use the same confidence model as albums."""
    collection = FactVerifier().verify_artist(_artist_context())

    birth_date = collection.by_category("birth_date")[0]
    genre = collection.by_category("genres")[0]

    assert birth_date.value == "1933-02-21"
    assert birth_date.verification_state == VerificationState.VERIFIED
    assert "musicbrainz" in birth_date.supporting_sources
    assert genre.verification_state in {VerificationState.VERIFIED, VerificationState.PROBABLE}
    assert "biography" not in collection.missing_facts


def test_fact_verifier_detects_conflicting_artist_facts() -> None:
    """Artist single-value conflicts should be visible."""
    context = _artist_context(origin="US", plex_country="France")

    collection = FactVerifier().verify_artist(context)
    origins = collection.by_category("origin")

    assert {fact.value for fact in origins} == {"US", "France"}
    assert all(fact.verification_state == VerificationState.CONFLICTING for fact in origins)
    assert {fact.category for fact in collection.conflicts} == {"origin"}


def _context(
    *,
    producers: list[str] | None = None,
    discogs_producers: list[str] | None = None,
    labels: list[str] | None = None,
    discogs_labels: list[str] | None = None,
    genres: list[str] | None = None,
    musicbrainz_genres: list[str] | None = None,
    plex_genres: list[str] | None = None,
    lastfm_tags: list[str] | None = None,
    recording_location: str | None = "New York",
) -> AlbumContext:
    """Return an album context with configurable provider facts."""
    selected_genres = ["jazz"] if genres is None else genres
    selected_musicbrainz_genres = (
        selected_genres if musicbrainz_genres is None else musicbrainz_genres
    )
    selected_plex_genres = selected_genres if plex_genres is None else plex_genres
    selected_producers = ["Hal Mooney"] if producers is None else producers
    selected_discogs_producers = (
        selected_producers if discogs_producers is None else discogs_producers
    )
    selected_labels = ["Philips Records"] if labels is None else labels
    selected_discogs_labels = selected_labels if discogs_labels is None else discogs_labels
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Current summary.",
            genres=selected_plex_genres,
        ),
        musicbrainz=MusicBrainzAlbumContext(
            release_date="1965-10",
            genres=selected_musicbrainz_genres,
            confidence=95,
        ),
        wikipedia=WikipediaAlbumContext(extract="Pastel Blues was released in 1965."),
        discogs=DiscogsAlbumContext(
            labels=selected_discogs_labels,
            producer=selected_discogs_producers,
            recording_location=recording_location,
        ),
        lastfm=LastFMAlbumContext(tags=[] if lastfm_tags is None else lastfm_tags),
        pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        producers=selected_producers,
        labels=selected_labels,
        genres=selected_genres,
        recording_location=recording_location,
    )


def _artist_context(
    *,
    origin: str | None = "US",
    plex_country: str | None = "US",
) -> ArtistContext:
    """Return an artist context with multiple provider facts."""
    return ArtistContext(
        plex=PlexArtistContext(
            rating_key="100",
            artist="Nina Simone",
            summary="Plex biography.",
            genres=["Jazz"],
            country=plex_country,
        ),
        musicbrainz=MusicBrainzArtistContext(
            artist_mbid="artist-mbid",
            artist_name="Nina Simone",
            country="US",
            genres=["jazz", "soul"],
            begin_date="1933-02-21",
            end_date="2003-04-21",
            aliases=["Eunice Waymon"],
            confidence=100,
        ),
        wikipedia=WikipediaArtistContext(extract="Nina Simone war Musikerin."),
        discogs=DiscogsArtistContext(
            aliases=["Eunice Waymon"],
            genres=["Jazz"],
            styles=["Vocal Jazz"],
            active_years="1954-2003",
        ),
        lastfm=LastFMArtistContext(
            biography="Last.fm biography.",
            short_biography="Last.fm short biography.",
            tags=["soul"],
        ),
        pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        full_name="Nina Simone",
        aliases=["Eunice Waymon"],
        birth_date="1933-02-21",
        death_date="2003-04-21",
        origin=origin,
        nationality="US",
        active_years="1954-2003",
        genres=["jazz", "soul"],
        styles=["Vocal Jazz"],
        biography="Nina Simone war Musikerin.",
        career_summary="Last.fm short biography.",
    )
