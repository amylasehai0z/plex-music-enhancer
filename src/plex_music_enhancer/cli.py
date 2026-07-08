"""Command-line interface for Plex Music Enhancer."""

from __future__ import annotations

import sys
from json import dumps
from pathlib import Path
from re import sub
from typing import Annotated

import typer
from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, SecretStr, TypeAdapter, ValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from plex_music_enhancer.config import Settings
from plex_music_enhancer.constants import CLI_NAME, MINIMUM_PYTHON_VERSION, __version__
from plex_music_enhancer.enrichment import (
    AlbumContext,
    EnrichmentPipeline,
    EnrichmentPipelineError,
)
from plex_music_enhancer.logging import configure_logging
from plex_music_enhancer.plex import (
    AlbumScanItem,
    AlbumWriteVerificationReport,
    ArtistScanItem,
    InspectedPlexObject,
    InspectTarget,
    MetadataAuditReport,
    MusicLibraryStats,
    PlexAuditError,
    PlexCapabilityAnalysis,
    PlexCapabilityAnalyzer,
    PlexCapabilityError,
    PlexClient,
    PlexInspectError,
    PlexMetadataAuditor,
    PlexMetadataInspector,
    PlexMusicScanner,
    PlexProbeError,
    PlexScannerError,
    PlexWriteProbe,
)
from plex_music_enhancer.services import (
    AlbumMetadataDocument,
    EnrichmentPreviewDocument,
    EnrichmentPreviewService,
    MatchResult,
    MetadataEnrichmentPipeline,
    MusicBrainzMatcher,
    PreviewError,
)

