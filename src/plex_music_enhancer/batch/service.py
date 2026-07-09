"""Sequential batch review service."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

from plex_music_enhancer.apply import ApplyResult, ApplyService
from plex_music_enhancer.batch.filters import filter_album_candidates
from plex_music_enhancer.batch.progress import BatchProgressStore
from plex_music_enhancer.planner import EnrichmentAction, EnrichmentPlan, EnrichmentPlanner
from plex_music_enhancer.review import ReviewDocument, ReviewService

BatchDecision = Literal["APPLY", "EDIT", "SKIP", "QUIT"]
BatchStepStatus = Literal["APPLIED", "SKIPPED", "FAILED"]


class BatchAlbumCandidate(BaseModel):
    """Album candidate for a batch review session."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    library: str
    artist: str
    album: str
    current_summary: str | None = Field(default=None, serialization_alias="currentSummary")


class BatchReviewOptions(BaseModel):
    """Options controlling a batch review run."""

    model_config = ConfigDict(frozen=True)

    library: str | None = None
    missing_only: bool = True
    limit: int | None = Field(default=None, ge=1)
    resume: bool = False


class BatchStepResult(BaseModel):
    """Result for one processed album."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    artist: str
    album: str
    library: str
    status: BatchStepStatus
    message: str
    apply_result: ApplyResult | None = Field(default=None, serialization_alias="applyResult")


class BatchReviewReport(BaseModel):
    """Summary report for a batch review session."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    processed: int = 0
    applied: int = 0
    skipped: int = 0
    failed: int = 0
    quit_requested: bool = Field(default=False, serialization_alias="quitRequested")
    job_path: str | None = Field(default=None, serialization_alias="jobPath")
    results: list[BatchStepResult] = Field(default_factory=list)
    average_quality_score: float | None = Field(
        default=None,
        serialization_alias="averageQualityScore",
    )
    lowest_quality_score: int | None = Field(
        default=None,
        serialization_alias="lowestQualityScore",
    )
    highest_quality_score: int | None = Field(
        default=None,
        serialization_alias="highestQualityScore",
    )
    albums_below_threshold: int = Field(default=0, serialization_alias="albumsBelowThreshold")
    albums_requiring_review: int = Field(default=0, serialization_alias="albumsRequiringReview")


class BatchReviewStep(BaseModel):
    """Interactive review step passed to CLI rendering and prompting."""

    model_config = ConfigDict(frozen=True)

    candidate: BatchAlbumCandidate
    plan: EnrichmentPlan
    review: ReviewDocument | None = None


class BatchReviewError(Exception):
    """Raised when a batch review session cannot run."""


class AlbumSource(Protocol):
    """Source of batch album candidates."""

    def scan_albums(self, *, library: str | None = None) -> list[BatchAlbumCandidate]:
        """Return candidate albums."""


DecisionCallback = Callable[[BatchReviewStep], BatchDecision]
DisplayCallback = Callable[[BatchReviewStep], None]
EditCallback = Callable[[ReviewDocument], str | None]


