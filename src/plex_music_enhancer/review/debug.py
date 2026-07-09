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


@dataclass(frozen=True)
class _CoverageRow:
    """One evidence topic and whether it reached the generated output."""

    label: str
    available: bool
    covered: bool


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
            "=== PROMPT BUDGET ==================================================",
            self._render_prompt_budget(document),
            "",
            "=== USED SOURCES ===================================================",
            self._render_used_sources(document),
            "",
            "=== PROMPT DECISIONS ===============================================",
            self._render_prompt_decisions(document),
            "",
            "=== EVIDENCE RANKING ===============================================",
            self._render_evidence_ranking(document),
            "",
            "=== PROMPT QUALITY =================================================",
            self._render_prompt_quality(document),
            "",
            "=== EDITORIAL COVERAGE =============================================",
            self._render_editorial_coverage(document),
            "",
            "=== EVIDENCE COVERAGE ==============================================",
            self._render_evidence_coverage(document),
            "",
            "=== EDITORIAL BALANCE ==============================================",
            self._render_editorial_balance(document),
            "",
            "=== PROMPT UTILIZATION =============================================",
            self._render_prompt_utilization(document),
            "",
            "=== PROMPT META ====================================================",
            self._render_prompt_meta(document),
            "",
            "=== RESPONSE META ==================================================",
            self._render_response_meta(document),
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

    def _render_prompt_budget(self, document: ReviewDocument) -> str:
        """Return grouped prompt budget diagnostics."""
        diagnostics = document.preview.rendered_prompt.budget_diagnostics or {}
        breakdown = diagnostics.get("budget_breakdown")
        if not isinstance(breakdown, dict):
            return "Not reported."
        lines = []
        for name, values in breakdown.items():
            if not isinstance(values, dict):
                continue
            lines.append(
                f"{name}: {values.get('characters', 0)} chars, "
                f"{values.get('estimated_tokens', 0)} tokens, "
                f"{values.get('percentage', 0)}%"
            )
        return "\n".join(lines) if lines else "Not reported."

    def _render_used_sources(self, document: ReviewDocument) -> str:
        """Return source availability based on prompt variables."""
        variables = document.preview.rendered_prompt.variables
        metadata = variables.get("additional_metadata", "")
        sources = {
            "Verified metadata": "Verified facts:" in metadata,
            "Wikipedia": _has_content(variables.get("wikipedia_extract"), "No reference extract"),
            "Discogs": "Discogs unique context:" in metadata,
            "Last.fm": "Last.fm style context:" in metadata,
            "Existing Plex biography": _has_content(variables.get("current_summary"), "No current"),
        }
        return "\n".join(
            f"{source}: {'used' if used else 'omitted'}" for source, used in sources.items()
        )

    def _render_editorial_coverage(self, document: ReviewDocument) -> str:
        """Return editorial evidence coverage for generated output."""
        rows = _coverage_rows(document)
        available = [row.label for row in rows if row.available]
        covered = [row.label for row in rows if row.available and row.covered]
        missed = [row.label for row in rows if row.available and not row.covered]
        sections = [
            "Evidence available",
            *[f"✓ {label}" for label in available],
            "",
            "Output coverage",
            *[f"{'✓' if row.covered else '✗'} {row.label}" for row in rows if row.available],
            "",
            "Missed opportunities",
            *list(missed),
        ]
        if not available:
            sections.append("No editorial evidence supplied.")
        if not missed:
            sections.append("None.")
        if covered:
            sections.insert(0, f"Covered evidence: {len(covered)}/{len(available)}")
        return "\n".join(sections)

    def _render_prompt_utilization(self, document: ReviewDocument) -> str:
        """Return high-level prompt utilization diagnostics."""
        prompt = document.preview.rendered_prompt
        rows = _coverage_rows(document)
        missed = [row.label for row in rows if row.available and not row.covered]
        evidence_sections = sum(
            1
            for value in prompt.variables.values()
            if value and not value.startswith("No ") and len(value) > 10
        )
        used = "HIGH" if not missed else ("MEDIUM" if len(missed) <= 2 else "LOW")
        lines = [
            f"Prompt size: {len(prompt.rendered_text)} characters",
            f"Estimated tokens: {_estimate_tokens(prompt.rendered_text)}",
            f"Evidence sections: {evidence_sections}",
            f"Evidence used: {used}",
        ]
        lines.extend(f"Unused evidence: {item}" for item in missed)
        return "\n".join(lines)

    def _render_prompt_decisions(self, document: ReviewDocument) -> str:
        """Return explainable prompt decisions from budget diagnostics."""
        diagnostics = document.preview.rendered_prompt.budget_diagnostics or {}
        decisions = diagnostics.get("prompt_decisions")
        if not isinstance(decisions, dict):
            decisions = {
                "included": ["Not reported."],
                "removed": ["Not reported."],
                "trimmed": ["Not reported."],
            }
        sections = []
        for title, key, marker in (
            ("Included", "included", "✓"),
            ("Removed", "removed", "-"),
            ("Trimmed", "trimmed", "-"),
        ):
            values = decisions.get(key)
            sections.append(title)
            if isinstance(values, list) and values:
                sections.extend(f"{marker} {value}" for value in values)
            else:
                sections.append("None.")
            sections.append("")
        return "\n".join(sections).strip()

    def _render_evidence_ranking(self, document: ReviewDocument) -> str:
        """Return ranked evidence scores from prompt diagnostics."""
        diagnostics = document.preview.rendered_prompt.budget_diagnostics or {}
        ranking = diagnostics.get("evidence_ranking")
        if not isinstance(ranking, dict) or not ranking:
            return "Not reported."
        return "\n".join(f"{name}: {score}" for name, score in ranking.items())

    def _render_prompt_quality(self, document: ReviewDocument) -> str:
        """Return prompt quality diagnostics from budget analysis."""
        diagnostics = document.preview.rendered_prompt.budget_diagnostics or {}
        quality = diagnostics.get("prompt_quality")
        if not isinstance(quality, dict):
            quality = {}
        rows = (
            ("Prompt redundancy", "prompt_redundancy"),
            ("Evidence diversity", "evidence_diversity"),
            ("Historical coverage", "historical_coverage"),
            ("Career coverage", "career_coverage"),
            ("Legacy coverage", "legacy_coverage"),
            ("Source balance", "source_balance"),
            ("Prompt efficiency", "prompt_efficiency"),
            ("Information density", "information_density"),
        )
        lines = [f"{label}: {quality.get(key, 'not reported')}" for label, key in rows]
        reason = quality.get("prompt_efficiency_reason")
        if reason:
            lines.append(f"Prompt efficiency reason: {reason}")
        return "\n".join(lines)

    def _render_evidence_coverage(self, document: ReviewDocument) -> str:
        """Return how much high-value evidence reached the generated output."""
        rows = _high_value_coverage_rows(document)
        available = [row for row in rows if row.available]
        covered = [row for row in available if row.covered]
        coverage = round((len(covered) / len(available)) * 100) if available else 100
        lines = [
            f"High-value evidence: {len(available)}",
            f"Used: {len(covered)}",
            f"Coverage: {coverage}%",
        ]
        missed = [row.label for row in available if not row.covered]
        lines.extend(f"Missed: {label}" for label in missed)
        return "\n".join(lines)

    def _render_editorial_balance(self, document: ReviewDocument) -> str:
        """Return balance diagnostics for the generated biography."""
        rows = _editorial_balance_rows(document.proposed_summary)
        scores = [score for _, score in rows]
        overall_score = round(sum(scores) / len(scores)) if scores else 0
        lines = [f"{label}: {_quality_label(score)}" for label, score in rows]
        lines.append(f"Overall: {_quality_label(overall_score)}")
        return "\n".join(lines)

    def _render_prompt_meta(self, document: ReviewDocument) -> str:
        """Return prompt metadata."""
        prompt = document.preview.rendered_prompt
        diagnostics = prompt.budget_diagnostics or {}
        return "\n".join(
            [
                f"name: {prompt.name}",
                f"version: {prompt.version}",
                f"characters: {len(prompt.rendered_text)}",
                f"estimated_tokens: {_estimate_tokens(prompt.rendered_text)}",
                f"budget: {diagnostics.get('max_characters', 'not reported')}",
                f"trimmed: {diagnostics.get('trimmed', 'not reported')}",
            ]
        )

    def _render_response_meta(self, document: ReviewDocument) -> str:
        """Return generated response metadata."""
        generated = document.preview.generated_summary
        metadata = generated.metadata
        return "\n".join(
            [
                f"provider: {generated.provider}",
                f"model: {generated.model}",
                f"characters: {len(generated.text)}",
                f"words: {len(generated.text.split())}",
                f"prompt_tokens: {metadata.get('prompt_tokens', 'not reported')}",
                f"completion_tokens: {metadata.get('completion_tokens', 'not reported')}",
                f"finish_reason: {metadata.get('finish_reason', 'not reported')}",
            ]
        )

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


