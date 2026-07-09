"""Interactive review service."""

from __future__ import annotations

from re import findall, search, split

from plex_music_enhancer.editorial import GermanEditorialStyleEngine
from plex_music_enhancer.planner import EnrichmentPlanner
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
        planner: EnrichmentPlanner | None = None,
        style_engine: GermanEditorialStyleEngine | None = None,
        polish: bool = False,
    ) -> None:
        """Create a review service."""
        self._preview_service = preview_service
        self._limits = limits or ReviewLimits()
        self._planner = planner or EnrichmentPlanner()
        self._style_engine = style_engine or GermanEditorialStyleEngine()
        self._polish = polish

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
        artist = preview.context.plex.artist
        album = getattr(preview.context.plex, "album", None)
        if self._polish:
            style_result = self._style_engine.improve(
                proposed_summary,
                artist=artist,
                album=album,
            )
            final_summary = style_result.text
            style = style_result.diagnostics
        else:
            final_summary = proposed_summary
            style = self._style_engine.analyze(final_summary, artist=artist, album=album)

        return ReviewDocument(
            preview=preview,
            current_summary=current_summary,
            proposed_summary=final_summary,
            diff=unified_summary_diff(current_summary, final_summary),
            quality=validate_summary_quality(final_summary, limits=self._limits),
            style=style,
            edited=edited,
            plan=self._planner.plan_summary(current_summary),
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
        "varied_sentence_openings": not _has_repetitive_sentence_starts(text),
        "not_fact_list_style": not _has_fact_list_style(text),
        "natural_transitions": not _has_poor_transitions(text),
        "strong_opening": not _has_weak_opening(text),
        "complete_closing": not _has_abrupt_ending(text),
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
    if not checks["varied_sentence_openings"]:
        warnings.append("REPETITIVE_SENTENCE_STARTS: Summary repeats sentence openings.")
    if not checks["not_fact_list_style"]:
        warnings.append("FACT_LIST_STYLE: Summary reads like a metadata list.")
    if not checks["natural_transitions"]:
        warnings.append("POOR_TRANSITIONS: Summary lacks natural transitions.")
    if not checks["strong_opening"]:
        warnings.append("WEAK_OPENING: Summary opens with generic or weak phrasing.")
    if not checks["complete_closing"]:
        warnings.append("ABRUPT_ENDING: Summary ends abruptly or incompletely.")

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


def _sentences(text: str) -> list[str]:
    """Return sentence-like prose chunks."""
    return [sentence.strip() for sentence in split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _has_repetitive_sentence_starts(text: str) -> bool:
    """Return whether multiple sentences begin with the same phrase."""
    sentences = _sentences(text)
    if len(sentences) < 3:
        return False

    starts: list[str] = []
    for sentence in sentences:
        words = findall(r"\b[\wÄÖÜäöüß-]+\b", sentence.casefold())
        if len(words) >= 2:
            starts.append(" ".join(words[:2]))

    return any(starts.count(start) >= 3 for start in set(starts))


def _has_fact_list_style(text: str) -> bool:
    """Return whether prose resembles field/value metadata output."""
    field_labels = (
        "artist",
        "album",
        "jahr",
        "year",
        "genre",
        "genres",
        "label",
        "producer",
        "produzent",
        "komponist",
        "composer",
        "lyricist",
        "texter",
        "studio",
        "release",
        "veröffentlichung",
    )
    label_pattern = "|".join(field_labels)
    label_hits = findall(rf"(?im)(?:^|[.;]\s*)({label_pattern})\s*:", text)
    line_count = len([line for line in text.splitlines() if line.strip()])
    semicolon_density = text.count(";") >= 4 and len(_sentences(text)) <= 2
    return len(label_hits) >= 2 or (line_count >= 3 and len(label_hits) >= 1) or semicolon_density


def _has_poor_transitions(text: str) -> bool:
    """Return whether longer prose has no visible transitional language."""
    sentences = _sentences(text)
    if len(sentences) < 4:
        return False

    lowered = f" {text.casefold()} "
    transitions = (
        " außerdem ",
        " dabei ",
        " dadurch ",
        " damit ",
        " daneben ",
        " dennoch ",
        " zugleich ",
        " gleichzeitig ",
        " während ",
        " hingegen ",
        " insgesamt ",
        " außerdem ",
        " dagegen ",
        " später ",
        " zuvor ",
        " damit ",
        " so ",
    )
    return not any(transition in lowered for transition in transitions)


def _has_weak_opening(text: str) -> bool:
    """Return whether the first sentence starts with generic metadata phrasing."""
    sentences = _sentences(text)
    if len(sentences) < 2:
        return False

    first = sentences[0].casefold()
    weak_starts = (
        "das album ist ",
        "das album war ",
        "dies ist ",
        "es ist ",
        "bei dem album handelt es sich ",
        "in diesem text ",
    )
    return any(first.startswith(start) for start in weak_starts) or len(first.split()) < 6


def _has_abrupt_ending(text: str) -> bool:
    """Return whether the closing sentence appears incomplete or too abrupt."""
    sentences = _sentences(text)
    if len(sentences) < 2:
        return False

    stripped = text.rstrip()
    if stripped.endswith((",", ";", ":")):
        return True

    last = sentences[-1]
    words = findall(r"\b[\wÄÖÜäöüß-]+\b", last)
    abrupt_starts = ("es enthält", "enthält", "mit", "und")
    return len(words) < 6 or last.casefold().startswith(abrupt_starts)
