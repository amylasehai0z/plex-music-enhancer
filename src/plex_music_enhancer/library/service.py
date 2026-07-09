"""Full-library planning, review, apply, and reporting workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.apply import ApplyResult, ApplyService
from plex_music_enhancer.batch import AlbumSource, BatchAlbumCandidate, BatchDecision
from plex_music_enhancer.planner import (
    EnrichmentAction,
    EnrichmentPlan,
    EnrichmentPlanner,
    PlannedAlbum,
)
from plex_music_enhancer.review import ReviewDocument, ReviewService
from plex_music_enhancer.utils.files import write_text_atomic

LibraryReviewStatus = Literal["APPROVED", "SKIPPED", "APPLIED", "FAILED"]
ActionCounts = dict[EnrichmentAction, int]

GENERATION_ACTIONS = (
    EnrichmentAction.CREATE,
    EnrichmentAction.TRANSLATE,
    EnrichmentAction.IMPROVE,
)
SECONDS_PER_GENERATION = 30


class LibraryWorkflowError(Exception):
    """Raised when a library workflow cannot run."""


class LibraryActionSummary(BaseModel):
    """Grouped planner summary for one action."""

    model_config = ConfigDict(frozen=True)

    action: EnrichmentAction
    count: int = Field(ge=0)
    estimated_seconds: int = Field(ge=0, serialization_alias="estimatedSeconds")


class LibraryPlanReport(BaseModel):
    """Plan for an entire Plex music library."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    library: str | None = None
    total_albums: int = Field(ge=0, serialization_alias="totalAlbums")
    groups: list[LibraryActionSummary]
    albums: list[PlannedAlbum]
    estimated_processing_seconds: int = Field(
        ge=0,
        serialization_alias="estimatedProcessingSeconds",
    )


class LibraryReviewRecord(BaseModel):
    """Persistent result for one library review item."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    library: str
    artist: str
    album: str
    action: EnrichmentAction
    status: LibraryReviewStatus
    message: str
    quality_score: int = Field(ge=0, le=100, serialization_alias="qualityScore")
    generation_time_seconds: float | None = Field(
        default=None,
        ge=0.0,
        serialization_alias="generationTimeSeconds",
    )
    review: ReviewDocument | None = None
    apply_result: ApplyResult | None = Field(default=None, serialization_alias="applyResult")


class LibraryReviewSession(BaseModel):
    """Persistent full-library review session."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    library: str | None = None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    records: list[LibraryReviewRecord] = Field(default_factory=list)

    @property
    def completed_rating_keys(self) -> set[str]:
        """Return rating keys already handled in this session."""
        return {record.rating_key for record in self.records}


class LibraryReviewStep(BaseModel):
    """Interactive review step for one generated library item."""

    model_config = ConfigDict(frozen=True)

    candidate: BatchAlbumCandidate
    plan: EnrichmentPlan
    review: ReviewDocument