def _coverage_rows(document: ReviewDocument) -> list[_CoverageRow]:
    """Return coverage rows comparing supplied evidence with generated output."""
    prompt_text = document.preview.rendered_prompt.rendered_text
    response = document.proposed_summary
    return [
        _CoverageRow(
            label=label,
            available=_contains_any(prompt_text, keywords),
            covered=_contains_any(response, keywords),
        )
        for label, keywords in _COVERAGE_TOPICS.items()
    ]


def _high_value_coverage_rows(document: ReviewDocument) -> list[_CoverageRow]:
    """Return coverage rows for the highest-value editorial topics."""
    rows = _coverage_rows(document)
    high_value = {
        "Historical significance",
        "Important works",
        "Career progression",
        "Later career",
        "Comeback",
        "Legacy",
        "International significance",
    }
    return [row for row in rows if row.label in high_value]


def _editorial_balance_rows(text: str) -> list[tuple[str, int]]:
    """Return balance scores for major biography dimensions."""
    return [
        ("Opening", _balance_score(text, ("ist", "war", "gruppe", "band", "künstler"))),
        ("Musical profile", _balance_score(text, _COVERAGE_TOPICS["Musical profile"])),
        ("Career", _balance_score(text, _COVERAGE_TOPICS["Career progression"])),
        ("Major works", _balance_score(text, _COVERAGE_TOPICS["Important works"])),
        ("Later development", _balance_score(text, _COVERAGE_TOPICS["Later career"])),
        ("Legacy", _balance_score(text, _COVERAGE_TOPICS["Legacy"])),
    ]


