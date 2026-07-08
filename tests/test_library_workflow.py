"""Full-library workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.apply import ApplyResult
from plex_music_enhancer.batch import BatchAlbumCandidate
from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.library import LibrarySessionStore, LibraryWorkflowService
from plex_music_enhancer.planner import EnrichmentAction
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.review import QualityReport, ReviewDocument
from plex_music_enhancer.services import EnrichmentPreviewDocument


def test_library_plan_groups_albums_by_action(tmp_path: Path) -> None:
    """Library planning should group every album by planner action."""
    service = _service(
        tmp_path=tmp_path,
        candidates=[
            _candidate("1", summary=None),
            _candidate("2", summary="The album is a concise jazz recording."),
            _candidate("3", summary="Das Album ist kurz."),
            _candidate("4", summary=_excellent_german_summary()),
        ],
    )

    report = service.plan_library(library="Music")
    counts = {group.action: group.count for group in report.groups}

    assert report.total_albums == 4
    assert counts[EnrichmentAction.CREATE] == 1
    assert counts[EnrichmentAction.TRANSLATE] == 1
    assert counts[EnrichmentAction.IMPROVE] == 1
    assert counts[EnrichmentAction.SKIP] == 1
    assert report.estimated_processing_seconds == 90


def test_library_review_collects_approved_items_without_applying(tmp_path: Path) -> None:
    """Library review should approve generated items and leave writes for library apply."""
    review_service = FakeReviewService()
    apply_service = FakeApplyService()
    service = _service(
        tmp_path=tmp_path,
        candidates=[
            _candidate("1", summary=None),
            _candidate("2", summary="The album is a concise jazz recording."),
            _candidate("3", summary="Das Album ist kurz."),
            _candidate("4", summary=_excellent_german_summary()),
        ],
        review_service=review_service,
        apply_service=apply_service,
    )
    decisions = iter(["APPLY", "SKIP", "APPLY"])

    report = service.review_library(
        library="Music",
        decide=lambda step: next(decisions),  # type: ignore[arg-type]
    )

    assert review_service.prompt_names == [
        "album_summary",
        "album_translate",
        "album_improve",
    ]
    assert report.albums_processed == 3
    assert report.approved == 2
    assert report.skipped == 1
    assert report.applied == 0
    assert apply_service.applied == []
    assert Path(report.session_path).exists()


def test_library_resume_skips_completed_items(tmp_path: Path) -> None:
    """Resume should continue after already recorded review decisions."""
    review_service = FakeReviewService()
    service = _service(
        tmp_path=tmp_path,
        candidates=[_candidate("1", summary=None), _candidate("2", summary="Das Album ist kurz.")],
        review_service=review_service,
    )

    first = service.review_library(library="Music", decide=lambda step: "APPLY")
    second = service.review_library(library="Music", resume=True, decide=lambda step: "APPLY")

    assert first.approved == 2
    assert second.albums_processed == 2
    assert review_service.prompt_names == ["album_summary", "album_improve"]


def test_library_apply_applies_approved_reviews(tmp_path: Path) -> None:
    """Library apply should write only approved saved reviews."""
    apply_service = FakeApplyService()
    service = _service(
        tmp_path=tmp_path,
        candidates=[_candidate("1", summary=None), _candidate("2", summary="Das Album ist kurz.")],
        apply_service=apply_service,
    )
    decisions = iter(["APPLY", "SKIP"])
    service.review_library(
        library="Music",
        decide=lambda step: next(decisions),  # type: ignore[arg-type]
    )

    report = service.apply_approved(library="Music")

    assert report.applied == 1
    assert report.skipped == 1
    assert apply_service.applied == ["Pastel Blues 1"]


def test_library_report_summarizes_saved_session(tmp_path: Path) -> None:
    """Library report should summarize a persisted session."""
    service = _service(
        tmp_path=tmp_path,
        candidates=[_candidate("1", summary=None), _candidate("2", summary="Das Album ist kurz.")],
    )
    service.review_library(library="Music", decide=lambda step: "APPLY")

    report = service.session_report(library="Music")

    assert report.albums_processed == 2
    assert report.created == 1
    assert report.improved == 1
    assert report.average_quality_score > 0
    assert report.average_generation_time_seconds == 0.25


class FakeAlbumSource:
    """Fake album source."""

    def __init__(self, candidates: list[BatchAlbumCandidate]) -> None:
        """Create a fake source."""
        self._candidates = candidates

    def scan_albums(self, *, library: str | None = None) -> list[BatchAlbumCandidate]:
        """Return candidates."""
        if library is None:
            return self._candidates
        return [candidate for candidate in self._candidates if candidate.library == library]


class FakeReviewService:
    """Fake review service."""

    def __init__(self) -> None:
        """Create a fake review service."""
        self.prompt_names: list[str] = []

    def create_review(
        self,
        *,
        artist: str,
        album: str,
        prompt_name: str = "album_summary",
    ) -> ReviewDocument:
        """Create a fake review document."""
        self.prompt_names.append(prompt_name)
        return _review_document(artist=artist, album=album, prompt_name=prompt_name)

    def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
        """Return a fake edited review document."""
        return document.model_copy(update={"proposed_summary": edited_summary, "edited": True})


class FakeApplyService:
    """Fake apply service."""

    def __init__(self) -> None:
        """Create a fake apply service."""
        self.applied: list[str] = []

    def apply_review(self, review: ReviewDocument) -> ApplyResult:
        """Record an applied review."""
        context = review.preview.context
        self.applied.append(context.plex.album)
        return ApplyResult(
            status="SUCCESS",
            artist=context.plex.artist,
            album=context.plex.album,
            rating_key=context.plex.rating_key,
            backup_created=True,
            write_successful=True,
            verification_passed=True,
            audit_stored=True,
            backup_path="exports/backups/item.json",
            audit_path="exports/audit/item.json",
            message="Summary written and verified successfully.",
            review=review,
        )


def _service(
    *,
    tmp_path: Path,
    candidates: list[BatchAlbumCandidate],
    review_service: FakeReviewService | None = None,
    apply_service: FakeApplyService | None = None,
) -> LibraryWorkflowService:
    """Create a library workflow service with fake dependencies."""
    return LibraryWorkflowService(
        album_source=FakeAlbumSource(candidates),
        review_service=review_service or FakeReviewService(),  # type: ignore[arg-type]
        apply_service=apply_service or FakeApplyService(),  # type: ignore[arg-type]
        session_store=LibrarySessionStore(directory=tmp_path / "exports" / "library"),
    )


def _candidate(rating_key: str, *, summary: str | None = None) -> BatchAlbumCandidate:
    """Create a fake album candidate."""
    return BatchAlbumCandidate(
        rating_key=rating_key,
        library="Music",
        artist="Nina Simone",
        album=f"Pastel Blues {rating_key}",
        current_summary=summary,
    )


def _review_document(*, artist: str, album: str, prompt_name: str) -> ReviewDocument:
    """Create a review document."""
    summary = _generated_summary()
    return ReviewDocument(
        preview=EnrichmentPreviewDocument(
            context=_album_context(artist=artist, album=album),
            rendered_prompt=RenderedPrompt(
                name=prompt_name,
                version="1.0",
                rendered_text="Prompt",
                variables={"artist": artist, "album": album, "language": "de"},
                template="Template",
            ),
            generated_summary=GeneratedSummary(
                language="de",
                text=summary,
                provider="dummy",
                model="dummy-v1",
                prompt_name=prompt_name,
                prompt_version="1.0",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                confidence=1.0,
                source_count=3,
                metadata={},
            ),
            generation_time_seconds=0.25,
        ),
        current_summary="Current summary",
        proposed_summary=summary,
        diff="--- current\n+++ generated\n",
        quality=QualityReport(
            status="PASS",
            checks={"not_empty": True},
            warnings=[],
            failures=[],
            word_count=90,
        ),
    )


def _album_context(*, artist: str, album: str) -> AlbumContext:
    """Create album context."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key=album.rsplit(" ", maxsplit=1)[-1],
            artist=artist,
            album=album,
            year=1965,
            summary="Current summary",
            genres=["Jazz"],
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
            title=album,
            extract="Wikipedia summary",
            page_url="https://de.wikipedia.org/wiki/Pastel_Blues",
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )


def _generated_summary() -> str:
    """Return deterministic generated German prose."""
    return (
        "Das Album verbindet soulige Gesangspassagen mit zurückhaltenden Jazz- und "
        "Blues-Elementen. Die Arrangements lassen der Stimme viel Raum und setzen auf "
        "klare Dynamik statt auf überladene Produktion. Besonders prägend ist die "
        "konzentrierte Atmosphäre, die zwischen stiller Spannung und kraftvollen "
        "Akzenten wechselt. Dadurch entsteht eine sachliche, gut einordnbare "
        "Beschreibung des musikalischen Charakters, ohne einzelne Fakten unnötig zu "
        "wiederholen."
    )


def _excellent_german_summary() -> str:
    """Return an existing German summary that planner should skip."""
    return _generated_summary()
