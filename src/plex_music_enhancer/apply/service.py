"""Orchestration for safely applying generated summaries to Plex."""

from __future__ import annotations

from typing import Any, Protocol

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

from plex_music_enhancer.apply.audit import ApplyAuditRecord, AuditStore
from plex_music_enhancer.apply.backup import BackupStore, SummaryBackup
from plex_music_enhancer.apply.verification import (
    PlexWriteError,
    VerificationResult,
    verify_album_summary,
    write_album_summary,
)
from plex_music_enhancer.review import ReviewDocument, ReviewService, evaluate_review_policy


class ApplyError(Exception):
    """Raised when an apply workflow cannot be prepared."""


class ApplyResult(BaseModel):
    """Complete result of one apply attempt."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    status: str
    artist: str
    album: str
    rating_key: str = Field(serialization_alias="ratingKey")
    backup_created: bool = Field(serialization_alias="backupCreated")
    write_successful: bool = Field(serialization_alias="writeSuccessful")
    verification_passed: bool = Field(serialization_alias="verificationPassed")
    audit_stored: bool = Field(serialization_alias="auditStored")
    backup_path: str | None = Field(default=None, serialization_alias="backupPath")
    audit_path: str | None = Field(default=None, serialization_alias="auditPath")
    message: str
    review: ReviewDocument
    backup: SummaryBackup | None = None
    verification: VerificationResult | None = None
    audit: ApplyAuditRecord | None = None


class _AlbumLoader(Protocol):
    """Callable that returns a mutable Plex album object by rating key."""

    def __call__(self, rating_key: str) -> Any:
        """Load a Plex album object."""


class ApplyService:
    """Apply a generated album summary with backup, verification, and audit logging."""

    def __init__(
        self,
        *,
        review_service: ReviewService,
        base_url: AnyHttpUrl,
        token: SecretStr,
        backup_store: BackupStore | None = None,
        audit_store: AuditStore | None = None,
        album_loader: _AlbumLoader | None = None,
        minimum_quality_score: int | None = None,
        verification_confidence_threshold: float = 0.7,
        force_quality: bool = False,
    ) -> None:
        """Create an apply service."""
        self._review_service = review_service
        self._backup_store = backup_store or BackupStore()
        self._audit_store = audit_store or AuditStore()
        self._album_loader = album_loader or _PlexAlbumLoader(base_url, token)
        self._minimum_quality_score = minimum_quality_score
        self._verification_confidence_threshold = verification_confidence_threshold
        self._force_quality = force_quality

    def apply_album_summary(
        self,
        *,
        artist: str,
        album: str,
        prompt_name: str = "album_summary",
    ) -> ApplyResult:
        """Generate, validate, back up, write, verify, and audit one album summary."""
        try:
            review = (
                self._review_service.create_review(artist=artist, album=album)
                if prompt_name == "album_summary"
                else self._review_service.create_review(
                    artist=artist,
                    album=album,
                    prompt_name=prompt_name,
                )
            )
        except Exception as exc:
            msg = str(exc) or "Unable to create review document."
            raise ApplyError(msg) from exc

        return self.apply_review(review)

    def apply_artist_summary(self, *, artist: str) -> ApplyResult:
        """Generate, validate, back up, write, verify, and audit one artist biography."""
        try:
            review = self._review_service.create_artist_review(artist=artist)
        except Exception as exc:
            msg = str(exc) or "Unable to create artist review document."
            raise ApplyError(msg) from exc

        return self.apply_review(review)

    def apply_review(self, review: ReviewDocument) -> ApplyResult:
        """Apply an already-reviewed summary without regenerating it."""
        policy = evaluate_review_policy(
            review,
            editorial_score_threshold=85,
            verification_confidence_threshold=self._verification_confidence_threshold,
        )
        if not policy.apply_allowed:
            message = (
                policy.messages[0]
                if policy.messages
                else "Generated summary did not pass critical validation."
            )
            return self._failed_without_write(
                review=review,
                message=(f"{message} No backup was created and Plex was not modified."),
            )
        qa_report = getattr(review.preview, "qa_report", None)
        if (
            self._minimum_quality_score is not None
            and qa_report is not None
            and qa_report.overall_score < self._minimum_quality_score
            and not self._force_quality
        ):
            return self._failed_without_write(
                review=review,
                message=(
                    f"Apply aborted. Minimum quality: {self._minimum_quality_score}. "
                    f"Current quality: {qa_report.overall_score}."
                ),
            )

        context = review.preview.context
        generated = review.preview.generated_summary
        prompt = review.preview.rendered_prompt
        artist_name = context.plex.artist
        album_name = getattr(context.plex, "album", "artist")
        try:
            backup = self._backup_store.create_backup(review)
        except Exception as exc:
            return self._failed_without_write(
                review=review,
                message=f"Unable to create backup. Plex was not modified: {exc}",
            )

        message = "Summary written and verified successfully."
        write_successful = False
        verification: VerificationResult | None = None

        try:
            album_object = self._album_loader(context.plex.rating_key)
            write_album_summary(album_object, review.proposed_summary)
            write_successful = True
            verification = verify_album_summary(album_object, review.proposed_summary)
            if not verification.passed:
                message = "Summary write completed, but verification failed after reload."
        except Exception as exc:
            message = str(exc) or "Summary write failed."
            if not isinstance(exc, PlexWriteError):
                message = f"Summary write failed: {message}"

        status = (
            "SUCCESS"
            if write_successful and verification is not None and verification.passed
            else "FAILED"
        )
        try:
            audit = self._audit_store.create_record(
                status=status,
                artist=artist_name,
                album=album_name,
                rating_key=context.plex.rating_key,
                provider=generated.provider,
                model=generated.model,
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                quality_status=review.quality.status,
                backup_path=backup.path,
                write_successful=write_successful,
                verification_passed=verification.passed if verification is not None else False,
                expected_summary=review.proposed_summary,
                verified_summary=verification.actual_summary if verification is not None else None,
                message=message,
            )
            audit_stored = True
        except Exception as exc:
            audit = None
            audit_stored = False
            status = "FAILED"
            message = f"{message} Audit storage failed: {exc}"

        return ApplyResult(
            status=status,
            artist=artist_name,
            album=album_name,
            rating_key=context.plex.rating_key,
            backup_created=True,
            write_successful=write_successful,
            verification_passed=verification.passed if verification is not None else False,
            audit_stored=audit_stored,
            backup_path=backup.path,
            audit_path=audit.path if audit is not None else None,
            message=message,
            review=review,
            backup=backup,
            verification=verification,
            audit=audit,
        )

    def _failed_without_write(self, *, review: ReviewDocument, message: str) -> ApplyResult:
        """Return a failure result for quality-gated summaries before any write."""
        context = review.preview.context
        album_name = getattr(context.plex, "album", "artist")
        return ApplyResult(
            status="FAILED",
            artist=context.plex.artist,
            album=album_name,
            rating_key=context.plex.rating_key,
            backup_created=False,
            write_successful=False,
            verification_passed=False,
            audit_stored=False,
            backup_path=None,
            audit_path=None,
            message=message,
            review=review,
        )


class _PlexAlbumLoader:
    """Load mutable Plex album objects by rating key."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex album loader."""
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def __call__(self, rating_key: str) -> Any:
        """Fetch an album object from Plex by rating key."""
        server = PlexServer(self._base_url, self._token.get_secret_value())
        fetch_item = getattr(server, "fetchItem", None)
        if not callable(fetch_item):
            raise ApplyError("Plex server does not support fetchItem().")

        return fetch_item(rating_key)
