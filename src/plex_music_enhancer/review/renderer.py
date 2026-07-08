"""Rich rendering for summary review."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from plex_music_enhancer.review.models import QualityReport, ReviewDocument


class ReviewRenderer:
    """Render review documents and quality reports."""

    def __init__(self, console: Console) -> None:
        """Create a review renderer."""
        self._console = console

    def render(self, document: ReviewDocument) -> None:
        """Render current summary, generated summary, diff, and quality."""
        generated_label = _generated_summary_label(document)
        self._console.rule("CURRENT SUMMARY")
        self._console.print(document.current_summary or "[dim]No current summary.[/dim]")
        if document.plan is not None:
            self.render_plan(document)
        if generated_label == "TRANSLATED SUMMARY":
            self._console.print("[bold]↓[/bold]")
        self._console.rule(generated_label)
        self._console.print(document.proposed_summary or "[dim]No generated summary.[/dim]")
        self._console.rule("UNIFIED DIFF")
        self._console.print(Panel(document.diff or "No changes.", expand=False))
        self.render_quality(document.quality)

    def render_quality(self, report: QualityReport) -> None:
        """Render a quality report."""
        self._console.rule("QUALITY")
        status_style = {
            "PASS": "green",
            "WARNINGS": "yellow",
            "FAILED": "red",
        }[report.status]
        self._console.print(f"[{status_style}]{report.status}[/{status_style}]")

        table = Table(show_header=False)
        table.add_column("Check", style="bold")
        table.add_column("Result")
        for check, passed in report.checks.items():
            table.add_row(check, "[green]PASS[/green]" if passed else "[red]FAIL[/red]")
        table.add_row("word_count", str(report.word_count))
        self._console.print(table)

        for failure in report.failures:
            self._console.print(f"[red]{failure}[/red]")
        for warning in report.warnings:
            self._console.print(f"[yellow]{warning}[/yellow]")

    def render_plan(self, document: ReviewDocument) -> None:
        """Render current-summary content quality and planner recommendation."""
        if document.plan is None:
            return

        plan = document.plan
        table = Table(title="Content Quality", show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Quality score", str(plan.quality.quality_score))
        table.add_row("Quality level", plan.quality.quality_level.value)
        table.add_row("Detected issues", ", ".join(issue.value for issue in plan.quality.issues))
        table.add_row("Recommended action", plan.action.value)
        table.add_row("Reason", plan.reason)
        self._console.print(table)


def _generated_summary_label(document: ReviewDocument) -> str:
    """Return the generated summary section label."""
    prompt_name = document.preview.rendered_prompt.name
    if prompt_name == "album_translate":
        return "TRANSLATED SUMMARY"

    return "GENERATED SUMMARY"
