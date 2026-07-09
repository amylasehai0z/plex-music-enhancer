"""Interactive review workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from rich.console import Console

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.enrichment import (
    AlbumContext,
    ArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.prompts import (
    ARTIST_BIOGRAPHY_MAX_WORDS,
    ARTIST_BIOGRAPHY_MIN_WORDS,
    RenderedPrompt,
)
from plex_music_enhancer.quality import QualityLevel, VerificationMetrics
from plex_music_enhancer.quality import QualityReport as QAReport
from plex_music_enhancer.review import (
    ReviewDebugContext,
    ReviewDebugLogger,
    ReviewDocument,
    ReviewLimits,
    ReviewRenderer,
    ReviewService,
)
from plex_music_enhancer.review.diff import unified_summary_diff
from plex_music_enhancer.review.policy import evaluate_review_policy
from plex_music_enhancer.review.service import _review_limits_for_preview, validate_summary_quality
from plex_music_enhancer.services import ArtistPreviewDocument, EnrichmentPreviewDocument
from plex_music_enhancer.verification import FactCollection, VerificationState, VerifiedFact


def test_unified_summary_diff_marks_changes() -> None:
    """Unified diff should compare current and generated summary text."""
    diff = unified_summary_diff("Alte Zusammenfassung.", "Neue Zusammenfassung.")

    assert "--- current summary" in diff
    assert "+++ generated summary" in diff
    assert "-Alte Zusammenfassung." in diff
    assert "+Neue Zusammenfassung." in diff


def test_quality_validation_passes_good_german_summary() -> None:
    """Quality validation should pass clean German prose in range."""
    summary = _german_summary(words=95)

    report = validate_summary_quality(summary)

    assert report.status == "PASS"
    assert report.word_count == 95
    assert report.failures == []
    assert report.warnings == []
    assert all(report.checks.values())


def test_quality_validation_warns_for_short_summary() -> None:
    """Quality validation should warn when prose is valid but too short."""
    report = validate_summary_quality(
        "Das Album ist ein Jazzalbum mit verifizierbaren Angaben.",
        limits=ReviewLimits(minimum_words=10, maximum_words=120),
    )

    assert report.status == "WARNINGS"
    assert report.failures == []
    assert report.warnings
    assert report.checks["length_in_range"] is False


def test_quality_validation_rejects_empty_markdown_bullets_and_placeholders() -> None:
    """Quality validation should fail summaries that can never be applied."""
    empty = validate_summary_quality("")
    markdown = validate_summary_quality("## Titel\n\nDies ist ein placeholder Text.")
    bullet = validate_summary_quality("- Das Album ist ein Jazzalbum.")

    assert empty.status == "FAILED"
    assert "Summary is empty." in empty.failures
    assert markdown.status == "FAILED"
    assert "Summary contains Markdown formatting." in markdown.failures
    assert "Summary contains placeholder text." in markdown.failures
    assert bullet.status == "FAILED"
    assert "Summary contains bullet lists." in bullet.failures


def test_quality_validation_rejects_non_german_summary() -> None:
    """Language validation is a critical failure."""
    report = validate_summary_quality("This album is a neutral English summary.")

    assert report.status == "FAILED"
    assert report.checks["language_is_german"] is False
    assert "Summary does not appear to be German." in report.failures


def test_artist_review_limits_match_prompt_word_target() -> None:
    """Artist review validation should share the prompt's biography word limits."""
    preview = _artist_preview_document_for_limits()

    limits = _review_limits_for_preview(preview, ReviewLimits())

    assert limits.minimum_words == ARTIST_BIOGRAPHY_MIN_WORDS
    assert limits.maximum_words == ARTIST_BIOGRAPHY_MAX_WORDS


def test_quality_validation_warns_for_repetitive_sentence_starts() -> None:
    """Editorial validation should detect repeated sentence openings."""
    report = validate_summary_quality(
        "Das Album erschien 1975 bei einem bekannten Label. "
        "Das Album verbindet Rock mit ruhigen Balladen. "
        "Das Album wurde von einem erfahrenen Produzenten betreut.",
        limits=ReviewLimits(minimum_words=1, maximum_words=120),
    )

    assert report.status == "WARNINGS"
    assert report.checks["varied_sentence_openings"] is False
    assert any("REPETITIVE_SENTENCE_STARTS" in warning for warning in report.warnings)