def _balance_score(text: str, keywords: tuple[str, ...]) -> int:
    """Return a readable 0-100 balance score for one topic."""
    lowered = text.casefold()
    matches = sum(1 for keyword in keywords if keyword in lowered)
    if matches == 0:
        return 35
    if matches == 1:
        return 70
    return 95


def _quality_label(score: int) -> str:
    """Return a concise quality label for a score."""
    if score >= 90:
        return "EXCELLENT"
    if score >= 75:
        return "GOOD"
    if score >= 55:
        return "FAIR"
    return "WEAK"


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


def _has_content(value: str | None, empty_prefix: str) -> bool:
    """Return whether a prompt variable has usable source content."""
    return bool(value and value.strip() and not value.strip().startswith(empty_prefix))


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Return whether text contains any keyword."""
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


_COVERAGE_TOPICS = {
    "Historical significance": ("historical", "historisch", "bedeutung", "significance"),
    "Musical profile": ("musical", "musik", "style", "stil", "genre", "sound"),
    "Career progression": ("career", "karriere", "active", "laufbahn"),
    "Important works": ("werk", "works", "album", "mamma mia", "voyage"),
    "Later career": ("later", "später", "reunion", "revival", "voyage"),
    "Comeback": ("comeback", "reunion", "rückkehr"),
    "Legacy": ("legacy", "vermächtnis", "influence", "einfluss"),
    "International significance": ("international", "weltweit", "global"),
}