class LibraryReviewReport(BaseModel):
    """Summary report for review, apply, resume, and report commands."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    library: str | None = None
    albums_processed: int = Field(ge=0, serialization_alias="albumsProcessed")
    created: int = Field(ge=0)
    translated: int = Field(ge=0)
    improved: int = Field(ge=0)
    skipped: int = Field(ge=0)
    approved: int = Field(ge=0)
    applied: int = Field(ge=0)
    failed: int = Field(ge=0)
    quit_requested: bool = Field(default=False, serialization_alias="quitRequested")
    average_quality_score: float = Field(ge=0.0, serialization_alias="averageQualityScore")
    average_generation_time_seconds: float = Field(
        ge=0.0,
        serialization_alias="averageGenerationTimeSeconds",
    )
    session_path: str = Field(serialization_alias="sessionPath")
    records: list[LibraryReviewRecord] = Field(default_factory=list)


DisplayCallback = Callable[[LibraryReviewStep], None]
DecisionCallback = Callable[[LibraryReviewStep], BatchDecision]
EditCallback = Callable[[ReviewDocument], str | None]


class LibrarySessionStore:
    """Store full-library review sessions as JSON."""

    def __init__(self, directory: Path | str = Path("exports/library")) -> None:
        """Create a session store."""
        self._directory = Path(directory)

    def path_for(self, library: str | None) -> Path:
        """Return the session path for a library."""
        suffix = _safe_segment(library or "all")
        return self._directory / f"{suffix}-session.json"

    def load_or_create(self, *, library: str | None, resume: bool) -> LibraryReviewSession:
        """Load an existing session or create a new one."""
        path = self.path_for(library)
        if resume and path.exists():
            return LibraryReviewSession.model_validate_json(path.read_text(encoding="utf-8"))

        now = datetime.now(tz=UTC)
        return LibraryReviewSession(library=library, created_at=now, updated_at=now)

    def save(self, session: LibraryReviewSession) -> Path:
        """Persist a session and return its path."""
        path = self.path_for(session.library)
        updated = session.model_copy(update={"updated_at": datetime.now(tz=UTC)})
        write_text_atomic(path, updated.model_dump_json(indent=2) + "\n")
        return path


class LibraryWorkflowService:
    """Run full-library workflows from planning through apply."""

    def __init__(
        self,
        *,
        album_source: AlbumSource,
        review_service: ReviewService,
        apply_service: ApplyService,
        planner: EnrichmentPlanner | None = None,
        session_store: LibrarySessionStore | None = None,
    ) -> None:
        """Create a library workflow service."""
        self._album_source = album_source
        self._review_service = review_service
        self._apply_service = apply_service
        self._planner = planner or EnrichmentPlanner()
        self._session_store = session_store or LibrarySessionStore()

    def plan_library(self, *, library: str | None = None) -> LibraryPlanReport:
        """Plan all albums in a Plex music library."""
        try:
            planned = [
                self._planner.plan_album(candidate)
                for candidate in self._album_source.scan_albums(library=library)
            ]
        except Exception as exc:
            msg = str(exc) or "Unable to plan library."
            raise LibraryWorkflowError(msg) from exc

        counts = _count_actions(planned)
        groups = [
            LibraryActionSummary(
                action=action,
                count=counts.get(action, 0),
                estimated_seconds=_estimated_seconds(action, counts.get(action, 0)),
            )
            for action in EnrichmentAction
        ]
        estimated = sum(group.estimated_seconds for group in groups)
        return LibraryPlanReport(
            library=library,
            total_albums=len(planned),
            groups=groups,
            albums=planned,
            estimated_processing_seconds=estimated,
        )

    def review_library(
        self,
        *,
        library: str | None = None,
        resume: bool = False,
        display: DisplayCallback | None = None,
        decide: DecisionCallback,
        edit: EditCallback | None = None,
    ) -> LibraryReviewReport:
        """Generate and collect approved review items for a library."""
        try:
            session = self._session_store.load_or_create(library=library, resume=resume)
            candidates = self._album_source.scan_albums(library=library)
        except Exception as exc:
            msg = str(exc) or "Unable to prepare library review."
            raise LibraryWorkflowError(msg) from exc

        completed = session.completed_rating_keys
        records = list(session.records)
        quit_requested = False
        for candidate in _ordered_generation_candidates(candidates, self._planner):
            if candidate.rating_key in completed:
                continue

            try:
                planned = self._planner.plan_album(candidate)
                plan = planned.plan
                if plan.action not in GENERATION_ACTIONS:
                    continue

                review = self._review_service.create_review(
                    artist=candidate.artist,
                    album=candidate.album,
                    prompt_name=_prompt_name_for_action(plan.action),
                )
                step = LibraryReviewStep(candidate=candidate, plan=plan, review=review)
                if display is not None:
                    display(step)

                decision = decide(step)
                while decision == "EDIT":
                    if edit is None:
                        decision = "SKIP"
                        break
                    edited = edit(review)
                    if edited is None:
                        decision = decide(step)
                        continue
                    review = self._review_service.update_summary(review, edited)
                    step = LibraryReviewStep(candidate=candidate, plan=plan, review=review)
                    if display is not None:
                        display(step)
                    decision = decide(step)

                if decision == "QUIT":
                    quit_requested = True
                    break

                status: LibraryReviewStatus = "APPROVED" if decision == "APPLY" else "SKIPPED"
                message = (
                    "Approved for library apply." if status == "APPROVED" else "Skipped by user."
                )
                records.append(_record_from_step(step, status=status, message=message))
                completed.add(candidate.rating_key)
                self._session_store.save(session.model_copy(update={"records": records}))
            except Exception as exc:
                records.append(
                    _failed_record(
                        candidate=candidate,
                        action=self._planner.plan_album(candidate).plan.action,
                        message=str(exc) or "Library review item failed.",
                    )
                )
                completed.add(candidate.rating_key)
                self._session_store.save(session.model_copy(update={"records": records}))

        path = self._session_store.save(session.model_copy(update={"records": records}))
        return _report_from_records(
            library=library,
            records=records,
            session_path=path,
            quit_requested=quit_requested,
        )

    def apply_approved(self, *, library: str | None = None) -> LibraryReviewReport:
        """Apply every approved review item from a saved library session."""
        try:
            session = self._session_store.load_or_create(library=library, resume=True)
        except Exception as exc:
            msg = str(exc) or "Unable to load library session."
            raise LibraryWorkflowError(msg) from exc

        records: list[LibraryReviewRecord] = []
        for record in session.records:
            if record.status != "APPROVED" or record.review is None:
                records.append(record)
                continue

            try:
                result = self._apply_service.apply_review(record.review)
                status: LibraryReviewStatus = "APPLIED" if result.status == "SUCCESS" else "FAILED"
                records.append(
                    record.model_copy(
                        update={
                            "status": status,
                            "message": result.message,
                            "apply_result": result,
                        }
                    )
                )
            except Exception as exc:
                records.append(
                    record.model_copy(
                        update={
                            "status": "FAILED",
                            "message": str(exc) or "Library apply item failed.",
                        }
                    )
                )

        path = self._session_store.save(session.model_copy(update={"records": records}))
        return _report_from_records(library=library, records=records, session_path=path)

    def session_report(self, *, library: str | None = None) -> LibraryReviewReport:
        """Return a report for the saved library session."""
        try:
            session = self._session_store.load_or_create(library=library, resume=True)
        except Exception as exc:
            msg = str(exc) or "Unable to load library session."
            raise LibraryWorkflowError(msg) from exc

        return _report_from_records(
            library=library,
            records=session.records,
            session_path=self._session_store.path_for(library),
        )


def _ordered_generation_candidates(
    candidates: list[BatchAlbumCandidate],
    planner: EnrichmentPlanner,
) -> list[BatchAlbumCandidate]:
    """Return candidates ordered by generation action."""
    planned = [(candidate, planner.plan_album(candidate).plan.action) for candidate in candidates]
    ordered: list[BatchAlbumCandidate] = []
    for action in GENERATION_ACTIONS:
        ordered.extend(
            candidate for candidate, planned_action in planned if planned_action is action
        )
    return ordered


def _record_from_step(
    step: LibraryReviewStep,
    *,
    status: LibraryReviewStatus,
    message: str,
) -> LibraryReviewRecord:
    """Create a persistent record from an interactive step."""
    return LibraryReviewRecord(
        rating_key=step.candidate.rating_key,
        library=step.candidate.library,
        artist=step.candidate.artist,
        album=step.candidate.album,
        action=step.plan.action,
        status=status,
        message=message,
        quality_score=step.plan.quality.quality_score,
        generation_time_seconds=step.review.preview.generation_time_seconds,
        review=step.review,
    )


def _failed_record(
    *,
    candidate: BatchAlbumCandidate,
    action: EnrichmentAction,
    message: str,
) -> LibraryReviewRecord:
    """Create a failed record for an item."""
    return LibraryReviewRecord(
        rating_key=candidate.rating_key,
        library=candidate.library,
        artist=candidate.artist,
        album=candidate.album,
        action=action,
        status="FAILED",
        message=message,
        quality_score=0,
    )


def _report_from_records(
    *,
    library: str | None,
    records: list[LibraryReviewRecord],
    session_path: Path,
    quit_requested: bool = False,
) -> LibraryReviewReport:
    """Build an aggregate report from session records."""
    quality_scores = [record.quality_score for record in records if record.quality_score > 0]
    generation_times = [
        record.generation_time_seconds
        for record in records
        if record.generation_time_seconds is not None
    ]
    return LibraryReviewReport(
        library=library,
        albums_processed=len(records),
        created=_count_records(records, EnrichmentAction.CREATE),
        translated=_count_records(records, EnrichmentAction.TRANSLATE),
        improved=_count_records(records, EnrichmentAction.IMPROVE),
        skipped=sum(1 for record in records if record.status == "SKIPPED"),
        approved=sum(1 for record in records if record.status == "APPROVED"),
        applied=sum(1 for record in records if record.status == "APPLIED"),
        failed=sum(1 for record in records if record.status == "FAILED"),
        quit_requested=quit_requested,
        average_quality_score=_average(quality_scores),
        average_generation_time_seconds=_average(generation_times),
        session_path=str(session_path),
        records=records,
    )


def _count_actions(planned: list[PlannedAlbum]) -> ActionCounts:
    """Count planned albums by action."""
    counts: ActionCounts = dict.fromkeys(EnrichmentAction, 0)
    for album in planned:
        counts[album.plan.action] += 1
    return counts


def _count_records(records: list[LibraryReviewRecord], action: EnrichmentAction) -> int:
    """Count records for one action."""
    return sum(1 for record in records if record.action is action)


def _estimated_seconds(action: EnrichmentAction, count: int) -> int:
    """Estimate processing seconds for a planner action."""
    return count * SECONDS_PER_GENERATION if action in GENERATION_ACTIONS else 0


def _average(values: list[float | int]) -> float:
    """Return a rounded average."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _prompt_name_for_action(action: EnrichmentAction) -> str:
    """Return the prompt template for a planner action."""
    if action is EnrichmentAction.TRANSLATE:
        return "album_translate"
    if action is EnrichmentAction.IMPROVE:
        return "album_improve"

    return "album_summary"


def _safe_segment(value: str) -> str:
    """Return a filesystem-safe segment."""
    return "".join(char if char.isalnum() or char in "._-" else "-" for char in value).strip("-")
