"""Interactive review service."""

from __future__ import annotations

from re import search

from plex_music_enhancer.review.diff import unified_summary_diff
from plex_music_enhancer.review.models import QualityReport, ReviewDocument, ReviewLimits
from plex_music_enhancer.services import (
    EnrichmentPreviewDocument,
    EnrichmentPreviewService,
    PreviewError,
)


class ReviewError(Exception):
    """Raised when a review document cannot be created."""


class ReviewService:
    """Build and update read-only summary review documents."""

    def __init__(
        self,
        *,
        preview_service: EnrichmentPreviewService,
        limits: ReviewLimits | None = None,
    ) -> None:
        """Create a review service."""
        self._preview_service = preview_service
        self._limits = limits or ReviewLimits()

    def create_review(
        self,
        *,
        artist: str,
        album: str,
        prompt_name: str = "album_summary",
    ) -> ReviewDocument:
        """Create a review document for one generated album summary."""
        try:
            preview = (
                self._preview_service.preview_album(artist=artist, album=album)
                if prompt_name == "album_summary"
                else self._preview_service.preview_album(
                    artist=artist,
                    album=album,
                    prompt_name=prompt_name,
                )
            )
        except PreviewError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to create review."
            raise ReviewError(msg) from exc

        return self._document_from_preview(preview, preview.generated_summary.text, edited=False)

    def create_artist_review(self, *, artist: str) -> ReviewDocument:
        """Create a review document for one generated artist biography."""
        try:
            preview = self._preview_service.preview_artist(artist=artist)
        except PreviewError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to create artist review."
            raise ReviewError(msg) from exc

        return self._document_from_preview(preview, preview.generated_summary.text, edited=False)

    def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
        """Return a new review document with edited summary text."""
        return self._document_from_preview(document.preview, edited_summary, edited=True)

    def _document_from_preview(
        self,
        preview: EnrichmentPreviewDocument,
        proposed_summary: str,
        *,
        edited: bool,
    ) -> ReviewDocument:
        """Build a review document from preview output and proposed text."""
        current_summary = preview.context.plex.summary or ""
        return ReviewDocument(
            preview=preview,
            current_summary=current_summary,
            proposed_summary=proposed_summary,
            diff=unified_summary_diff(current_summary, proposed_summary),
            quality=validate_summary_quality(proposed_summary, limits=self._limits),
            edited=edited,
        )


def validate_summary_quality(summary: str, *, limits: ReviewLimits | None = None) -> QualityReport:
    """Validate generated or edited summary quality."""
    selected_limits = limits or ReviewLimits()
    text = summary.strip()
    word_count = len(text.split()) if text else 0
    checks = {
        "not_empty": bool(text),
        "language_is_german": _looks_german(text),
        "length_in_range": (
            selected_limits.minimum_words <= word_count <= selected_limits.maximum_words
        ),
        "no_markdown": not _has_markdown(text),
        "no_bullet_lists": not _has_bullet_list(text),
        "no_placeholder_text": not _has_placeholder_text(text),
    }

    failures: list[str] = []
    warnings: list[str] = []
    if not checks["not_empty"]:
        failures.append("Summary is empty.")
    if not checks["no_markdown"]:
        failures.append("Summary contains Markdown formatting.")
    if not checks["no_bullet_lists"]:
        failures.append("Summary contains bullet lists.")
    if not checks["no_placeholder_text"]:
        failures.append("Summary contains placeholder text.")
    if not checks["language_is_german"]:
        warnings.append("Summary does not appear to be German.")
    if not checks["length_in_range"]:
        warnings.append(
            "Summary length is outside the configured range "
            f"({selected_limits.minimum_words}-{selected_limits.maximum_words} words)."
        )

    if failures:
        status = "FAILED"
    elif warnings:
        status = "WARNINGS"
    else:
        status = "PASS"

    return QualityReport(
        status=status,
        checks=checks,
        warnings=warnings,
        failures=failures,
        word_count=word_count,
    )


def _looks_german(text: str) -> bool:
    """Return whether text has simple German-language signals."""
    lowered = f" {text.casefold()} "
    markers = [
        " der ",
        " die ",
        " das ",
        " und ",
        " ist ",
        " mit ",
        " ein ",
        " eine ",
        " album ",
    ]
    return any(marker in lowered for marker in markers) or any(char in text for char in "äöüÄÖÜß")


def _has_markdown(text: str) -> bool:
    """Return whether text appears to contain Markdown formatting."""
    return bool(search(r"(^|\s)(#{1,6}\s|\*\*|__|`|>\s)", text))


def _has_bullet_list(text: str) -> bool:
    """Return whether text contains Markdown-like bullet lists."""
    return bool(search(r"(?m)^\s*([-*+]|\d+\.)\s+", text))


def _has_placeholder_text(text: str) -> bool:
    """Return whether text contains common placeholder markers."""
    lowered = text.casefold()
    placeholders = [
        "placeholder",
        "lorem ipsum",
        "todo",
        "tbd",
        "dummyprovider",
        "{{",
        "}}",
    ]
    return any(marker in lowered for marker in placeholders)