class BatchReviewService:
    """Run sequential interactive batch review sessions."""

    def __init__(
        self,
        *,
        album_source: AlbumSource,
        review_service: ReviewService,
        apply_service: ApplyService,
        progress_store: BatchProgressStore | None = None,
        planner: EnrichmentPlanner | None = None,
    ) -> None:
        """Create a batch review service."""
        self._album_source = album_source
        self._review_service = review_service
        self._apply_service = apply_service
        self._progress_store = progress_store or BatchProgressStore()
        self._planner = planner or EnrichmentPlanner()

    def review_albums(
        self,
        *,
        options: BatchReviewOptions,
        decide: DecisionCallback,
        display: DisplayCallback | None = None,
        edit: EditCallback | None = None,
    ) -> BatchReviewReport:
        """Run a sequential batch review session."""
        try:
            progress = self._progress_store.load_or_create(
                library=options.library,
                missing_only=options.missing_only,
                resume=options.resume,
            )
            candidates = self._album_source.scan_albums(library=options.library)
            selected = filter_album_candidates(
                candidates,
                missing_only=options.missing_only,
                limit=options.limit,
                completed_rating_keys=set(progress.completed_rating_keys),
            )
        except Exception as exc:
            msg = str(exc) or "Unable to prepare batch review."
            raise BatchReviewError(msg) from exc

        report = BatchReviewReport(job_path=str(self._progress_store.save(progress)))
        for candidate in selected:
            try:
                planned_album = self._planner.plan_album(candidate)
                plan = planned_album.plan
                if plan.action is EnrichmentAction.SKIP:
                    step_result = _skipped_result(candidate, message=plan.reason)
                    progress = progress.mark_completed(candidate.rating_key)
                    job_path = self._progress_store.save(progress)
                    report = _add_step_result(report, step_result, job_path)
                    continue

                if plan.action is EnrichmentAction.REVIEW:
                    step = BatchReviewStep(candidate=candidate, plan=plan)
                    if display is not None:
                        display(step)
                    decision = decide(step)
                    if decision == "QUIT":
                        return report.model_copy(update={"quit_requested": True})

                    step_result = _skipped_result(candidate, message=plan.reason)
                    progress = progress.mark_completed(candidate.rating_key)
                    job_path = self._progress_store.save(progress)
                    report = _add_step_result(report, step_result, job_path)
                    continue

                review = self._review_service.create_review(
                    artist=candidate.artist,
                    album=candidate.album,
                    prompt_name=_prompt_name_for_action(plan.action),
                )
                step = BatchReviewStep(candidate=candidate, plan=plan, review=review)
                if display is not None:
                    display(step)

                decision = decide(step)
                while decision == "EDIT":
                    if review is None:
                        decision = "SKIP"
                        break
                    if edit is None:
                        decision = "SKIP"
                        break
                    edited_summary = edit(review)
                    if edited_summary is None:
                        decision = decide(step)
                        continue
                    review = self._review_service.update_summary(review, edited_summary)
                    step = BatchReviewStep(candidate=candidate, plan=plan, review=review)
                    if display is not None:
                        display(step)
                    decision = decide(step)

                if decision == "QUIT":
                    return report.model_copy(update={"quit_requested": True})

                if decision == "APPLY":
                    step_result = self._apply_review(candidate, review)
                else:
                    step_result = _skipped_result(candidate)
            except Exception as exc:
                step_result = _failed_result(candidate, str(exc) or "Batch item failed.")

            progress = progress.mark_completed(candidate.rating_key)
            job_path = self._progress_store.save(progress)
            report = _add_step_result(report, step_result, job_path)

        return report

    def _apply_review(
        self,
        candidate: BatchAlbumCandidate,
        review: ReviewDocument,
    ) -> BatchStepResult:
        """Apply a reviewed summary and return a batch step result."""
        result = self._apply_service.apply_review(review)
        if result.status == "SUCCESS":
            return BatchStepResult(
                rating_key=candidate.rating_key,
                artist=candidate.artist,
                album=candidate.album,
                library=candidate.library,
                status="APPLIED",
                message=result.message,
                apply_result=result,
            )

        return BatchStepResult(
            rating_key=candidate.rating_key,
            artist=candidate.artist,
            album=candidate.album,
            library=candidate.library,
            status="FAILED",
            message=result.message,
            apply_result=result,
        )


class PlexBatchAlbumSource:
    """Read Plex album candidates for batch review."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex batch album source."""
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def scan_albums(self, *, library: str | None = None) -> list[BatchAlbumCandidate]:
        """Scan music libraries and return album candidates."""
        server = PlexServer(self._base_url, self._token.get_secret_value())
        sections = [
            section
            for section in server.library.sections()
            if _is_music_section(section)
            and (
                library is None
                or _normalize(getattr(section, "title", None)) == _normalize(library)
            )
        ]
        if library is not None and not sections:
            raise BatchReviewError(f'No music library named "{library}" was found.')

        return [
            _candidate_from_album(section, album)
            for section in sections
            for album in _safe_iterable(getattr(section, "albums", None))
        ]


