"""Rich rendering for developer-mode diagnostics."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from plex_music_enhancer.developer.models import (
    DeveloperDoctorReport,
    DeveloperExplanation,
    PromptDebugDocument,
    PromptMetaDocument,
    ReviewLogDocument,
)


class DeveloperDebugRenderer:
    """Render developer-mode diagnostics using Rich."""

    def __init__(self, console: Console) -> None:
        """Create a renderer."""
        self._console = console

    def render_prompt(self, document: PromptDebugDocument, *, show_stats: bool = False) -> None:
        """Render the latest prompt."""
        if not document.exists:
            self._console.print("[yellow]No prompt debug file found.[/yellow]")
            self._console.print(f"[dim]{document.path}[/dim]")
            return
        self._console.print(Panel(document.content or "Prompt file is empty.", title="Prompt"))
        if show_stats:
            self._console.print(self._stats_table(document))

    def render_meta(self, document: PromptMetaDocument) -> None:
        """Render prompt metadata."""
        if not document.exists:
            self._console.print("[yellow]No prompt metadata file found.[/yellow]")
            self._console.print(f"[dim]{document.path}[/dim]")
            return
        table = Table(title="Prompt Meta")
        table.add_column("Field")
        table.add_column("Value")
        for key in (
            "timestamp",
            "provider",
            "model",
            "target",
            "prompt_version",
            "prompt_characters",
            "estimated_prompt_tokens",
            "max_prompt_characters",
        ):
            table.add_row(key, _format_value(document.payload.get(key)))
        budget = document.payload.get("budget_diagnostics")
        if isinstance(budget, dict):
            table.add_row("prompt_decisions", _format_value(budget.get("prompt_decisions")))
            table.add_row(
                "prompt_efficiency",
                _format_value(_nested(budget, "prompt_quality", "prompt_efficiency")),
            )
        self._console.print(table)

    def render_review(
        self,
        document: ReviewLogDocument,
        *,
        summary: bool = False,
        section: str | None = None,
    ) -> None:
        """Render the review debug log."""
        if not document.exists:
            self._console.print("[yellow]No review debug log found.[/yellow]")
            self._console.print(f"[dim]{document.path}[/dim]")
            return
        if section:
            content = document.section(section)
            self._console.print(Panel(content or "Section not found.", title=section))
            return
        if summary:
            for name in (
                "Quality",
                "Editorial Quality",
                "Verification",
                "Editorial Coverage",
                "Evidence Coverage",
                "Prompt Quality",
            ):
                content = document.section(name)
                if content:
                    self._console.print(Panel(content, title=name))
            return
        self._console.print(Panel(document.content or "Review log is empty.", title="Review Log"))

    def render_explanation(self, explanation: DeveloperExplanation) -> None:
        """Render explainability analysis."""
        self._console.print(Panel("\n".join(explanation.summary), title="Explain"))
        self._console.print(_mapping_table("Used Sources", explanation.used_sources))
        self._console.print(_list_mapping_table("Prompt Decisions", explanation.prompt_decisions))
        if explanation.missed_opportunities:
            self._console.print(
                Panel(
                    "\n".join(explanation.missed_opportunities),
                    title="Missed Opportunities",
                )
            )
        self._console.print(Panel("\n".join(explanation.recommendations), title="Recommendations"))

    def render_doctor(self, report: DeveloperDoctorReport) -> None:
        """Render the full developer-mode doctor report."""
        table = Table(title="Developer Doctor")
        table.add_column("Check")
        table.add_column("Status")
        for key, value in report.checks.items():
            style = "green" if value == "PASS" else "yellow" if value == "UNKNOWN" else "red"
            table.add_row(key, f"[{style}]{value}[/{style}]")
        self._console.print(table)
        self.render_explanation(report.explanation)

    def _stats_table(self, document: PromptDebugDocument) -> Table:
        """Return a prompt statistics table."""
        table = Table(title="Prompt Stats")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Characters", str(document.stats.characters))
        table.add_row("Words", str(document.stats.words))
        table.add_row("Estimated tokens", str(document.stats.estimated_tokens))
        table.add_row("Budget", _format_value(document.stats.budget))
        table.add_row("Prompt version", _format_value(document.stats.prompt_version))
        return table


def _mapping_table(title: str, values: dict[str, str]) -> Table:
    """Return a two-column mapping table."""
    table = Table(title=title)
    table.add_column("Name")
    table.add_column("Value")
    if not values:
        table.add_row("n/a", "No data")
    for key, value in values.items():
        table.add_row(key, value)
    return table


def _list_mapping_table(title: str, values: dict[str, list[str]]) -> Table:
    """Return a mapping table with list values."""
    table = Table(title=title)
    table.add_column("Group")
    table.add_column("Items")
    if not values:
        table.add_row("n/a", "No data")
    for key, items in values.items():
        table.add_row(key, "\n".join(items) if items else "None")
    return table


def _format_value(value: Any) -> str:
    """Return a compact printable value."""
    if value is None:
        return "not reported"
    if isinstance(value, dict):
        return ", ".join(f"{key}={_format_value(item)}" for key, item in value.items()) or "{}"
    if isinstance(value, list):
        return ", ".join(_format_value(item) for item in value) or "[]"
    return str(value)


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    """Return a nested value from dictionaries."""
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
