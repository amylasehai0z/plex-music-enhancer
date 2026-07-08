"""Batch review workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.apply import ApplyResult
from plex_music_enhancer.batch import (
    BatchAlbumCandidate,
    BatchProgressStore,
    BatchReviewOptions,
    BatchReviewService,
    PlexBatchAlbumSource,
    filter_album_candidates,
    is_missing_summary,
)
from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.review import QualityReport, ReviewDocument
from plex_music_enhancer.services import EnrichmentPreviewDocument


def test_filter_album_candidates_supports_missing_limit_and_completed() -> None:
    """Batch filters should isolate missing summaries and respect resume progress."""
    candidates = [
        _candidate("1", summary=None),
        _candidate("2", summary="Existing summary"),
        _candidate("3", summary=""),
    ]

    filtered = filter_album_candidates(
        candidates,
        missing_only=True,
        limit=1,
        completed_rating_keys={"1"},
    )

    assert len(filtered) == 1
    assert filtered[0].rating_key == "3"
    assert is_missing_summary(candidates[0]) is True
    assert is_missing_summary(candidates[1]) is False


def test_progress_store_saves_and_resumes(tmp_path: Path) -> None:
    """Batch progress should persist completed rating keys."""
    store = BatchProgressStore(directory=tmp_path / "exports" / "jobs")
    progress = store.load_or_create(library="Music", missing_only=True, resume=False)
    progress = progress.mark_completed("42")
    path = store.save(progress)

    resumed = store.load_or_create(library="Music", missing_only=True, resume=True)

    assert path.exists()
    assert resumed.completed_rating_keys == ["42"]
    assert resumed.library == "Music"


def test_batch_review_service_applies_and_skips(tmp_path: Path) -> None:
    """Batch review should process albums sequentially and count outcomes."""
    apply_service = FakeApplyService()
    service = _service(
        tmp_path=tmp_path,
        candidates=[_candidate("1"), _candidate("2")],
        apply_service=apply_service,
    )
    decisions = iter(["APPLY", "SKIP"])

    report = service.review_albums(
        options=BatchReviewOptions(missing_only=True),
        decide=lambda step: next(decisions),  # type: ignore[arg-type]
    )

    assert report.processed == 2
    assert report.applied == 1
    assert report.skipped == 1
    assert report.failed == 0
    assert apply_service.applied_summaries == [_german_summary()]
    assert report.job_path is not None
    assert Path(report.job_path).exists()


def test_batch_review_service_resumes_completed_items(tmp_path: Path) -> None:
    """Resume should skip albums recorded in the job progress file."""
    progress_store = BatchProgressStore(directory=tmp_path / "exports" / "jobs")
    progress = progress_store.load_or_create(library=None, missing_only=True, resume=False)
    progress_store.save(progress.mark_completed("1"))
    service = _service(
        tmp_path=tmp_path,
        candidates=[_candidate("1"), _candidate("2")],
        progress_store=progress_store,
    )

    report = service.review_albums(
        options=BatchReviewOptions(missing_only=True, resume=True),
        decide=lambda step: "SKIP",
    )

    assert report.processed == 1
    assert report.results[0].rating_key == "2"


def test_batch_review_service_supports_edit_before_apply(tmp_path: Path) -> None:
    """Editing should revalidate the summary and apply the edited text."""
    apply_service = FakeApplyService()
    service = _service(
        tmp_path=tmp_path,
        candidates=[_candidate("1")],
        apply_service=apply_service,
    )
    decisions = iter(["EDIT", "APPLY"])
    edited = _german_summary(prefix="Die bearbeitete Fassung")

    report = service.review_albums(
        options=BatchReviewOptions(missing_only=True),
        decide=lambda step: next(decisions),  # type: ignore[arg-type]
        edit=lambda document: edited,
    )

    assert report.applied == 1
    assert apply_service.applied_summaries == [edited]


def test_batch_review_service_uses_planner_actions(tmp_path: Path) -> None:
    """Batch review should select prompts and skip items from planner decisions."""
    review_service = FakeReviewService()
    service = BatchReviewService(
        album_source=FakeAlbumSource(
            [
                _candidate("1", summary="The album is a jazz recording with a reflective tone."),
                _candidate("2", summary="Das Album ist kurz."),
                _candidate("3", summary=" ".join(["Das Album ist gut und vollständig."] * 20)),
            ]
        ),
        review_service=review_service,  # type: ignore[arg-type]
        apply_service=FakeApplyService(),  # type: ignore[arg-type]
        progress_store=BatchProgressStore(directory=tmp_path / "exports" / "jobs"),
    )

    decisions = iter(["SKIP", "SKIP"])
    report = service.review_albums(
        options=BatchReviewOptions(missing_only=False),
        decide=lambda step: next(decisions),  # type: ignore[arg-type]
    )

    assert review_service.prompt_names == ["album_translate", "album_improve"]
    assert report.processed == 3
    assert report.skipped == 3
    assert report.results[2].message == "German summary already appears complete enough."


def test_batch_review_service_quit_stops_without_marking_item(tmp_path: Path) -> None:
    """Quit should stop the session and leave the current album unprocessed."""
    service = _service(tmp_path=tmp_path, candidates=[_candidate("1")])

    report = service.review_albums(
        options=BatchReviewOptions(missing_only=True),
        decide=lambda step: "QUIT",
    )

    assert report.quit_requested is True
    assert report.processed == 0


def test_plex_batch_album_source_filters_music_library(monkeypatch) -> None:
    """PlexBatchAlbumSource should enumerate albums from the selected music library."""
    monkeypatch.setattr("plex_music_enhancer.batch.service.PlexServer", FakePlexServer)

    source = PlexBatchAlbumSource("http://localhost:32400", SecretStr("token"))
    candidates = source.scan_albums(library="Music")

    assert len(candidates) == 1
    assert candidates[0].library == "Music"
    assert candidates[0].artist == "Nina Simone"
    assert candidates[0].album == "Pastel Blues"


class FakeAlbumSource:
    """Fake album source for batch service tests."""

    def __init__(self, candidates: list[BatchAlbumCandidate]) -> None:
        """Create a fake album source."""
        self._candidates = candidates

    def scan_albums(self, *, library: str | None = None) -> list[BatchAlbumCandidate]:
        """Return fake candidates."""
        if library is None:
            return self._candidates
        return [candidate for candidate in self._candidates if candidate.library == library]


class FakeReviewService:
    """Fake review service for batch tests."""

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
        return _review_document(artist=artist, album=album, summary=_german_summary())

    def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
        """Return a fake edited review document."""
        context = document.preview.context
        return _review_document(
            artist=context.plex.artist,
            album=context.plex.album,
            summary=edited_summary,
        )


class FakeApplyService:
    """Fake apply service for batch tests."""

    def __init__(self) -> None:
        """Create a fake apply service."""
        self.applied_summaries: list[str] = []

    def apply_review(self, review: ReviewDocument) -> ApplyResult:
        """Record and report an applied review."""
        self.applied_summaries.append(review.proposed_summary)
        context = review.preview.context
        return ApplyResult(
            status="SUCCESS",
            artist=context.plex.artist,
            album=context.plex.album,
            rating_key=context.plex.rating_key,
            backup_created=True,
            write_successful=True,
            verification_passed=True,
            audit_stored=True,
            backup_path="exports/backups/backup.json",
            audit_path="exports/audit/audit.json",
            message="Summary written and verified successfully.",
            review=review,
        )


class FakePlexAlbum:  # noqa: N801
    """Fake Plex album for source tests."""

    ratingKey = "42"  # noqa: N815
    title = "Pastel Blues"
    parentTitle = "Nina Simone"  # noqa: N815
    summary = None


class FakePlexSection:
    """Fake Plex library section."""

    def __init__(self, title: str, section_type: str) -> None:
        """Create a fake section."""
        self.title = title
        self.type = section_type

    def albums(self) -> list[FakePlexAlbum]:
        """Return fake albums."""
        return [FakePlexAlbum()]


class FakePlexLibrary:
    """Fake Plex library accessor."""

    def sections(self) -> list[FakePlexSection]:
        """Return fake sections."""
        return [
            FakePlexSection("Music", "artist"),
            FakePlexSection("Movies", "movie"),
        ]


class FakePlexServer:
    """Fake Plex server."""

    def __init__(self, base_url: str, token: str) -> None:
        """Create a fake Plex server."""
        self.base_url = base_url
        self.token = token
        self.library = FakePlexLibrary()


def _service(
    *,
    tmp_path: Path,
    candidates: list[BatchAlbumCandidate],
    apply_service: FakeApplyService | None = None,
    progress_store: BatchProgressStore | None = None,
) -> BatchReviewService:
    """Create a batch review service with fake dependencies."""
    return BatchReviewService(
        album_source=FakeAlbumSource(candidates),
        review_service=FakeReviewService(),  # type: ignore[arg-type]
        apply_service=apply_service or FakeApplyService(),  # type: ignore[arg-type]
        progress_store=progress_store
        or BatchProgressStore(directory=tmp_path / "exports" / "jobs"),
    )


def _candidate(rating_key: str, *, summary: str | None = None) -> BatchAlbumCandidate:
    """Create a batch candidate fixture."""
    return BatchAlbumCandidate(
        rating_key=rating_key,
        library="Music",
        artist="Nina Simone",
        album=f"Pastel Blues {rating_key}",
        current_summary=summary,
    )


def _review_document(*, artist: str, album: str, summary: str) -> ReviewDocument:
    """Create a review document fixture."""
    return ReviewDocument(
        preview=_preview_document(artist=artist, album=album, summary=summary),
        current_summary="",
        proposed_summary=summary,
        diff="--- current summary\n+++ generated summary\n",
        quality=QualityReport(
            status="PASS",
            checks={
                "not_empty": True,
                "language_is_german": True,
                "length_in_range": True,
                "no_markdown": True,
                "no_bullet_lists": True,
                "no_placeholder_text": True,
            },
            warnings=[],
            failures=[],
            word_count=90,
        ),
    )


def _preview_document(*, artist: str, album: str, summary: str) -> EnrichmentPreviewDocument:
    """Create a preview document fixture."""
    return EnrichmentPreviewDocument(
        context=_album_context(artist=artist, album=album),
        rendered_prompt=RenderedPrompt(
            name="album_summary",
            version="1.0",
            rendered_text="Prompt",
            variables={"artist": artist, "album": album, "language": "de"},
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
            metadata={},
        ),
        generation_time_seconds=0.25,
    )


def _album_context(*, artist: str, album: str) -> AlbumContext:
    """Create an album context fixture."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key=album.rsplit(" ", maxsplit=1)[-1],
            artist=artist,
            album=album,
            year=1965,
            summary=None,
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


def _german_summary(*, prefix: str = "Das Album ist") -> str:
    """Return deterministic German prose."""
    words = [
        *prefix.split(),
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
    return " ".join(words[index % len(words)] for index in range(90)) + "."
