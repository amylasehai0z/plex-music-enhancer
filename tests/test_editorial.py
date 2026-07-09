"""Editorial composition tests."""

from __future__ import annotations

from plex_music_enhancer.editorial import EditorialComposer
from plex_music_enhancer.editorial.composer import render_editorial_context
from plex_music_enhancer.enrichment import (
    AlbumContext,
    DiscogsAlbumContext,
    LastFMAlbumContext,
    LastFMArtistContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)


def test_editorial_composer_builds_story_order_from_available_context() -> None:
    """Composer should omit unavailable story sections and keep a narrative order."""
    editorial = EditorialComposer().compose_album(_context())

    assert editorial.recommended_story_order == [
        "Studio album",
        "Career placement",
        "Recording",
        "Musical style",
        "Production",
        "Personnel",
        "Songwriting and themes",
        "Historical significance",
        "Closing classification",
    ]
    assert editorial.opening_focus is not None
    assert "Pastel Blues" in editorial.opening_focus
    assert "2. studio album" in editorial.opening_focus


def test_editorial_composer_scores_facts_by_source_support() -> None:
    """Facts backed by stronger or multiple sources should sort ahead of weaker facts."""
    editorial = EditorialComposer().compose_album(_context())
    assert editorial.important_facts is not None

    release = _fact(editorial.important_facts, "release_date")
    producer = _fact(editorial.important_facts, "producer", contains="Discogs Producer")
    community = _fact(editorial.important_facts, "community_tags")

    assert release.confidence == "high"
    assert producer.confidence == "high"
    assert community.confidence == "low"
    assert release.priority > producer.priority > community.priority


def test_editorial_composer_removes_duplicate_facts() -> None:
    """Facts repeated by merged provider context should be emitted once."""
    editorial = EditorialComposer().compose_album(
        _context(producers=["Nick Patrick", "Nick Patrick"], discogs_producers=["Nick Patrick"])
    )
    assert editorial.production_context is not None

    producer_facts = [
        fact for fact in editorial.production_context if fact.text == "Producer: Nick Patrick"
    ]

    assert len(producer_facts) == 1
    assert producer_facts[0].sources == ["musicbrainz", "discogs"]


def test_editorial_composer_reports_missing_context() -> None:
    """Composer should expose factual gaps that the prompt must not invent."""
    editorial = EditorialComposer().compose_album(
        _context(
            release_date=None,
            year=None,
            genres=[],
            producers=[],
            labels=[],
            recording_location=None,
            recording_period=None,
            studios=[],
            career_phase=None,
            discography_position=None,
            artist_biography=None,
        )
    )

    assert editorial.missing_context == [
        "release date",
        "genres",
        "artist context",
        "producer",
        "label",
        "recording information",
    ]
    assert editorial.avoid_topics is not None
    assert "unsupplied producer" in editorial.avoid_topics


def test_editorial_renderer_omits_empty_sections() -> None:
    """Rendered editorial context should skip sections without usable facts."""
    rendered = render_editorial_context(
        EditorialComposer().compose_album(_context(producers=[], discogs_producers=[], labels=[]))
    )

    assert "Production context:" not in rendered
    assert "Producer:" not in rendered
    assert "Label:" not in rendered
    assert "Opening focus:" in rendered


def test_editorial_prompt_guidance_contains_prioritized_facts() -> None:
    """Rendered context should include story guidance, facts, and safeguards."""
    rendered = render_editorial_context(EditorialComposer().compose_album(_context()))

    assert "Recommended story order:" in rendered
    assert "Most important facts:" in rendered
    assert "Verified facts:" in rendered
    assert "Probable facts:" in rendered
    assert "Weak facts:" in rendered
    assert "Writing guidance:" in rendered
    assert "emphasize verified facts" in rendered
    assert "never resolve conflicting facts by guessing" in rendered
    assert "avoid isolated fact lists" in rendered
    assert "Avoid topics:" in rendered


def test_editorial_composer_omits_conflicting_facts_from_narrative_context() -> None:
    """Conflicting provider values should be diagnosed but not used as prose facts."""
    editorial = EditorialComposer().compose_album(
        _context(
            producers=[],
            discogs_producers=[],
            labels=["Philips Records"],
            discogs_labels=["RCA Victor"],
        )
    )
    rendered = render_editorial_context(editorial)

    assert editorial.conflicting_facts is not None
    assert "Conflicting facts:" in rendered
    assert "Production context:" not in rendered
    assert "Label: Philips Records" not in rendered
    assert "RCA Victor" in rendered


def _fact(facts, topic: str, *, contains: str | None = None):
    """Return one fact by topic and optional text fragment."""
    for fact in facts:
        if fact.topic == topic and (contains is None or contains in fact.text):
            return fact
    raise AssertionError(f"Missing fact: {topic}")


def _context(
    *,
    release_date: str | None = "1965-10",
    year: int | None = 1965,
    genres: list[str] | None = None,
    producers: list[str] | None = None,
    discogs_producers: list[str] | None = None,
    labels: list[str] | None = None,
    discogs_labels: list[str] | None = None,
    recording_location: str | None = "New York",
    recording_period: str | None = "1964-1965",
    studios: list[str] | None = None,
    career_phase: str | None = "mature phase",
    discography_position: str | None = "2. studio album in available discography",
    artist_biography: str | None = "Last.fm artist biography.",
) -> AlbumContext:
    """Return an album context fixture."""
    selected_genres = ["jazz"] if genres is None else genres
    selected_producers = ["Hal Mooney", "Discogs Producer"] if producers is None else producers
    selected_discogs_producers = (
        ["Discogs Producer"] if discogs_producers is None else discogs_producers
    )
    selected_labels = ["Philips Records"] if labels is None else labels
    selected_discogs_labels = selected_labels if discogs_labels is None else discogs_labels
    selected_studios = ["RCA Studio B"] if studios is None else studios
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=year,
            summary="Current summary.",
            genres=selected_genres,
        ),
        musicbrainz=MusicBrainzAlbumContext(
            release_date=release_date,
            genres=selected_genres,
            tags=["blues"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(
            language="en",
            title="Pastel Blues",
            extract="Pastel Blues was released in 1965.",
        ),
        discogs=DiscogsAlbumContext(
            producer=selected_discogs_producers,
            recording_location=recording_location,
            labels=selected_discogs_labels,
        ),
        lastfm=LastFMAlbumContext(tags=["vocal jazz"], summary="Last.fm album context."),
        lastfm_artist=LastFMArtistContext(
            biography=artist_biography,
            tags=["jazz singer"],
            similar_artists=["Billie Holiday"],
        ),
        pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        producers=selected_producers,
        labels=selected_labels,
        genres=selected_genres,
        recording_location=recording_location,
        recording_period=recording_period,
        studios=selected_studios,
        career_phase=career_phase,
        discography_position=discography_position,
        composers=["Nina Simone"],
        lyricists=["Oscar Brown Jr."],
        sound_engineers=["Sound Engineer"],
        notable_tracks=["Sinnerman"],
        historical_context="Recorded during Simone's Philips period.",
        legacy_summary="Later known for Sinnerman.",
    )
