"""Smart enrichment planner tests."""

from __future__ import annotations

from plex_music_enhancer.batch import BatchAlbumCandidate
from plex_music_enhancer.planner import EnrichmentAction, EnrichmentPlanner


def test_planner_creates_missing_summaries() -> None:
    """Missing summaries should be created from metadata."""
    plan = EnrichmentPlanner().plan_summary(None)

    assert plan.action is EnrichmentAction.CREATE
    assert plan.language == "unknown"
    assert "Missing summary" in plan.reason


def test_planner_translates_english_summaries() -> None:
    """English summaries should be translated."""
    plan = EnrichmentPlanner().plan_summary(
        "The album is a focused jazz recording with a sparse sound and a reflective tone."
    )

    assert plan.action is EnrichmentAction.TRANSLATE
    assert plan.language == "english"


def test_planner_improves_short_german_summaries() -> None:
    """Short German summaries should be improved."""
    plan = EnrichmentPlanner(german_improve_threshold_words=20).plan_summary(
        "Das Album ist eine ruhige Jazzaufnahme mit klarer Sprache."
    )

    assert plan.action is EnrichmentAction.IMPROVE
    assert plan.language == "german"


def test_planner_skips_high_quality_german_summaries() -> None:
    """Longer German summaries should be skipped."""
    summary = " ".join(["Das Album ist eine sachliche Beschreibung und"] * 20)
    plan = EnrichmentPlanner(german_improve_threshold_words=20).plan_summary(summary)

    assert plan.action is EnrichmentAction.SKIP
    assert plan.language == "german"


def test_planner_reviews_unknown_language() -> None:
    """Ambiguous summaries should be sent to manual review."""
    plan = EnrichmentPlanner().plan_summary("Ambient textures, nocturne, modal phrasing.")

    assert plan.action is EnrichmentAction.REVIEW
    assert plan.language == "other"


def test_planner_returns_planned_albums() -> None:
    """Planner should include album metadata in planning reports."""
    candidate = BatchAlbumCandidate(
        rating_key="42",
        library="Music",
        artist="Nina Simone",
        album="Pastel Blues",
        current_summary=None,
    )

    report = EnrichmentPlanner().plan_albums([candidate])

    assert len(report.albums) == 1
    assert report.albums[0].album == "Pastel Blues"
    assert report.albums[0].plan.action is EnrichmentAction.CREATE
