"""Smart enrichment planner tests."""

from __future__ import annotations

from plex_music_enhancer.batch import BatchAlbumCandidate
from plex_music_enhancer.planner import (
    ContentIssue,
    EnrichmentAction,
    EnrichmentPlanner,
    QualityLevel,
    analyze_content_quality,
)


def test_planner_creates_missing_summaries() -> None:
    """Missing summaries should be created from metadata."""
    plan = EnrichmentPlanner().plan_summary(None)

    assert plan.action is EnrichmentAction.CREATE
    assert plan.language == "unknown"
    assert "Missing summary" in plan.reason
    assert plan.quality.quality_score == 0
    assert ContentIssue.MISSING in plan.quality.issues


def test_planner_translates_english_summaries() -> None:
    """English summaries should be translated."""
    plan = EnrichmentPlanner().plan_summary(
        "The album is a focused jazz recording with a sparse sound and a reflective tone."
    )

    assert plan.action is EnrichmentAction.TRANSLATE
    assert plan.language == "english"


def test_planner_improves_short_german_summaries() -> None:
    """Short German summaries should be improved."""
    plan = EnrichmentPlanner().plan_summary(
        "Das Album ist eine ruhige Jazzaufnahme mit klarer Sprache."
    )

    assert plan.action is EnrichmentAction.IMPROVE
    assert plan.language == "german"
    assert ContentIssue.SHORT in plan.quality.issues


def test_planner_improves_poor_german_summaries() -> None:
    """Poor German summaries should be improved even when they contain facts."""
    plan = EnrichmentPlanner().plan_summary(
        "Das Album wurde veröffentlicht in 1965 und ist den Genres Jazz und Blues " "zuzuordnen."
    )

    assert plan.action is EnrichmentAction.IMPROVE
    assert plan.quality.quality_score < 60
    assert ContentIssue.MACHINE_TRANSLATION in plan.quality.issues


def test_planner_skips_high_quality_german_summaries() -> None:
    """Excellent German summaries should be skipped."""
    plan = EnrichmentPlanner().plan_summary(_excellent_german_summary())

    assert plan.action is EnrichmentAction.SKIP
    assert plan.language == "german"
    assert plan.quality.quality_score > 80
    assert plan.quality.quality_level is QualityLevel.EXCELLENT


def test_planner_reviews_fair_german_summaries() -> None:
    """Fair German summaries should be sent to manual review."""
    plan = EnrichmentPlanner().plan_summary(
        "Das Album verbindet ruhige Jazzpassagen mit zurückhaltendem Blues und klaren "
        "Arrangements. Die Aufnahme wirkt konzentriert und sachlich, bleibt in der "
        "Darstellung aber knapp. Das Album ist eine sachliche Beschreibung und das "
        "Album ist eine sachliche Beschreibung und das Album ist eine sachliche "
        "Beschreibung."
    )

    assert plan.action is EnrichmentAction.REVIEW
    assert 60 <= plan.quality.quality_score <= 80
    assert ContentIssue.REPETITIVE in plan.quality.issues


def test_planner_reviews_unknown_language() -> None:
    """Ambiguous summaries should be sent to manual review."""
    plan = EnrichmentPlanner().plan_summary("Ambient textures, nocturne, modal phrasing.")

    assert plan.action is EnrichmentAction.REVIEW
    assert plan.language == "other"
    assert ContentIssue.UNKNOWN_LANGUAGE in plan.quality.issues


def test_quality_report_detects_placeholder_text() -> None:
    """Placeholder summaries should be treated as poor content."""
    report = analyze_content_quality("TODO: Das Album ist ein Platzhaltertext.")

    assert report.quality_level is QualityLevel.POOR
    assert ContentIssue.PLACEHOLDER in report.issues


def test_quality_report_detects_machine_translation() -> None:
    """Awkward translated phrasing should be reported."""
    report = analyze_content_quality(
        "Das Album ist den Genres Jazz und Soul zuzuordnen und wurde veröffentlicht in " "1965."
    )

    assert ContentIssue.MACHINE_TRANSLATION in report.issues


def test_quality_report_detects_duplicate_wording() -> None:
    """Repeated phrases should lower content quality."""
    report = analyze_content_quality(
        "Das Album hat eine ruhige Sprache. Die Aufnahme bleibt sachlich und präzise. "
        "Das Album hat eine ruhige Sprache. Das Album hat eine ruhige Sprache."
    )

    assert ContentIssue.REPETITIVE in report.issues


def test_quality_report_detects_formatting_and_whitespace() -> None:
    """Markdown and excessive whitespace should be reported."""
    report = analyze_content_quality(
        "Das Album ist eine Beschreibung.   \n\n\n- Es nutzt eine Liste."
    )

    assert ContentIssue.EXCESSIVE_WHITESPACE in report.issues
    assert ContentIssue.FORMATTING_PROBLEMS in report.issues


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


def _excellent_german_summary() -> str:
    """Return varied German prose that should be considered complete."""
    return (
        "Das Album verbindet soulige Gesangspassagen mit zurückhaltenden Jazz- und "
        "Blues-Elementen. Die Arrangements lassen der Stimme viel Raum und setzen auf "
        "klare Dynamik statt auf überladene Produktion. Besonders prägend ist die "
        "konzentrierte Atmosphäre, die zwischen stiller Spannung und kraftvollen "
        "Akzenten wechselt. Dadurch entsteht eine sachliche, gut einordnbare "
        "Beschreibung des musikalischen Charakters, ohne einzelne Fakten unnötig zu "
        "wiederholen."
    )