def _add_step_result(
    report: BatchReviewReport,
    result: BatchStepResult,
    job_path: object,
) -> BatchReviewReport:
    """Return a report with one step result counted."""
    results = [*report.results, result]
    scores = _quality_scores(results)
    return report.model_copy(
        update={
            "processed": report.processed + 1,
            "applied": report.applied + (1 if result.status == "APPLIED" else 0),
            "skipped": report.skipped + (1 if result.status == "SKIPPED" else 0),
            "failed": report.failed + (1 if result.status == "FAILED" else 0),
            "job_path": str(job_path),
            "results": results,
            "average_quality_score": (
                round(sum(scores) / len(scores), 2) if scores else report.average_quality_score
            ),
            "lowest_quality_score": min(scores) if scores else report.lowest_quality_score,
            "highest_quality_score": max(scores) if scores else report.highest_quality_score,
            "albums_below_threshold": sum(1 for score in scores if score < 80),
            "albums_requiring_review": sum(1 for score in scores if score < 90),
        }
    )


def _quality_scores(results: list[BatchStepResult]) -> list[int]:
    """Return QA scores found in batch apply results."""
    scores: list[int] = []
    for result in results:
        qa_report = (
            result.apply_result.review.preview.qa_report
            if result.apply_result is not None
            and result.apply_result.review.preview.qa_report is not None
            else None
        )
        if qa_report is not None:
            scores.append(qa_report.overall_score)
    return scores


def _skipped_result(
    candidate: BatchAlbumCandidate, *, message: str = "Skipped by user."
) -> BatchStepResult:
    """Return a skipped result."""
    return BatchStepResult(
        rating_key=candidate.rating_key,
        artist=candidate.artist,
        album=candidate.album,
        library=candidate.library,
        status="SKIPPED",
        message=message,
    )


def _failed_result(candidate: BatchAlbumCandidate, message: str) -> BatchStepResult:
    """Return a failed result."""
    return BatchStepResult(
        rating_key=candidate.rating_key,
        artist=candidate.artist,
        album=candidate.album,
        library=candidate.library,
        status="FAILED",
        message=message,
    )


def _prompt_name_for_action(action: EnrichmentAction) -> str:
    """Return the prompt template for a planner action."""
    if action is EnrichmentAction.TRANSLATE:
        return "album_translate"
    if action is EnrichmentAction.IMPROVE:
        return "album_improve"

    return "album_summary"


def _candidate_from_album(section: Any, album: Any) -> BatchAlbumCandidate:
    """Create a batch candidate from a Plex album object."""
    return BatchAlbumCandidate(
        rating_key=str(getattr(album, "ratingKey", "")),
        library=str(getattr(section, "title", "Untitled")),
        artist=str(getattr(album, "parentTitle", "") or ""),
        album=str(getattr(album, "title", "Untitled")),
        current_summary=_optional_string(getattr(album, "summary", None)),
    )


def _is_music_section(section: Any) -> bool:
    """Return whether a Plex section is a music library."""
    section_type = getattr(section, "type", None) or getattr(section, "TYPE", None)
    return section_type == "artist"


def _normalize(value: object) -> str:
    """Normalize a user-facing title."""
    return str(value or "").strip().casefold()


def _safe_iterable(method: Any) -> list[Any]:
    """Call a Plex collection method and return a list."""
    if not callable(method):
        return []
    result = method()
    if result is None:
        return []
    return list(cast(Any, result))


def _optional_string(value: object) -> str | None:
    """Return a populated string value."""
    if value is None:
        return None

    text = str(value)
    return text or None
