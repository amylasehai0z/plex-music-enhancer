"""Command-line interface for Plex Music Enhancer."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from plex_music_enhancer.config import Settings
from plex_music_enhancer.constants import CLI_NAME, MINIMUM_PYTHON_VERSION, __version__
from plex_music_enhancer.logging import configure_logging
from plex_music_enhancer.plex import PlexClient

app = typer.Typer(
    name=CLI_NAME,
    help="Production-grade tools for improving Plex music libraries.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main(
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            envvar="PLEX_ENHANCER_LOG_LEVEL",
            help="Logging level.",
        ),
    ] = "INFO",
) -> None:
    """Configure shared CLI behavior."""
    configure_logging(log_level)


@app.command()
def version() -> None:
    """Print the installed Plex Music Enhancer version."""
    console.print(f"{CLI_NAME} {__version__}")


@app.command()
def doctor() -> None:
    """Run diagnostics for the local Plex Music Enhancer setup."""
    checks = _run_diagnostics()
    _render_diagnostics(checks)

    if any(not check.ok for check in checks):
        raise typer.Exit(code=1)


class DiagnosticCheck:
    """A single doctor diagnostic check."""

    def __init__(self, name: str, ok: bool, detail: str) -> None:
        """Create a diagnostic check row."""
        self.name = name
        self.ok = ok
        self.detail = detail


def _run_diagnostics() -> list[DiagnosticCheck]:
    """Execute doctor diagnostics."""
    checks: list[DiagnosticCheck] = []

    python_ok = sys.version_info >= MINIMUM_PYTHON_VERSION
    checks.append(
        DiagnosticCheck(
            "Python version",
            python_ok,
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    try:
        settings = Settings()
    except ValidationError as exc:
        checks.append(DiagnosticCheck("Configuration", False, _format_validation_error(exc)))
        checks.append(
            DiagnosticCheck("Plex URL", False, "Skipped because configuration is invalid.")
        )
        checks.append(
            DiagnosticCheck(
                "Plex connection",
                False,
                "Skipped because configuration is invalid.",
            )
        )
        return checks

    checks.append(
        DiagnosticCheck(
            "Configuration",
            settings.has_plex_configuration,
            (
                "Required Plex settings are present."
                if settings.has_plex_configuration
                else "Set PLEX_ENHANCER_PLEX_URL and PLEX_ENHANCER_PLEX_TOKEN."
            ),
        )
    )

    checks.append(
        DiagnosticCheck(
            "Plex URL",
            settings.plex_url is not None,
            str(settings.plex_url) if settings.plex_url is not None else "Missing Plex URL.",
        )
    )

    if not settings.has_plex_configuration:
        checks.append(
            DiagnosticCheck(
                "Plex connection",
                False,
                "Skipped because Plex URL or token is missing.",
            )
        )
        return checks

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        checks.append(
            DiagnosticCheck(
                "Plex connection",
                False,
                "Skipped because Plex URL or token is missing.",
            )
        )
        return checks

    result = PlexClient(
        plex_url,
        plex_token,
        timeout_seconds=settings.request_timeout_seconds,
    ).check_connection()
    detail = result.message or "No connection detail returned."
    if result.server_name:
        detail = f"{detail} Server: {result.server_name}."
    if result.status_code is not None:
        detail = f"{detail} HTTP {result.status_code}."

    checks.append(DiagnosticCheck("Plex connection", result.ok, detail))
    return checks


def _render_diagnostics(checks: list[DiagnosticCheck]) -> None:
    """Render diagnostic checks as a Rich table."""
    table = Table(title="Plex Music Enhancer Diagnostics", show_lines=False)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    for check in checks:
        status = "[green]OK[/green]" if check.ok else "[red]FAIL[/red]"
        table.add_row(check.name, status, check.detail)

    console.print(table)


def _format_validation_error(exc: ValidationError) -> str:
    """Return a compact validation error summary for CLI output."""
    messages = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        messages.append(f"{field}: {error['msg']}")
    return "; ".join(messages)


if __name__ == "__main__":
    app()
