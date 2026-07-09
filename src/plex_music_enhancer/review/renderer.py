"""Rich rendering for summary review."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from plex_music_enhancer.review.models import QualityReport, ReviewDocument
from plex_music_enhancer.review.policy import evaluate_review_policy


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
        self.render_diff(document)
        self.render_quality(document.quality)
        self.render_policy_summary(document)
        self.render_style(document)
        self.render_editorial_quality(document)
        self.render_verification(document)

    def render_diff(self, document: ReviewDocument) -> None:
        """Render the unified diff section."""
        self._console.rule("UNIFIED DIFF")
        self._console.print(Panel(document.diff or "No changes.", expand=False))

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

    def render_policy_summary(self, document: ReviewDocument) -> None:
        """Render apply policy summary."""
        policy = evaluate_review_policy(document)
        table = Table(title="QUALITY SUMMARY", show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Critical validation", policy.critical_validation)
        table.add_row("Editorial validation", policy.editorial_validation)
        table.add_row("Publishable", "YES" if policy.publishable else "NO")
        for message in policy.messages:
            table.add_row("Message", message)
        self._console.print(table)

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

    def render_style(self, document: ReviewDocument) -> None:
        """Render German editorial style diagnostics."""
        style = document.style
        table = Table(title="STYLE ANALYSIS", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Result")
        table.add_row("Sentence variation", style.sentence_variation)
        table.add_row("Vocabulary diversity", style.vocabulary_diversity)
        table.add_row("Repetition", style.repetition)
        table.add_row("Readability", style.readability)
        table.add_row("LLM clichés", style.llm_cliches)
        table.add_row("Passive voice", style.passive_voice)
        table.add_row("Overall style", style.overall_style)
        table.add_row("Readability score", str(style.readability_score))
        if style.issues:
            table.add_row("Issues", ", ".join(style.issues))
        self._console.print(table)

    def render_verification(self, document: ReviewDocument) -> None:
        """Render a compact fact verification summary."""
        collection = getattr(document.preview.context, "fact_collection", None)
        if collection is None:
            return

        table = Table(title="VERIFICATION SUMMARY", show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        verified = collection.by_state("verified")
        probable = collection.by_state("probable")
        weak = collection.by_state("weak")
        table.add_row("Verified facts", str(len([fact for fact in verified if fact.value])))
        table.add_row("Probable facts", str(len([fact for fact in probable if fact.value])))
        table.add_row("Weak facts", str(len([fact for fact in weak if fact.value])))
        table.add_row("Conflicts", str(len(collection.conflicts)))
        if collection.missing_facts:
            table.add_row("Missing", ", ".join(collection.missing_facts[:8]))
        self._console.print(table)

    def render_editorial_quality(self, document: ReviewDocument) -> None:
        """Render deterministic editorial QA results."""
        report = getattr(document.preview, "qa_report", None)
        if report is None:
            return

        table = Table(title="EDITORIAL QUALITY", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_row("Overall Score", str(report.overall_score))
        level = report.overall_level or report.quality_level
        table.add_row("Quality Level", level.value if level is not None else "UNKNOWN")
        for check in report.checks:
            table.add_row(check.category.value, check.status.value)
        if report.recommendations:
            table.add_row(
                "Missing Opportunities",
                "\n".join(str(recommendation) for recommendation in report.recommendations[:8]),
            )
        self._console.print(table)


def _generated_summary_label(document: ReviewDocument) -> str:
    """Return the generated summary section label."""
    prompt_name = document.preview.rendered_prompt.name
    if prompt_name == "album_translate":
        return "TRANSLATED SUMMARY"

    return "GENERATED SUMMARY"