def test_quality_validation_warns_for_fact_list_style() -> None:
    """Editorial validation should reject field/value metadata prose."""
    report = validate_summary_quality(
        "Künstler: Nina Simone. Album: Pastel Blues. Genre: Jazz. Label: Philips Records.",
        limits=ReviewLimits(minimum_words=1, maximum_words=120),
    )

    assert report.status == "WARNINGS"
    assert report.checks["not_fact_list_style"] is False
    assert any("FACT_LIST_STYLE" in warning for warning in report.warnings)


def test_quality_validation_warns_for_poor_transitions() -> None:
    """Editorial validation should detect disconnected sentence chains."""
    report = validate_summary_quality(
        "Pastel Blues erschien 1965 bei Philips Records. "
        "Nina Simone sang mehrere Stücke mit sparsamer Begleitung. "
        "Die Aufnahme verbindet Jazz, Blues und Soul. "
        "Die Produktion bleibt trocken und konzentriert.",
        limits=ReviewLimits(minimum_words=1, maximum_words=120),
    )

    assert report.status == "WARNINGS"
    assert report.checks["natural_transitions"] is False
    assert any("POOR_TRANSITIONS" in warning for warning in report.warnings)


def test_quality_validation_warns_for_weak_opening_and_abrupt_ending() -> None:
    """Editorial validation should detect weak article framing."""
    report = validate_summary_quality(
        "Das Album ist eine Jazzaufnahme. "
        "Dabei verbindet die Sängerin kontrollierte Arrangements mit Blues. "
        "Ende.",
        limits=ReviewLimits(minimum_words=1, maximum_words=120),
    )

    assert report.status == "WARNINGS"
    assert report.checks["strong_opening"] is False
    assert report.checks["complete_closing"] is False
    assert any("WEAK_OPENING" in warning for warning in report.warnings)
    assert any("ABRUPT_ENDING" in warning for warning in report.warnings)


def test_review_service_creates_and_edits_review_document() -> None:
    """ReviewService should build review documents and revalidate edits."""
    service = ReviewService(
        preview_service=FakePreviewService(_preview_document(_german_summary(words=95)))
    )

    document = service.create_review(artist="Nina Simone", album="Pastel Blues")
    edited = service.update_summary(document, _german_summary(words=90))

    assert document.current_summary == "Aktuelle Plex-Zusammenfassung."
    assert document.quality.status == "PASS"
    assert edited.edited is True
    assert edited.quality.status == "PASS"
    assert edited.proposed_summary != document.proposed_summary
    assert "+Das Album ist" in edited.diff


def test_review_service_rejects_generated_placeholder_summary() -> None:
    """ReviewService should mark placeholder output as failed."""
    service = ReviewService(preview_service=FakePreviewService(_preview_document("placeholder")))

    document = service.create_review(artist="Nina Simone", album="Pastel Blues")

    assert document.quality.status == "FAILED"
    assert "Summary contains placeholder text." in document.quality.failures


def test_review_service_attaches_style_analysis() -> None:
    """Review documents should include German editorial diagnostics."""
    service = ReviewService(
        preview_service=FakePreviewService(
            _preview_document(
                "Das Album zeigt eindrucksvoll eine gelungene Mischung. "
                "Das Album verbindet Jazz und Blues. "
                "Das Album bleibt sachlich beschrieben.",
            )
        ),
        limits=ReviewLimits(minimum_words=1, maximum_words=120),
    )

    document = service.create_review(artist="Nina Simone", album="Pastel Blues")

    assert document.style.llm_cliches in {"LOW", "MEDIUM", "HIGH"}
    assert "LLM_CLICHES" in document.style.issues
    assert "REPETITIVE_SENTENCE_OPENINGS" in document.style.issues


