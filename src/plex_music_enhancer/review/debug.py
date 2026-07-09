"""Temporary debug logging for interactive review runs."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from rich.console import Console

from plex_music_enhancer.review.models import ReviewDocument
from plex_music_enhancer.review.renderer import ReviewRenderer

REVIEW_DEBUG_LOG_PATH = Path("/tmp/plex_review.log")  # noqa: S108 - requested debug path.
PROMPT_DEBUG_DUMP_PATH = Path("/tmp/openai_prompt.txt")  # noqa: S108 - requested debug path.


@dataclass(frozen=True)
class ReviewDebugContext:
    """Command context included in the temporary review debug log."""

    artist: str
    album: str | None = None
    provider: str | None = None
    model: str | None = None


class ReviewDebugLogger:
    """Write a temporary plain-text copy of the current review screen."""

    def __init__(
        self,
        *,
        path: Path = REVIEW_DEBUG_LOG_PATH,
        prompt_dump_path: Path = PROMPT_DEBUG_DUMP_PATH,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Create a debug logger."""
        self._path = path
        self._prompt_dump_path = prompt_dump_path
        self._clock = clock or (lambda: datetime.now(UTC))

    def write(self, document: ReviewDocument, context: ReviewDebugContext) -> None:
        """Write the current review document to the debug log, ignoring file errors."""
        with suppress(OSError):
            self._path.write_text(
                self.render(document, context),
                encoding="utf-8",
            )

    def render(self, document: ReviewDocument, context: ReviewDebugContext) -> str:
        """Return the debug log text for a review document."""
        rendered_sections = [
            _separator(),
            f"Timestamp: {self._clock().isoformat()}",
            self._render_command_context(document, context),
            _separator(),
            "",
            "=== DIAGNOSTICS ====================================================",
            self._render_diagnostics(document),
            "",
            "=== PROMPT =========================================================",
            self._prompt_text(document),
            "",
            "=== CURRENT SUMMARY ===============================================",
            document.current_summary or "No current summary.",
            "",
            "=== GENERATED SUMMARY =============================================",
            document.proposed_summary or "No generated summary.",
            "",
            "=== UNIFIED DIFF ==================================================",
            self._capture(lambda renderer: renderer.render_diff(document)),
            "",
            "=== QUALITY ========================================================",
            self._capture(lambda renderer: _render_quality_sections(renderer, document)),
            "",
            "=== STYLE ANALYSIS =================================================",
            self._capture(lambda renderer: renderer.render_style(document)),
            "",
            "=== EDITORIAL QUALITY =============================================",
            self._capture(lambda renderer: renderer.render_editorial_quality(document)),
            "",
            "=== VERIFICATION ===================================================",
            self._capture(lambda renderer: renderer.render_verification(document)),
            "",
        ]
        return "\n".join(rendered_sections)

    def _render_command_context(
        self,
        document: ReviewDocument,
        context: ReviewDebugContext,
    ) -> str:
        """Return the command context section."""
        generated = document.preview.generated_summary
        prompt = document.preview.rendered_prompt
        values = {
            "target": "album" if context.album else "artist",
            "review_mode": prompt.name,
            "artist": context.artist,
            "album": context.album or "n/a",
            "provider": context.provider or generated.provider,
            "model": context.model or generated.model,
        }
        return "Command context: " + ", ".join(f"{name}={value}" for name, value in values.items())

    def _render_diagnostics(self, document: ReviewDocument) -> str:
        """Return available generation, prompt, QA, and context diagnostics."""
        prompt = document.preview.rendered_prompt
        generated = document.preview.generated_summary
        metadata = generated.metadata
        qa_report = getattr(document.preview, "qa_report", None)
        budget = prompt.budget_diagnostics or {}
        diagnostics = {
            "prompt_characters": len(prompt.rendered_text),
            "estimated_prompt_tokens": _estimate_tokens(prompt.rendered_text),
            "response_characters": len(generated.text),
            "response_words": len(generated.text.split()),
            "generation_time_seconds": f"{document.preview.generation_time_seconds:.3f}",
            "prompt_tokens": metadata.get("prompt_tokens", "not reported"),
            "completion_tokens": metadata.get("completion_tokens", "not reported"),
            "finish_reason": metadata.get("finish_reason", "not reported"),
            "qa_overall_score": getattr(qa_report, "overall_score", "not available"),
            "editorial_level": _editorial_level(qa_report),
            "review_status": document.quality.status,
            "publishable": document.quality.publishable,
            "prompt_budget": budget.get("max_characters", "not reported"),
            "prompt_trimmed_size": budget.get("final_size", "not reported"),
        }
        return "\n".join(f"{name}: {value}" for name, value in diagnostics.items())

    def _prompt_text(self, document: ReviewDocument) -> str:
        """Return the exact current prompt text, preferring the OpenAI dump when current."""
        prompt = document.preview.rendered_prompt.rendered_text
        with suppress(OSError):
            dumped_prompt = self._prompt_dump_path.read_text(encoding="utf-8")
            if dumped_prompt == prompt:
                return dumped_prompt
        return prompt

    def _capture(self, render: Callable[[ReviewRenderer], None]) -> str:
        """Capture existing Rich review rendering as plain text."""
        capture_console = Console(
            file=StringIO(),
            record=True,
            color_system=None,
            width=120,
        )
        renderer = ReviewRenderer(capture_console)
        render(renderer)
        text = capture_console.export_text(clear=True).strip()
        return text or "Not available."


def _render_quality_sections(renderer: ReviewRenderer, document: ReviewDocument) -> None:
    """Render the same quality sections shown in the interactive review."""
    renderer.render_quality(document.quality)
    renderer.render_policy_summary(document)


def _separator() -> str:
    """Return the debug log separator."""
    return "=" * 79


def _estimate_tokens(text: str) -> int:
    """Return a conservative local token estimate for debug output."""
    return max(1, round(len(text) / 4)) if text else 0


def _editorial_level(report: object | None) -> str:
    """Return a readable editorial QA level."""
    if report is None:
        return "not available"
    level = getattr(report, "overall_level", None) or getattr(report, "quality_level", None)
    return getattr(level, "value", str(level)) if level is not None else "UNKNOWN"
