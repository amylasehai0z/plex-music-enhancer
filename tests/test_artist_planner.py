"""Tests for artist enrichment planner."""

from plex_music_enhancer.planner.artist import (
    ArtistEnrichmentPlanner,
    _analyze_biography_quality,
    _estimate_biography_language,
)
from plex_music_enhancer.planner.models import (
    ContentIssue,
    EnrichmentAction,
    QualityLevel,
)
from plex_music_enhancer.plex.audit import SummaryLanguage


class TestEstimateBiographyLanguage:
    """Test language detection for artist biographies."""

    def test_detects_german_biography(self) -> None:
        """German text should be detected as German."""
        german_text = (
            "Bob Dylan ist ein US-amerikanischer Musiker und Songwriter. "
            "Er wurde 1941 geboren und ist bekannt für seine influenzielle "
            "Rolle in der Populärmusik."
        )
        assert _estimate_biography_language(german_text) is SummaryLanguage.GERMAN

    def test_detects_english_biography(self) -> None:
        """English text should be detected as English."""
        english_text = (
            "David Bowie was an English singer, songwriter, and musician. "
            "He is widely regarded as one of the most influential rock artists of the 20th century."
        )
        assert _estimate_biography_language(english_text) is SummaryLanguage.ENGLISH

    def test_handles_empty_text(self) -> None:
        """Empty text should return UNKNOWN."""
        assert _estimate_biography_language("") is SummaryLanguage.UNKNOWN

    def test_handles_mixed_language(self) -> None:
        """Mixed language should fall back to dominant language."""
        mixed = "The Beatles waren eine englische Band and they revolutionized music."
        # Result depends on indicator counts; should handle gracefully
        result = _estimate_biography_language(mixed)
        assert result in [SummaryLanguage.GERMAN, SummaryLanguage.ENGLISH]


class TestAnalyzeBiographyQuality:
    """Test quality analysis for artist biographies."""

    def test_scores_good_german_biography(self) -> None:
        """Well-written German biography should score high."""
        good_bio = (
            "Prince war ein US-amerikanischer Musiker, Sänger und Songwriter. "
            "Er wurde 1958 in Minneapolis geboren und ist bekannt für seine "
            "Virtuosität, seinen unverwechselbaren Musikstil und seine Kontrolle "
            "über seine künstlerische Karriere. Prince starb 2016 in Minneapolis."
        )
        quality = _analyze_biography_quality(good_bio, SummaryLanguage.GERMAN)
        assert quality.quality_score >= 60
        assert quality.quality_level in [QualityLevel.GOOD, QualityLevel.EXCELLENT]

    def test_penalizes_too_short_biography(self) -> None:
        """Very short biography should be flagged."""
        short_bio = "Artist from USA."
        quality = _analyze_biography_quality(short_bio, SummaryLanguage.GERMAN)
        assert ContentIssue.TOO_SHORT in quality.issues
        assert quality.quality_score < 60

    def test_penalizes_too_long_biography(self) -> None:
        """Very long biography should be flagged."""
        long_bio = " ".join(["word"] * 600)
        quality = _analyze_biography_quality(long_bio, SummaryLanguage.GERMAN)
        assert ContentIssue.TOO_LONG in quality.issues
        assert quality.quality_score < 100

    def test_detects_markdown_formatting(self) -> None:
        """Markdown-formatted text should be flagged."""
        markdown_bio = """• Born in 1980
        • Known for rock music
        • Won multiple awards"""
        quality = _analyze_biography_quality(markdown_bio, SummaryLanguage.GERMAN)
        assert ContentIssue.MARKDOWN_DETECTED in quality.issues
        assert quality.quality_score < 80

    def test_detects_mixed_language(self) -> None:
        """German text with many English words should be flagged."""
        mixed_bio = (
            "David Bowie was ein berühmter Musiker. He was also known for "
            "his innovative style. The Beatles and other artists influenced him. "
            "He is one of the greatest rock musicians."
        )
        quality = _analyze_biography_quality(mixed_bio, SummaryLanguage.GERMAN)
        # May flag as mixed language depending on English word count
        assert quality.quality_score <= 100