def test_review_service_can_polish_generated_summary() -> None:
    """Optional polishing should improve wording before review without adding facts."""
    service = ReviewService(
        preview_service=FakePreviewService(
            _preview_document(
                "Pastel Blues zeigt eindrucksvoll, wie Nina Simone 1965 Jazz und Blues verbindet."
            )
        ),
        limits=ReviewLimits(minimum_words=1, maximum_words=120),
        polish=True,
    )

    document = service.create_review(artist="Nina Simone", album="Pastel Blues")

    assert "zeigt eindrucksvoll" not in document.proposed_summary
    assert "Pastel Blues" in document.proposed_summary
    assert "Nina Simone" in document.proposed_summary
    assert "1965" in document.proposed_summary


def test_review_renderer_outputs_required_sections() -> None:
    """ReviewRenderer should display summary, diff, and quality sections."""
    service = ReviewService(
        preview_service=FakePreviewService(_preview_document(_german_summary(words=95)))
    )
    document = service.create_review(artist="Nina Simone", album="Pastel Blues")
    console = Console(record=True, width=120)

    ReviewRenderer(console).render(document)

    output = console.export_text()
    assert "CURRENT SUMMARY" in output
    assert "GENERATED SUMMARY" in output
    assert "UNIFIED DIFF" in output
    assert "QUALITY" in output
    assert "QUALITY SUMMARY" in output
    assert "Critical validation" in output
    assert "Editorial validation" in output
    assert "Publishable" in output
    assert "EDITORIAL QUALITY" in output
    assert "STYLE ANALYSIS" in output
    assert "VERIFICATION SUMMARY" in output
    assert "Sentence variation" in output
    assert "PASS" in output