app = typer.Typer(
    name=CLI_NAME,
    help="Production-grade tools for improving Plex music libraries.",
    no_args_is_help=True,
)
scan_app = typer.Typer(
    help="Scan Plex music library data without modifying Plex.",
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(scan_app, name="scan")
inspect_app = typer.Typer(help="Inspect Plex metadata without modifying Plex.")
app.add_typer(inspect_app, name="inspect")
probe_app = typer.Typer(help="Probe Plex write capabilities safely.")
app.add_typer(probe_app, name="probe")
metadata_app = typer.Typer(help="Gather and normalize metadata without modifying Plex.")
app.add_typer(metadata_app, name="metadata")
context_app = typer.Typer(help="Collect normalized album context without modifying Plex.")
app.add_typer(context_app, name="context")
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


@app.command()
def audit(
    export_json: Annotated[
        bool,
        typer.Option("--export-json", help="Export metadata audit to exports/audit.json."),
    ] = False,
) -> None:
    """Audit Plex music metadata completeness without modifying Plex."""
    auditor, token = _create_metadata_auditor()

    try:
        report = auditor.audit()
    except PlexAuditError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to audit Plex metadata:[/red] {message}")
        raise typer.Exit(code=1) from exc

    _render_audit(report)

    if export_json:
        export_path = Path("exports/audit.json")
        _write_scan_export(export_path, report)
        console.print(f"[green]Exported metadata audit to {export_path}[/green]")


@app.command()
def capabilities() -> None:
    """Analyze Plex metadata capabilities without modifying Plex."""
    analyzer, token = _create_capability_analyzer()

    try:
        analysis = analyzer.analyze()
    except PlexCapabilityError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to analyze Plex capabilities:[/red] {message}")
        raise typer.Exit(code=1) from exc

    export_path = Path("exports/capabilities.json")
    _write_scan_export(export_path, analysis)
    _render_capabilities(analysis, export_path)


@app.command()
def login() -> None:
    """Configure Plex server credentials for local CLI usage."""
    url_input = typer.prompt("Plex server URL").strip()
    token = typer.prompt("Plex token", hide_input=True).strip()

    try:
        plex_url = _validate_plex_url(url_input)
    except ValueError as exc:
        console.print(f"[red]Invalid Plex URL:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if not token:
        console.print("[red]Plex token is required.[/red]")
        raise typer.Exit(code=1)

    try:
        _connect_with_plexapi(plex_url, token)
    except PlexLoginError as exc:
        console.print(f"[red]Unable to connect to Plex:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _write_env_values(
        Path(".env"),
        {
            "PLEX_ENHANCER_PLEX_URL": plex_url,
            "PLEX_ENHANCER_PLEX_TOKEN": token,
        },
    )

    console.print("[green]Plex login saved successfully.[/green]")
    checks = _run_diagnostics()
    _render_diagnostics(checks)

    if any(not check.ok for check in checks):
        raise typer.Exit(code=1)


@app.command(name="match")
def match_album(
    artist: Annotated[str, typer.Option("--artist", help="Artist name.")],
    album: Annotated[str, typer.Option("--album", help="Album title.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete match result as JSON."),
    ] = False,
) -> None:
    """Match an album to a MusicBrainz release group without modifying Plex."""
    matcher = MusicBrainzMatcher()

    try:
        result = matcher.match_album(artist_name=artist, album_title=album)
    except Exception as exc:
        console.print(f"[red]Unable to match MusicBrainz metadata:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(result.model_dump_json(indent=2))
    else:
        _render_match_result(result)


@app.command()
def preview(
    artist: Annotated[str, typer.Option("--artist", help="Artist name.")],
    album: Annotated[str, typer.Option("--album", help="Album title.")],
) -> None:
    """Preview album metadata readiness without generating text or modifying Plex."""
    service, token = _create_preview_service()

    try:
        document = service.preview_album(artist=artist, album=album)
    except PreviewError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to preview album enrichment:[/red] {message}")
        raise typer.Exit(code=1) from exc

    _render_enrichment_preview(document)


@scan_app.callback()
def scan(
    ctx: typer.Context,
    export_json: Annotated[
        bool,
        typer.Option(
            "--export-json",
            help="Export music library statistics to exports/libraries.json.",
        ),
    ] = False,
) -> None:
    """Scan configured Plex music libraries without modifying Plex."""
    if ctx.invoked_subcommand is not None:
        return

    _scan_libraries(export_json=export_json)


@scan_app.command()
def artists(
    export_json: Annotated[
        bool,
        typer.Option(
            "--export-json",
            help="Export artist scan results to exports/artists.json.",
        ),
    ] = False,
) -> None:
    """Scan every artist from every configured Plex music library."""
    scanner, token = _create_plex_scanner()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task_id = progress.add_task("Scanning artists...", total=None)

            def update_progress(title: str) -> None:
                progress.update(task_id, description=f"Scanning artist: {title}")

            scan_export = scanner.scan_artists(update_progress)
    except PlexScannerError as exc:
        _raise_scan_error("artists", exc, token)

    _render_artists(scan_export.artists)

    if export_json:
        export_path = Path("exports/artists.json")
        _write_scan_export(export_path, scan_export)
        console.print(f"[green]Exported artist scan to {export_path}[/green]")


@scan_app.command()
def albums(
    export_json: Annotated[
        bool,
        typer.Option(
            "--export-json",
            help="Export album scan results to exports/albums.json.",
        ),
    ] = False,
) -> None:
    """Scan every album from every configured Plex music library."""
    scanner, token = _create_plex_scanner()

    try:
        scan_export = scanner.scan_albums()
    except PlexScannerError as exc:
        _raise_scan_error("albums", exc, token)

    _render_albums(scan_export.albums)

    if export_json:
        export_path = Path("exports/albums.json")
        _write_scan_export(export_path, scan_export)
        console.print(f"[green]Exported album scan to {export_path}[/green]")


@inspect_app.command()
def library(
    rating_key: Annotated[
        str | None,
        typer.Option("--id", help="Plex library ID or rating key."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Plex library title."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete inspection as formatted JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save the complete inspection JSON under exports/inspect/."),
    ] = False,
) -> None:
    """Inspect a Plex library section."""
    _inspect_target(
        InspectTarget.LIBRARY,
        rating_key=rating_key,
        name=name,
        json_output=json_output,
        save=save,
    )


@inspect_app.command()
def artist(
    rating_key: Annotated[
        str | None,
        typer.Option("--id", help="Plex artist rating key."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Plex artist title."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete inspection as formatted JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save the complete inspection JSON under exports/inspect/."),
    ] = False,
) -> None:
    """Inspect a Plex artist."""
    _inspect_target(
        InspectTarget.ARTIST,
        rating_key=rating_key,
        name=name,
        json_output=json_output,
        save=save,
    )


@inspect_app.command()
def album(
    rating_key: Annotated[
        str | None,
        typer.Option("--id", help="Plex album rating key."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Plex album title."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete inspection as formatted JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save the complete inspection JSON under exports/inspect/."),
    ] = False,
) -> None:
    """Inspect a Plex album."""
    _inspect_target(
        InspectTarget.ALBUM,
        rating_key=rating_key,
        name=name,
        json_output=json_output,
        save=save,
    )


@inspect_app.command()
def track(
    rating_key: Annotated[
        str | None,
        typer.Option("--id", help="Plex track rating key."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Plex track title."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete inspection as formatted JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save the complete inspection JSON under exports/inspect/."),
    ] = False,
) -> None:
    """Inspect a Plex track."""
    _inspect_target(
        InspectTarget.TRACK,
        rating_key=rating_key,
        name=name,
        json_output=json_output,
        save=save,
    )


@probe_app.command()
def write(
    artist: Annotated[str, typer.Option("--artist", help="Artist title to locate.")],
    album: Annotated[str, typer.Option("--album", help="Album title to locate.")],
    execute: Annotated[
        bool,
        typer.Option(
            "--execute",
            help="Perform the reversible album.summary write verification.",
        ),
    ] = False,
) -> None:
    """Verify whether an album summary can be edited and restored."""
    probe, token = _create_write_probe()

    try:
        report = probe.verify_album_summary(
            artist_name=artist,
            album_title=album,
            execute=execute,
        )
    except PlexProbeError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to probe Plex write capability:[/red] {message}")
        raise typer.Exit(code=1) from exc

    _render_write_probe(report)


@metadata_app.command(name="album")
def album_metadata(
    artist: Annotated[str, typer.Option("--artist", help="Artist name.")],
    album: Annotated[str, typer.Option("--album", help="Album title.")],
    year: Annotated[int | None, typer.Option("--year", help="Optional release year.")] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the normalized metadata document as JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save metadata JSON under exports/metadata/."),
    ] = False,
) -> None:
    """Gather normalized album metadata without modifying Plex."""
    pipeline = MetadataEnrichmentPipeline()
    document = pipeline.enrich_album(artist=artist, album=album, year=year)

    if json_output:
        console.print_json(document.model_dump_json(indent=2))
    else:
        _render_album_metadata_document(document)

    if save:
        export_path = _metadata_export_path(artist, album)
        _write_scan_export(export_path, document)
        console.print(f"[green]Saved metadata JSON to {export_path}[/green]")


@context_app.command(name="album")
def album_context(
    artist: Annotated[str, typer.Option("--artist", help="Artist name.")],
    album: Annotated[str, typer.Option("--album", help="Album title.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete album context as JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save album context JSON under exports/context/."),
    ] = False,
) -> None:
    """Collect normalized context for one Plex album without modifying Plex."""
    pipeline, token = _create_enrichment_pipeline()

    try:
        context = pipeline.collect_album_context(artist=artist, album=album)
    except EnrichmentPipelineError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to collect album context:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(context.model_dump_json(indent=2))
    else:
        _render_album_context(context)

    if save:
        export_path = _context_export_path(artist, album)
        _write_scan_export(export_path, context)
        console.print(f"[green]Saved album context JSON to {export_path}[/green]")


def _inspect_target(
    target: InspectTarget,
    *,
    rating_key: str | None,
    name: str | None,
    json_output: bool,
    save: bool,
) -> None:
    """Inspect one Plex metadata object and render or save the result."""
    _validate_inspect_lookup(rating_key=rating_key, name=name)
    inspector, token = _create_plex_inspector()

    try:
        inspected_object = inspector.inspect(target, rating_key=rating_key, name=name)
    except PlexInspectError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to inspect Plex {target.value}:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(inspected_object.model_dump_json(indent=2, by_alias=True))
    else:
        _render_inspection(inspected_object)

    if save:
        export_path = _inspection_export_path(target, inspected_object, rating_key, name)
        _write_scan_export(export_path, inspected_object)
        console.print(f"[green]Saved inspection JSON to {export_path}[/green]")


def _validate_inspect_lookup(*, rating_key: str | None, name: str | None) -> None:
    """Validate mutually exclusive inspect lookup options."""
    if (rating_key is None and name is None) or (rating_key is not None and name is not None):
        console.print("[red]Provide exactly one of --id or --name.[/red]")
        raise typer.Exit(code=1)


def _scan_libraries(*, export_json: bool) -> None:
    """Scan Plex music libraries and optionally export JSON."""
    scanner, token = _create_plex_scanner()

    try:
        scan_export = scanner.scan()
    except PlexScannerError as exc:
        _raise_scan_error("libraries", exc, token)

    _render_music_libraries(scan_export.libraries)

    if export_json:
        export_path = Path("exports/libraries.json")
        _write_scan_export(export_path, scan_export)
        console.print(f"[green]Exported music library scan to {export_path}[/green]")


def _create_plex_scanner() -> tuple[PlexMusicScanner, SecretStr]:
    """Create a configured Plex scanner or exit with a user-facing error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return PlexMusicScanner(plex_url, plex_token), plex_token


def _create_plex_inspector() -> tuple[PlexMetadataInspector, SecretStr]:
    """Create a configured Plex inspector or exit with a user-facing error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return PlexMetadataInspector(plex_url, plex_token), plex_token


def _create_metadata_auditor() -> tuple[PlexMetadataAuditor, SecretStr]:
    """Create a configured Plex metadata auditor or exit with an error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return PlexMetadataAuditor(plex_url, plex_token), plex_token


def _create_capability_analyzer() -> tuple[PlexCapabilityAnalyzer, SecretStr]:
    """Create a configured Plex capability analyzer or exit with an error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return PlexCapabilityAnalyzer(plex_url, plex_token), plex_token


def _create_write_probe() -> tuple[PlexWriteProbe, SecretStr]:
    """Create a configured Plex write probe or exit with an error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return PlexWriteProbe(plex_url, plex_token), plex_token


def _create_preview_service() -> tuple[EnrichmentPreviewService, SecretStr]:
    """Create a configured enrichment preview service or exit with an error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return EnrichmentPreviewService(plex_url, plex_token), plex_token


def _create_enrichment_pipeline() -> tuple[EnrichmentPipeline, SecretStr]:
    """Create a configured album context pipeline or exit with an error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(
            "[red]Missing Plex configuration.[/red] "
            "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and "
            "PLEX_ENHANCER_PLEX_TOKEN."
        )
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print("[red]Missing Plex URL or token.[/red]")
        raise typer.Exit(code=1)

    return EnrichmentPipeline(plex_url, plex_token), plex_token


def _raise_scan_error(scan_target: str, exc: PlexScannerError, token: SecretStr) -> None:
    """Display a scanner error without exposing secrets."""
    message = _redact_secret(str(exc), token.get_secret_value())
    console.print(f"[red]Unable to scan Plex {scan_target}:[/red] {message}")
    raise typer.Exit(code=1) from exc


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


def _render_audit(report: MetadataAuditReport) -> None:
    """Render metadata audit results."""
    for library in report.libraries:
        console.print(f"[bold]Library: {library.library_title}[/bold]")

        artists = Table(title="Artists", show_header=False)
        artists.add_column("Metric")
        artists.add_column("Value", justify="right")
        artists.add_row("Total", str(library.statistics.artist_total))
        artists.add_row(
            "Biography present",
            str(library.statistics.artist_biography_present),
        )
        artists.add_row(
            "Biography missing",
            str(library.statistics.artist_biography_missing),
        )
        artists.add_row(
            "Biography unknown",
            str(library.statistics.artist_biography_unknown),
        )
        console.print(artists)

        albums = Table(title="Albums", show_header=False)
        albums.add_column("Metric")
        albums.add_column("Value", justify="right")
        albums.add_row("Total", str(library.statistics.album_total))
        albums.add_row("Summary present", str(library.statistics.album_summary_present))
        albums.add_row("Summary missing", str(library.statistics.album_summary_missing))
        albums.add_row("Summary unknown", str(library.statistics.album_summary_unknown))
        console.print(albums)

        languages = Table(title="Languages", show_header=False)
        languages.add_column("Language")
        languages.add_column("Count", justify="right")
        languages.add_row("German", str(library.statistics.languages.get("german", 0)))
        languages.add_row("English", str(library.statistics.languages.get("english", 0)))
        languages.add_row("Other", str(library.statistics.languages.get("other", 0)))
        console.print(languages)


def _render_capabilities(analysis: PlexCapabilityAnalysis, export_path: Path) -> None:
    """Render capability analysis summary."""
    summary = Table(title="Plex Metadata Capabilities", show_lines=False)
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("Plex Server version", analysis.plex_server_version or "")
    summary.add_row("Platform", analysis.platform or "")
    summary.add_row("Music libraries", str(len(analysis.libraries)))
    summary.add_row("Server API capabilities", ", ".join(analysis.api_capabilities))
    summary.add_row("Export", str(export_path))
    console.print(summary)

    libraries = Table(title="Music Library Agents", show_lines=False)
    libraries.add_column("Library", style="bold")
    libraries.add_column("Agent")
    libraries.add_column("Scanner")
    for library_item in analysis.libraries:
        libraries.add_row(
            library_item.library_title,
            library_item.agent or "",
            library_item.scanner or "",
        )
    console.print(libraries)

    samples = Table(title="Sample Attribute Capabilities", show_lines=False)
    samples.add_column("Object", style="bold")
    samples.add_column("Available", justify="right")
    samples.add_column("Writable", justify="right")
    samples.add_column("Read-only", justify="right")
    samples.add_column("API capabilities")
    for sample in analysis.samples:
        samples.add_row(
            sample.object_type,
            str(len(sample.available_attributes)),
            str(len(sample.writable_attributes)),
            str(len(sample.read_only_attributes)),
            ", ".join(sample.api_capabilities),
        )
    console.print(samples)


def _render_write_probe(report: AlbumWriteVerificationReport) -> None:
    """Render a write verification report."""
    summary = Table(title="Plex Write Verification", show_lines=False)
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("Status", _format_probe_status(report.status))
    summary.add_row("Executed", "yes" if report.executed else "no")
    summary.add_row("Library", report.library or "")
    summary.add_row("Artist", report.artist)
    summary.add_row("Album", report.title or report.album)
    summary.add_row("RatingKey", report.rating_key or "")
    summary.add_row("Current summary", report.current_summary or "")
    summary.add_row("Available edit methods", ", ".join(report.available_edit_methods))
    summary.add_row("editSummary() exists", "yes" if report.edit_summary_exists else "no")
    summary.add_row("✔ Original summary length", str(report.original_summary_length))
    if report.temporary_summary is not None:
        summary.add_row("✔ Temporary summary", report.temporary_summary)
    if report.summary_after_reload is not None:
        summary.add_row("✔ Summary after reload", report.summary_after_reload)
    if report.restore_status is not None:
        summary.add_row("✔ Restore status", report.restore_status)
    if report.final_verification is not None:
        summary.add_row("✔ Final verification", "yes" if report.final_verification else "no")
    if report.temporary_summary_verified is not None:
        summary.add_row(
            "Temporary summary verified",
            "yes" if report.temporary_summary_verified else "no",
        )
    if report.original_summary_restored is not None:
        summary.add_row(
            "Original summary restored",
            "yes" if report.original_summary_restored else "no",
        )
    summary.add_row("Explanation", report.explanation)
    console.print(summary)

    if report.exception:
        console.print("[red]Exception[/red]")
        console.print(report.exception)


def _render_album_metadata_document(document: AlbumMetadataDocument) -> None:
    """Render an album metadata enrichment document."""
    console.rule("PLEX")
    plex = Table(show_header=False)
    plex.add_column("Field", style="bold")
    plex.add_column("Value")
    plex.add_row("Artist", document.plex.artist)
    plex.add_row("Album", document.plex.album)
    plex.add_row("Year", str(document.plex.year or ""))
    plex.add_row("Summary", document.plex.summary or "")
    console.print(plex)

    console.rule("MUSICBRAINZ")
    musicbrainz = Table(show_header=False)
    musicbrainz.add_column("Field", style="bold")
    musicbrainz.add_column("Value")
    musicbrainz.add_row("Matched", "yes" if document.musicbrainz.matched else "no")
    musicbrainz.add_row("Confidence", str(document.musicbrainz.confidence))
    musicbrainz.add_row("MBID", document.musicbrainz.artist_mbid or "")
    musicbrainz.add_row("Release Group", document.musicbrainz.release_group_mbid or "")
    musicbrainz.add_row("Release Date", document.musicbrainz.release_date or "")
    musicbrainz.add_row("Primary Type", document.musicbrainz.primary_type or "")
    musicbrainz.add_row("Secondary Types", ", ".join(document.musicbrainz.secondary_types))
    musicbrainz.add_row("Genres", ", ".join(document.musicbrainz.genres))
    musicbrainz.add_row("Tags", ", ".join(document.musicbrainz.tags))
    console.print(musicbrainz)

    console.rule("NORMALIZED METADATA")
    metadata = Table(show_header=False)
    metadata.add_column("Field", style="bold")
    metadata.add_column("Value")
    metadata.add_row("Artist", document.metadata.artist)
    metadata.add_row("Album", document.metadata.album)
    metadata.add_row("Year", str(document.metadata.year or ""))
    metadata.add_row("Genres", ", ".join(document.metadata.genres))
    metadata.add_row("Summary", document.metadata.summary or "")
    metadata.add_row("Sources", ", ".join(document.metadata.sources))
    metadata.add_row("Confidence", str(document.metadata.confidence))
    console.print(metadata)


def _render_album_context(context: AlbumContext) -> None:
    """Render normalized album context."""
    console.rule("PLEX")
    plex = Table(show_header=False)
    plex.add_column("Field", style="bold")
    plex.add_column("Value")
    plex.add_row("RatingKey", context.plex.rating_key)
    plex.add_row("Artist", context.plex.artist)
    plex.add_row("Album", context.plex.album)
    plex.add_row("Year", str(context.plex.year or ""))
    plex.add_row("Summary", context.plex.summary or "")
    plex.add_row("Genres", ", ".join(context.plex.genres))
    plex.add_row("Styles", ", ".join(context.plex.styles))
    plex.add_row("Moods", ", ".join(context.plex.moods))
    console.print(plex)

    console.rule("MUSICBRAINZ")
    musicbrainz = Table(show_header=False)
    musicbrainz.add_column("Field", style="bold")
    musicbrainz.add_column("Value")
    musicbrainz.add_row("Artist MBID", context.musicbrainz.artist_mbid or "")
    musicbrainz.add_row("Release Group MBID", context.musicbrainz.release_group_mbid or "")
    musicbrainz.add_row("Release MBID", context.musicbrainz.release_mbid or "")
    musicbrainz.add_row("Release Date", context.musicbrainz.release_date or "")
    musicbrainz.add_row("Genres", ", ".join(context.musicbrainz.genres))
    musicbrainz.add_row("Tags", ", ".join(context.musicbrainz.tags))
    musicbrainz.add_row("Confidence", str(context.musicbrainz.confidence))
    console.print(musicbrainz)

    console.rule("WIKIPEDIA")
    wikipedia = Table(show_header=False)
    wikipedia.add_column("Field", style="bold")
    wikipedia.add_column("Value")
    wikipedia.add_row("Language", context.wikipedia.language or "")
    wikipedia.add_row("Title", context.wikipedia.title or "")
    wikipedia.add_row("Extract", context.wikipedia.extract or "")
    wikipedia.add_row("Page URL", context.wikipedia.page_url or "")
    wikipedia.add_row("Thumbnail URL", context.wikipedia.thumbnail_url or "")
    console.print(wikipedia)

    console.rule("PIPELINE STATUS")
    pipeline = Table(show_header=False)
    pipeline.add_column("Field", style="bold")
    pipeline.add_column("Value")
    pipeline.add_row("Collected Sources", ", ".join(context.pipeline.collected_sources))
    pipeline.add_row("Missing Fields", ", ".join(context.pipeline.missing_fields))
    pipeline.add_row("Warnings", "\n".join(context.pipeline.warnings))
    console.print(pipeline)

    console.rule("READY FOR GENERATION")
    console.print(_yes_no(context.pipeline.ready_for_generation))


def _render_match_result(result: MatchResult) -> None:
    """Render a MusicBrainz match result."""
    table = Table(title="MusicBrainz Match", show_lines=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Artist", result.artist_name or "")
    table.add_row("Album", result.album_title or "")
    table.add_row("Confidence (0-100)", str(result.confidence))
    table.add_row("MusicBrainz Artist ID", result.artist_mbid or "")
    table.add_row("Release Group ID", result.release_group_mbid or "")
    table.add_row("Release ID", result.release_mbid or "")
    table.add_row("Release Year", str(result.release_year or ""))
    table.add_row("Primary Type", result.primary_type or "")
    table.add_row("Secondary Types", ", ".join(result.secondary_types))
    table.add_row("Warnings", "\n".join(result.warnings))
    console.print(table)


def _render_enrichment_preview(document: EnrichmentPreviewDocument) -> None:
    """Render a read-only enrichment preview."""
    album = Table(title="Plex Album", show_lines=False)
    album.add_column("Field", style="bold")
    album.add_column("Value")
    album.add_row("Title", document.plex.title)
    album.add_row("Artist", document.plex.artist)
    album.add_row("Current summary", document.plex.current_summary or "")
    album.add_row("Year", str(document.plex.year or ""))
    album.add_row("Genres", ", ".join(document.plex.genres))
    console.print(album)

    provider = Table(title="Provider Checks", show_lines=False)
    provider.add_column("Check", style="bold")
    provider.add_column("Status")
    provider.add_row("✓ Provider reachable", _yes_no(document.provider.reachable))
    provider.add_row("✓ Match found", _yes_no(document.provider.match_found))
    provider.add_row("✓ Metadata available", _yes_no(document.provider.metadata_available))
    if document.provider.error:
        provider.add_row("Error", document.provider.error)
    console.print(provider)

    musicbrainz = Table(title="MusicBrainz", show_lines=False)
    musicbrainz.add_column("Field", style="bold")
    musicbrainz.add_column("Value")
    metadata = document.metadata.musicbrainz if document.metadata is not None else None
    musicbrainz.add_row("MusicBrainz ID", metadata.artist_mbid if metadata else "")
    musicbrainz.add_row("Release Group", metadata.release_group_mbid if metadata else "")
    release_year = str(document.metadata.metadata.year) if document.metadata else ""
    musicbrainz.add_row("Release Year", release_year)
    musicbrainz.add_row("Genres", ", ".join(metadata.genres) if metadata else "")
    console.print(musicbrainz)

    if document.ready_for_ai_enrichment:
        console.print("[green]This album is ready for AI enrichment.[/green]")
    else:
        console.print("[yellow]This album is not ready for AI enrichment yet.[/yellow]")


def _yes_no(value: bool) -> str:
    """Return a Rich status label."""
    return "[green]yes[/green]" if value else "[red]no[/red]"


def _format_probe_status(status: str) -> str:
    """Return a Rich-formatted write probe status."""
    if status == "SUCCESS":
        return "[green]SUCCESS[/green]"
    if status == "READ_ONLY":
        return "[yellow]READ_ONLY[/yellow]"
    if status == "FAILED":
        return "[red]FAILED[/red]"

    return status


def _render_inspection(inspected_object: InspectedPlexObject) -> None:
    """Render a human-readable metadata inspection."""
    summary = Table(title=f"Plex {inspected_object.object_type.title()} Inspection")
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("ratingKey", inspected_object.rating_key or "")
    summary.add_row("guid", inspected_object.guid or "")
    summary.add_row("title", inspected_object.title or "")
    summary.add_row("attributes", str(len(inspected_object.attributes)))
    summary.add_row("media objects", str(len(inspected_object.media)))
    summary.add_row("images", str(len(inspected_object.images)))
    summary.add_row("children", str(len(inspected_object.children)))
    console.print(summary)

    _render_key_value_table("Attributes", inspected_object.attributes)
    _render_sequence_table("Media Objects", inspected_object.media)
    _render_sequence_table(
        "Images",
        [image.model_dump(by_alias=True) for image in inspected_object.images],
    )
    _render_sequence_table(
        "Children",
        [child.model_dump(by_alias=True) for child in inspected_object.children],
    )


def _render_key_value_table(title: str, values: dict[str, object]) -> None:
    """Render key-value inspection data."""
    table = Table(title=title, show_lines=False)
    table.add_column("Name", style="bold")
    table.add_column("Value")

    for key, value in values.items():
        table.add_row(key, _display_value(value))

    console.print(table)


def _render_sequence_table(title: str, values: list[dict[str, object]]) -> None:
    """Render list-like inspection data."""
    table = Table(title=title, show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("Data")

    for index, value in enumerate(values, start=1):
        table.add_row(str(index), _display_value(value))

    console.print(table)


def _display_value(value: object) -> str:
    """Return a compact display value for Rich tables."""
    if isinstance(value, str):
        return value

    try:
        return dumps(value, default=str, ensure_ascii=False)
    except TypeError:
        return str(value)


def _render_music_libraries(libraries: list[MusicLibraryStats]) -> None:
    """Render music library statistics as a Rich table."""
    table = Table(title="Plex Music Libraries", show_lines=False)
    table.add_column("Library Name", style="bold")
    table.add_column("Library ID")
    table.add_column("Artists", justify="right")
    table.add_column("Albums", justify="right")
    table.add_column("Tracks", justify="right")

    for library in libraries:
        table.add_row(
            library.library_title,
            library.library_id,
            str(library.artist_count),
            str(library.album_count),
            str(library.track_count),
        )

    console.print(table)


def _render_artists(artist_items: list[ArtistScanItem]) -> None:
    """Render artist scan results as a Rich table."""
    table = Table(title="Plex Artists", show_lines=False)
    table.add_column("Artist", style="bold")
    table.add_column("Albums", justify="right")
    table.add_column("Country")
    table.add_column("Genres")

    for artist_item in artist_items:
        table.add_row(
            artist_item.title,
            str(artist_item.album_count),
            artist_item.country or "",
            ", ".join(artist_item.genres),
        )

    console.print(table)


def _render_albums(album_items: list[AlbumScanItem]) -> None:
    """Render album scan results as a Rich table."""
    table = Table(title="Plex Albums", show_lines=False)
    table.add_column("Album", style="bold")
    table.add_column("Artist")
    table.add_column("Year", justify="right")
    table.add_column("Tracks", justify="right")

    for album_item in album_items:
        table.add_row(
            album_item.title,
            album_item.parent_artist or "",
            str(album_item.year) if album_item.year is not None else "",
            str(album_item.leaf_count),
        )

    console.print(table)


def _write_scan_export(export_path: Path, scan_export: BaseModel) -> None:
    """Write scan results to a JSON export file."""
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        scan_export.model_dump_json(indent=2, by_alias=True) + "\n",
        encoding="utf-8",
    )


def _inspection_export_path(
    target: InspectTarget,
    inspected_object: InspectedPlexObject,
    rating_key: str | None,
    name: str | None,
) -> Path:
    """Return the export path for a saved inspection."""
    identifier = (
        inspected_object.rating_key or rating_key or inspected_object.title or name or "unknown"
    )
    safe_identifier = sub(r"[^A-Za-z0-9_.-]+", "-", identifier).strip("-") or "unknown"
    return Path("exports") / "inspect" / f"{target.value}-{safe_identifier}.json"


def _metadata_export_path(artist: str, album: str) -> Path:
    """Return the export path for saved album metadata."""
    filename = f"{_safe_export_segment(artist)}-{_safe_export_segment(album)}.json"
    return Path("exports") / "metadata" / filename


def _context_export_path(artist: str, album: str) -> Path:
    """Return the export path for saved album context."""
    filename = f"{_safe_export_segment(artist)}-{_safe_export_segment(album)}.json"
    return Path("exports") / "context" / filename


def _safe_export_segment(value: str) -> str:
    """Return a filesystem-safe export path segment."""
    return sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "unknown"


def _format_validation_error(exc: ValidationError) -> str:
    """Return a compact validation error summary for CLI output."""
    messages = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        messages.append(f"{field}: {error['msg']}")
    return "; ".join(messages)


class PlexLoginError(Exception):
    """Raised when Plex login validation fails."""


def _validate_plex_url(raw_url: str) -> str:
    """Validate and normalize a Plex server URL."""
    normalized_url = raw_url.rstrip("/")
    if not normalized_url:
        msg = "URL is required."
        raise ValueError(msg)

    try:
        TypeAdapter(AnyHttpUrl).validate_python(normalized_url)
    except ValidationError as exc:
        msg = _format_validation_error(exc)
        raise ValueError(msg) from exc

    return normalized_url


def _connect_with_plexapi(plex_url: str, token: str) -> None:
    """Verify Plex connectivity using plexapi."""
    try:
        server = PlexServer(plex_url, token)
        _ = server.friendlyName
    except Exception as exc:
        msg = _redact_secret(
            str(exc) or "Check the server URL and token, then try again.",
            token,
        )
        raise PlexLoginError(msg) from exc


def _write_env_values(env_path: Path, values: dict[str, str]) -> None:
    """Create or update `.env` values while preserving unrelated variables."""
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    remaining_values = values.copy()
    updated_lines: list[str] = []

    for line in existing_lines:
        key = _parse_env_key(line)
        if key in remaining_values:
            updated_lines.append(f"{key}={remaining_values.pop(key)}")
        else:
            updated_lines.append(line)

    for key, value in remaining_values.items():
        updated_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def _parse_env_key(line: str) -> str | None:
    """Return the key for a simple `.env` assignment line."""
    stripped_line = line.strip()
    if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
        return None

    key, _separator, _value = stripped_line.partition("=")
    return key.strip()


def _redact_secret(message: str, secret: str) -> str:
    """Remove a sensitive value from a user-facing message."""
    if not secret:
        return message

    return message.replace(secret, "REDACTED")


if __name__ == "__main__":
    app()