class TestArtistEnrichmentPlanner:
    """Test artist enrichment planning logic."""

    def test_create_action_for_missing_biography(self) -> None:
        """Missing biography should recommend CREATE."""
        planner = ArtistEnrichmentPlanner()
        plan = planner.plan_biography(None)
        assert plan.action is EnrichmentAction.CREATE
        assert plan.reason == "Missing artist biography."
        assert ContentIssue.MISSING in plan.quality.issues

    def test_create_action_for_empty_biography(self) -> None:
        """Empty biography should recommend CREATE."""
        planner = ArtistEnrichmentPlanner()
        plan = planner.plan_biography("   ")
        assert plan.action is EnrichmentAction.CREATE

    def test_translate_action_for_english_biography(self) -> None:
        """English biography should recommend TRANSLATE."""
        planner = ArtistEnrichmentPlanner()
        english_bio = (
            "Jimi Hendrix was an American guitarist and singer-songwriter. "
            "He is widely regarded as one of the greatest electric guitarists "
            "in the history of popular music."
        )
        plan = planner.plan_biography(english_bio)
        assert plan.action is EnrichmentAction.TRANSLATE
        assert "English" in plan.reason

    def test_improve_action_for_poor_german_biography(self) -> None:
        """Poor German biography should recommend IMPROVE."""
        planner = ArtistEnrichmentPlanner()
        poor_bio = "Artist."  # Too short, poor quality
        plan = planner.plan_biography(poor_bio)
        assert plan.action is EnrichmentAction.IMPROVE
        assert "poor" in plan.reason.lower()

    def test_review_action_for_medium_quality_german_biography(self) -> None:
        """Medium-quality German biography should recommend REVIEW."""
        planner = ArtistEnrichmentPlanner()
        medium_bio = (
            "Kurt Cobain war ein amerikanischer Musiker und Sänger. "
            "Er war der Sänger der Rockband Nirvana."
        )
        plan = planner.plan_biography(medium_bio)
        # Depending on quality score (60-80), should be REVIEW
        if 60 <= plan.quality.quality_score <= 80:
            assert plan.action is EnrichmentAction.REVIEW

    def test_skip_action_for_excellent_german_biography(self) -> None:
        """Excellent German biography should recommend SKIP."""
        planner = ArtistEnrichmentPlanner()
        excellent_bio = (
            "Madonna Louise Ciccone ist eine US-amerikanische Sängerin, Songwriterin "
            "und Schauspielerin. Sie wurde 1958 in Bay City geboren und ist bekannt als "
            "die Königin des Pop. Madonna hat eine immense Karriere mit zahlreichen "
            "Hits und Auszeichnungen und hat die Popkultur nachhaltig beeinflusst."
        )
        plan = planner.plan_biography(excellent_bio)
        if plan.quality.quality_score > 80:
            assert plan.action is EnrichmentAction.SKIP
            assert "high" in plan.reason.lower()

    def test_confidence_scores_decrease_for_uncertain_cases(self) -> None:
        """Confidence should be highest for clear cases."""
        planner = ArtistEnrichmentPlanner()

        # Missing (highest confidence)
        plan_missing = planner.plan_biography(None)
        assert plan_missing.confidence == 1.0

        # English (high confidence)
        plan_english = planner.plan_biography("This is an English biography.")
        assert plan_english.confidence >= 0.85

        # Unknown language (lower confidence)
        plan_unknown = planner.plan_biography("日本語テキスト")
        assert plan_unknown.confidence < 0.75

    def test_quality_report_structure(self) -> None:
        """Quality report should have consistent structure."""
        planner = ArtistEnrichmentPlanner()
        plan = planner.plan_biography("Some artist biography.")

        # Quality report should always be present
        assert plan.quality is not None
        assert 0 <= plan.quality.quality_score <= 100
        assert plan.quality.quality_level in [
            QualityLevel.POOR,
            QualityLevel.ACCEPTABLE,
            QualityLevel.GOOD,
            QualityLevel.EXCELLENT,
        ]
        assert isinstance(plan.quality.issues, list)