def test_review_debug_logger_writes_sectioned_review_log(tmp_path) -> None:
    """Review debug logger should persist the current review sections as plain text."""
    document = _review_document()
    log_path = tmp_path / "plex_review.log"
    prompt_dump_path = tmp_path / "openai_prompt.txt"
    prompt_dump_path.write_text(document.preview.rendered_prompt.rendered_text, encoding="utf-8")
    logger = ReviewDebugLogger(
        path=log_path,
        prompt_dump_path=prompt_dump_path,
        clock=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    logger.write(
        document,
        ReviewDebugContext(
            artist="Nina Simone",
            album="Pastel Blues",
            provider="openai",
            model="gpt-5.5",
        ),
    )

    output = log_path.read_text(encoding="utf-8")
    assert "Timestamp: 2026-01-01T12:00:00+00:00" in output
    assert "Command context: artist=Nina Simone, album=Pastel Blues" in output
    assert "provider=openai" in output
    assert "model=gpt-5.5" in output
    assert "=== PROMPT " in output
    assert document.preview.rendered_prompt.rendered_text in output
    assert "=== CURRENT SUMMARY " in output
    assert "Aktuelle Plex-Zusammenfassung." in output
    assert "=== GENERATED SUMMARY " in output
    assert document.proposed_summary in output
    assert "=== UNIFIED DIFF " in output
    assert "--- current summary" in output
    assert "=== QUALITY " in output
    assert "QUALITY SUMMARY" in output
    assert "=== STYLE ANALYSIS " in output
    assert "Sentence variation" in output
    assert "=== EDITORIAL QUALITY " in output
    assert "Overall Score" in output
    assert "=== VERIFICATION " in output
    assert "VERIFICATION SUMMARY" in output


def test_policy_allows_score_91_with_weak_opening_warning() -> None:
    """A high editorial score should allow apply despite non-critical warnings."""
    document = _review_document(
        checks={"strong_opening": False},
        warnings=["WEAK_OPENING: Summary opens with generic or weak phrasing."],
        qa_score=91,
    )

    policy = evaluate_review_policy(document)

    assert policy.apply_allowed is True
    assert policy.critical_validation == "PASS"
    assert policy.editorial_validation == "WARNINGS"
    assert policy.publishable is True


def test_policy_allows_score_90_with_transition_warning() -> None:
    """Natural-transition warnings should never block apply by themselves."""
    document = _review_document(
        checks={"natural_transitions": False},
        warnings=["POOR_TRANSITIONS: Summary lacks natural transitions."],
        qa_score=90,
    )

    policy = evaluate_review_policy(document)

    assert policy.apply_allowed is True
    assert policy.editorial_validation == "WARNINGS"


def test_policy_blocks_placeholder_markdown_empty_and_language_failures() -> None:
    """Critical validation failures must block apply."""
    cases = [
        _review_document(
            proposed_summary="placeholder",
            checks={"no_placeholder_text": False},
            failures=["Summary contains placeholder text."],
        ),
        _review_document(
            proposed_summary="This album is an English summary.",
            checks={"language_is_german": False},
            failures=["Summary does not appear to be German."],
        ),
        _review_document(
            proposed_summary="## Titel\n\nDas Album ist sachlich beschrieben.",
            checks={"no_markdown": False},
            failures=["Summary contains Markdown formatting."],
        ),
        _review_document(
            proposed_summary="",
            checks={"not_empty": False},
            failures=["Summary is empty."],
        ),
    ]

    for document in cases:
        policy = evaluate_review_policy(document)

        assert policy.apply_allowed is False
        assert policy.critical_validation == "FAIL"
        assert policy.publishable is False


def test_policy_blocks_factual_conflicts() -> None:
    """Fact conflicts are hard failures even when prose quality is high."""
    conflict = VerifiedFact(
        value="1965",
        category="release_year",
        confidence_score=0.3,
        supporting_sources=["wikipedia"],
        conflicting_sources=["musicbrainz"],
        preferred_source=None,
        verification_state=VerificationState.CONFLICTING,
    )
    document = _review_document(
        fact_collection=FactCollection(facts=[conflict], conflicts=[conflict]),
        qa_score=91,
    )

    policy = evaluate_review_policy(document)

    assert policy.apply_allowed is False
    assert "Factual conflicts exist." in policy.critical_failures


def test_policy_blocks_low_verification_confidence() -> None:
    """Facts below the configured confidence threshold are hard failures."""
    weak_fact = VerifiedFact(
        value="Unverified Label",
        category="label",
        confidence_score=0.4,
        supporting_sources=["lastfm"],
        conflicting_sources=[],
        preferred_source="lastfm",
        verification_state=VerificationState.WEAK,
    )
    document = _review_document(
        fact_collection=FactCollection(facts=[weak_fact]),
        qa_score=91,
        verification_metrics=VerificationMetrics(weak_facts_mentioned=["label"]),
    )

    policy = evaluate_review_policy(document, verification_confidence_threshold=0.7)

    assert policy.apply_allowed is False
    assert any("Verification confidence" in failure for failure in policy.critical_failures)


class FakePreviewService:
    """Fake preview service for review tests."""

    def __init__(self, document: EnrichmentPreviewDocument) -> None:
        """Create a fake preview service."""
        self._document = document

    def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
        """Return fake preview output."""
        assert artist == "Nina Simone"
        assert album == "Pastel Blues"
        return self._document


class _FrozenModel(BaseModel):
    """Base frozen model for fixtures."""

    model_config = ConfigDict(frozen=True)


def _artist_preview_document_for_limits() -> ArtistPreviewDocument:
    """Return an artist preview fixture for review-limit tests."""
    return ArtistPreviewDocument(
        context=ArtistContext(
            plex=PlexArtistContext(rating_key="100", artist="Nina Simone", summary=""),
            musicbrainz=MusicBrainzArtistContext(artist_name="Nina Simone"),
            wikipedia=WikipediaArtistContext(),
            pipeline=PipelineContext(collected_sources=["plex"], ready_for_generation=True),
        ),
        rendered_prompt=RenderedPrompt(
            name="artist_biography",
            version="1.0",
            rendered_text=(f"Use {ARTIST_BIOGRAPHY_MIN_WORDS}-{ARTIST_BIOGRAPHY_MAX_WORDS} words"),
            variables={},
            template="Template",
        ),
        generated_summary=GeneratedSummary(
            language="de",
            text=_german_summary(words=ARTIST_BIOGRAPHY_MIN_WORDS),
            provider="dummy",
            model="dummy",
            prompt_name="artist_biography",
            prompt_version="1.0",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=1.0,
            source_count=1,
        ),
        generation_time_seconds=0.0,
    )


def _preview_document(
    summary: str,
    *,
    fact_collection: FactCollection | None = None,
    qa_score: int = 91,
    qa_level: QualityLevel = QualityLevel.VERY_GOOD,
    verification_metrics: VerificationMetrics | None = None,
) -> EnrichmentPreviewDocument:
    """Return preview document fixture."""
    return EnrichmentPreviewDocument(
        context=_album_context(fact_collection=fact_collection),
        rendered_prompt=RenderedPrompt(
            name="album_summary",
            version="1.0",
            rendered_text="Prompt",
            variables={"artist": "Nina Simone", "album": "Pastel Blues", "language": "de"},
            template="Template",
        ),
        generated_summary=GeneratedSummary(
            language="de",
            text=summary,
            provider="openai",
            model="gpt-5.5",
            prompt_name="album_summary",
            prompt_version="1.0",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=0.9,
            source_count=3,
            metadata={"prompt_tokens": 100, "completion_tokens": 40},
        ),
        generation_time_seconds=0.25,
        qa_report=QAReport(
            overall_score=qa_score,
            quality_level=qa_level,
            verification_metrics=verification_metrics or VerificationMetrics(),
        ),
    )


def _review_document(
    *,
    proposed_summary: str | None = None,
    checks: dict[str, bool] | None = None,
    warnings: list[str] | None = None,
    failures: list[str] | None = None,
    fact_collection: FactCollection | None = None,
    qa_score: int = 91,
    qa_level: QualityLevel = QualityLevel.VERY_GOOD,
    verification_metrics: VerificationMetrics | None = None,
) -> ReviewDocument:
    """Return a review document fixture for policy tests."""
    summary = proposed_summary if proposed_summary is not None else _german_summary(words=95)
    selected_checks = {
        "not_empty": bool(summary.strip()),
        "language_is_german": True,
        "length_in_range": True,
        "no_markdown": True,
        "no_bullet_lists": True,
        "no_placeholder_text": True,
        "varied_sentence_openings": True,
        "not_fact_list_style": True,
        "natural_transitions": True,
        "strong_opening": True,
        "complete_closing": True,
    }
    if checks:
        selected_checks.update(checks)
    selected_failures = failures or []
    selected_warnings = warnings or []
    status = "FAILED" if selected_failures else ("WARNINGS" if selected_warnings else "PASS")
    return ReviewDocument(
        preview=_preview_document(
            summary,
            fact_collection=fact_collection,
            qa_score=qa_score,
            qa_level=qa_level,
            verification_metrics=verification_metrics,
        ),
        current_summary="Aktuelle Plex-Zusammenfassung.",
        proposed_summary=summary,
        diff=unified_summary_diff("Aktuelle Plex-Zusammenfassung.", summary),
        quality=validate_summary_quality(summary).model_copy(
            update={
                "status": status,
                "checks": selected_checks,
                "warnings": selected_warnings,
                "failures": selected_failures,
                "word_count": len(summary.split()) if summary else 0,
            }
        ),
    )


def _album_context(fact_collection: FactCollection | None = None) -> AlbumContext:
    """Return album context fixture."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Aktuelle Plex-Zusammenfassung.",
            genres=["Jazz", "Soul"],
            styles=[],
            moods=[],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            genres=["jazz"],
            tags=["blues"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(
            language="de",
            title="Pastel Blues",
            extract="Wikipedia summary",
            page_url="https://de.wikipedia.org/wiki/Pastel_Blues",
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
        fact_collection=fact_collection or FactCollection(),
    )


def _german_summary(*, words: int) -> str:
    """Return deterministic German prose with a requested word count."""
    base_words = [
        "Das",
        "Album",
        "ist",
        "eine",
        "sachliche",
        "Sammlung",
        "verifizierbarer",
        "Angaben",
        "und",
        "beschreibt",
        "die",
        "musikalische",
        "Einordnung",
        "mit",
        "ruhigem",
        "Ton",
        "und",
        "neutraler",
        "Sprache",
    ]
    repeated = [base_words[index % len(base_words)] for index in range(words)]
    return " ".join(repeated) + "."
