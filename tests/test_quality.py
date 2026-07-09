"""Editorial QA engine tests."""

from __future__ import annotations

from plex_music_enhancer.enrichment import (
    AlbumContext,
    ArtistContext,
    DiscogsArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.quality import EditorialQualityEngine, QualityCategory
from plex_music_enhancer.verification import FactVerifier


def test_quality_engine_scores_complete_album_summary() -> None:
    """Complete German prose should receive a strong deterministic QA report."""
    context = _album_context()
    text = (
        "Pastel Blues erschien 1965 von Nina Simone und verbindet Jazz mit Soul. "
        "Dabei prägen Produzent Hal Mooney, Philips Records und die Aufnahme in New York "
        "den konzentrierten Klang. Zudem verweist Sinnerman auf den historischen Kontext "
        "der Philips-Phase."
    )

    report = EditorialQualityEngine().analyze_album(context, text)

    assert report.overall_score >= 80
    assert report.overall_level == report.quality_level
    assert report.metadata_coverage.coverage_score > 0
    assert report.editorial_metrics.sentence_count == 3
    assert report.quality_level.value in {"GOOD", "VERY GOOD", "EXCELLENT"}
    assert report.verification_metrics.verified_facts_mentioned
    assert not report.verification_metrics.conflicting_facts_mentioned


def test_quality_engine_reports_missing_metadata_opportunities() -> None:
    """Available reliable metadata omitted from text should produce recommendations."""
    context = _album_context()

    report = EditorialQualityEngine().analyze_album(
        context,
        "Pastel Blues erschien 1965 von Nina Simone und ist ein Jazzalbum.",
    )

    assert "producer" in report.missing_topics
    assert "label" in report.missing_topics
    assert any("Producer available" in item for item in report.recommendations)
    assert report.metadata_coverage.omitted_topics
    assert any(check.category is QualityCategory.COMPLETENESS for check in report.checks)


def test_quality_engine_detects_conflicting_fact_mentions() -> None:
    """Conflicting verified facts should be reported when mentioned."""
    context = _album_context(labels=["Philips Records", "RCA Victor"])

    report = EditorialQualityEngine().analyze_album(
        context,
        "Pastel Blues erschien 1965 bei RCA Victor.",
    )

    assert report.verification_metrics.conflicting_facts_mentioned
    assert report.verification_metrics.coverage_score >= 0
    assert any("conflicting" in warning.casefold() for warning in report.warnings)


def test_quality_engine_analyzes_artist_biography() -> None:
    """Artist biographies should use the same QA model."""
    context = _artist_context()
    text = (
        "Nina Simone war eine US-amerikanische Musikerin, die ab 1954 aktiv war. "
        "Dabei verband sie Jazz und Soul mit einer sachlichen, eigenständigen "
        "Interpretationsweise."
    )

    report = EditorialQualityEngine().analyze_artist(context, text)

    assert report.overall_score >= 70
    assert report.style_metrics["lexical_diversity"] is not None
    assert report.verification_metrics.verified_facts_mentioned


def test_quality_engine_recommends_missing_artist_context() -> None:
    """Artist QA should recommend available career, style, legacy, and work context."""
    context = _artist_context().model_copy(
        update={
            "historical_context": "wichtige Stimme der Bürgerrechtsbewegung",
            "associated_acts": ["Langston Hughes"],
            "notable_albums": ["Pastel Blues"],
            "milestones": ["Durchbruch in den 1960er Jahren"],
            "genres": ["Jazz", "Soul"],
        }
    )
    context = context.model_copy(update={"fact_collection": FactVerifier().verify_artist(context)})
    text = (
        "Nina Simone war eine US-amerikanische Musikerin. "
        "Ihre Laufbahn wird hier bewusst knapp beschrieben."
    )

    report = EditorialQualityEngine().analyze_artist(context, text)
    recommendations = [str(item) for item in report.recommendations]

    assert "Historical context available but not mentioned." in recommendations
    assert "Associated artists available but not mentioned." in recommendations
    assert "Important albums available but not mentioned." in recommendations
    assert "Career milestones available but not mentioned." in recommendations
    assert "Genres available but not mentioned." in recommendations


def test_quality_engine_filters_unknown_and_low_confidence_artist_recommendations() -> None:
    """Unknown fields and low-confidence probable facts should not become recommendations."""
    context = _artist_context().model_copy(
        update={
            "death_date": None,
            "members": [],
            "discogs": DiscogsArtistContext(members=["Discogs Member"]),
        }
    )
    context = context.model_copy(update={"fact_collection": FactVerifier().verify_artist(context)})

    report = EditorialQualityEngine().analyze_artist(
        context,
        "Nina Simone verband Jazz und Soul in einer eigenständigen musikalischen Sprache.",
    )
    recommendations = [str(item) for item in report.recommendations]

    assert not any("Death Date available" in item for item in recommendations)
    assert not any("Members available" in item for item in recommendations)


def test_quality_engine_does_not_modify_generated_text() -> None:
    """The QA engine should only report and never rewrite text."""
    context = _album_context()
    text = "Pastel Blues zeigt eindrucksvoll Jazz."

    EditorialQualityEngine().analyze_album(context, text)

    assert text == "Pastel Blues zeigt eindrucksvoll Jazz."


def _album_context(labels: list[str] | None = None) -> AlbumContext:
    """Return a verified album context."""
    context = AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Current summary.",
            genres=["Jazz"],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            release_date="1965-10",
            genres=["Jazz", "Soul"],
            confidence=95,
        ),
        wikipedia=WikipediaAlbumContext(extract="Pastel Blues was released in 1965."),
        pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        producers=["Hal Mooney"],
        labels=["Philips Records"] if labels is None else labels,
        genres=["Jazz", "Soul"],
        recording_location="New York",
        historical_context="Philips phase",
        notable_tracks=["Sinnerman"],
    )
    return context.model_copy(update={"fact_collection": FactVerifier().verify_album(context)})


def _artist_context() -> ArtistContext:
    """Return a verified artist context."""
    context = ArtistContext(
        plex=PlexArtistContext(
            rating_key="100",
            artist="Nina Simone",
            summary="Current biography.",
            genres=["Jazz"],
            country="US",
        ),
        musicbrainz=MusicBrainzArtistContext(
            artist_name="Nina Simone",
            country="US",
            genres=["Jazz", "Soul"],
            begin_date="1954",
            aliases=["Eunice Waymon"],
            confidence=100,
        ),
        wikipedia=WikipediaArtistContext(extract="Nina Simone war Musikerin."),
        pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        full_name="Nina Simone",
        active_years="1954",
        genres=["Jazz", "Soul"],
        biography="Nina Simone war Musikerin.",
    )
    return context.model_copy(update={"fact_collection": FactVerifier().verify_artist(context)})
