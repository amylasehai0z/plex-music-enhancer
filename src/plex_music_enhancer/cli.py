"""Command-line interface for Plex Music Enhancer."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from errno import EACCES, EADDRINUSE
from json import dumps
from os import environ
from pathlib import Path
from re import sub
from shutil import which
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket
from typing import Annotated

import typer
from click import edit as click_edit
from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, SecretStr, TypeAdapter, ValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from plex_music_enhancer.ai import AIError, AIManager
from plex_music_enhancer.apply import ApplyError, ApplyResult, ApplyService
from plex_music_enhancer.batch import (
    BatchDecision,
    BatchReviewError,
    BatchReviewOptions,
    BatchReviewReport,
    BatchReviewService,
    BatchReviewStep,
    PlexBatchAlbumSource,
)
from plex_music_enhancer.cache import CacheEntryInfo, CacheStats, KnowledgeCacheStore
from plex_music_enhancer.config import AISettings, Settings
from plex_music_enhancer.constants import CLI_NAME, MINIMUM_PYTHON_VERSION, __version__
from plex_music_enhancer.developer import (
    DeveloperAnalyzer,
    DeveloperDebugRenderer,
    PromptDebugReader,
    PromptMetaReader,
    ReviewLogReader,
)
from plex_music_enhancer.editorial import GermanEditorialStyleEngine
from plex_music_enhancer.enrichment import (
    AlbumContext,
    EnrichmentPipeline,
    EnrichmentPipelineError,
)
from plex_music_enhancer.library import (
    LibraryPlanReport,
    LibraryReviewReport,
    LibraryReviewStep,
    LibraryWorkflowError,
    LibraryWorkflowService,
)
from plex_music_enhancer.logging import configure_logging
from plex_music_enhancer.performance import BenchmarkReport, BenchmarkService
from plex_music_enhancer.planner import EnrichmentPlanner, PlanningReport
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
from plex_music_enhancer.prompts import PromptRegistry
from plex_music_enhancer.review import (
    ReviewDebugContext,
    ReviewDebugLogger,
    ReviewDocument,
    ReviewError,
    ReviewRenderer,
    ReviewService,
    evaluate_review_policy,
)
from plex_music_enhancer.services import (
    AlbumMetadataDocument,
    ArtistPreviewDocument,
    EnrichmentPreviewDocument,
    EnrichmentPreviewService,
    MatchResult,
    MetadataEnrichmentPipeline,
    MusicBrainzMatcher,
    PreviewError,
)
from plex_music_enhancer.utils.files import write_text_atomic
from plex_music_enhancer.verification import FactCollection
from plex_music_enhancer.verification.verifier import (
    SUPPORTED_ARTIST_CATEGORIES,
    SUPPORTED_CATEGORIES,
)

PLEX_CONFIGURATION_HELP = (
    "Run `plex-enhancer login` or set PLEX_ENHANCER_PLEX_URL and " "PLEX_ENHANCER_PLEX_TOKEN."
)
ARTIST_OPTION_HELP = "Artist name."
ALBUM_OPTION_HELP = "Album title."
AI_PROVIDER_REVIEW_HELP = "AI provider override for this review."
AI_MODEL_REVIEW_HELP = "AI model override for this review."
JSON_REVIEW_HELP = "Print the complete review document as JSON."
TRANSLATE_REVIEW_HELP = "Review a German translation of the current summary."
IMPROVE_REVIEW_HELP = "Review an improved German version of the current summary."

app = typer.Typer(
    name=CLI_NAME,
    help="Production-grade tools for improving Plex music libraries.",
    epilog=(
        "Examples:\n"
        "  plex-enhancer doctor\n"
        "  plex-enhancer scan --export-json\n"
        '  plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer library plan --library "Music"'
    ),
    no_args_is_help=True,
)
scan_app = typer.Typer(
    help="Scan Plex music library data without modifying Plex.",
    epilog=(
        "Examples:\n"
        "  plex-enhancer scan\n"
        "  plex-enhancer scan artists --export-json\n"
        "  plex-enhancer scan albums --export-json"
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(scan_app, name="scan")
inspect_app = typer.Typer(
    help="Inspect Plex metadata without modifying Plex.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer inspect artist --name "Nina Simone"\n'
        "  plex-enhancer inspect album --id 12345 --json\n"
        '  plex-enhancer inspect track --name "Sinnerman" --save'
    ),
)
app.add_typer(inspect_app, name="inspect")
probe_app = typer.Typer(
    help="Probe Plex write capabilities safely.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer probe write --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer probe write --artist "Nina Simone" --album "Pastel Blues" --execute'
    ),
)
app.add_typer(probe_app, name="probe")
metadata_app = typer.Typer(
    help="Gather and normalize metadata without modifying Plex.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer metadata album --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer metadata album --artist "Nina Simone" --album "Pastel Blues" --save'
    ),
)
app.add_typer(metadata_app, name="metadata")
context_app = typer.Typer(
    help="Collect normalized album context without modifying Plex.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer context album --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer context album --artist "Nina Simone" --album "Pastel Blues" --json'
    ),
)
app.add_typer(context_app, name="context")
preview_app = typer.Typer(
    help="Preview generated metadata without modifying Plex.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues" --translate\n'
        '  plex-enhancer preview artist --artist "Nina Simone"'
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(preview_app, name="preview")
review_app = typer.Typer(
    help="Review generated metadata without modifying Plex.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer review album --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer review album --artist "Nina Simone" --album "Pastel Blues" --improve\n'
        '  plex-enhancer review artist --artist "Nina Simone"'
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(review_app, name="review")
apply_app = typer.Typer(
    help="Apply approved generated metadata safely.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer apply --artist "Nina Simone" --album "Pastel Blues"\n'
        '  plex-enhancer apply --artist "Nina Simone" --album "Pastel Blues" --translate\n'
        '  plex-enhancer apply artist --artist "Nina Simone"'
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(apply_app, name="apply")
batch_app = typer.Typer(
    help="Process multiple albums in a guided session.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer batch review --library "Music" --limit 25\n'
        '  plex-enhancer batch review --library "Music" --all --resume'
    ),
)
app.add_typer(batch_app, name="batch")
library_app = typer.Typer(
    help="Process an entire Plex music library interactively.",
    epilog=(
        "Examples:\n"
        '  plex-enhancer library plan --library "Music"\n'
        '  plex-enhancer library review --library "Music"\n'
        '  plex-enhancer library apply --library "Music"\n'
        '  plex-enhancer library report --library "Music" --export-json'
    ),
)
app.add_typer(library_app, name="library")
cache_app = typer.Typer(
    help="Inspect and manage the local provider knowledge cache.",
    epilog=(
        "Examples:\n"
        "  plex-enhancer cache stats\n"
        "  plex-enhancer cache list\n"
        "  plex-enhancer cache clear"
    ),
)
app.add_typer(cache_app, name="cache")
debug_app = typer.Typer(
    help="Inspect prompt and review debug artifacts without running AI.",
    epilog=(
        "Examples:\n"
        "  plex-enhancer debug prompt --stats\n"
        "  plex-enhancer debug meta\n"
        "  plex-enhancer debug review --summary\n"
        "  plex-enhancer debug explain\n"
        "  plex-enhancer debug doctor --json"
    ),
)
app.add_typer(debug_app, name="debug")
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
def serve(
    host: Annotated[str, typer.Option("--host", help="Host interface to bind.")] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            min=1,
            max=65535,
            envvar="PLEX_ENHANCER_WEB__PORT",
            help="Port to bind.",
        ),
    ] = 8080,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable Uvicorn reload for local development."),
    ] = False,
) -> None:
    """Start the optional FastAPI REST backend."""
    try:
        import uvicorn

        from plex_music_enhancer.web.app import create_app
    except ImportError as exc:
        console.print(
            "[red]FastAPI backend dependencies are not installed.[/red] "
            'Install with: python -m pip install ".[web]"'
        )
        raise typer.Exit(code=1) from exc
    try:
        application = create_app()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    bind_socket = socket(AF_INET, SOCK_STREAM)
    bind_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    try:
        bind_socket.bind((host, port))
        bind_socket.listen(2048)
    except OSError as exc:
        bind_socket.close()
        _render_serve_bind_error(host=host, port=port, error=exc)
        raise typer.Exit(code=1) from exc

    web_url = f"http://{host}:{port}"
    console.print("[green]✔ Web Interface[/green]")
    console.print(web_url)
    console.print("[green]✔ REST API[/green]")
    console.print(f"{web_url}/api/v1/docs")

    config = uvicorn.Config(application, host=host, port=port, reload=reload)
    server = uvicorn.Server(config)
    server.run(sockets=[bind_socket])


def _render_serve_bind_error(*, host: str, port: int, error: OSError) -> None:
    """Render actionable web-server bind errors."""
    url = f"http://{host}:{port}"
    console.print("[red]Web Interface could not be started.[/red]")
    console.print(f"Attempted URL: {url}")

    if error.errno == EADDRINUSE:
        console.print("[yellow]Port is already in use.[/yellow]")
    elif error.errno == EACCES:
        console.print("[yellow]Port is not permitted for this user or environment.[/yellow]")
    else:
        console.print(f"[yellow]Underlying exception:[/yellow] {error}")

    console.print("Recommended alternative:")
    console.print("  plex-enhancer serve --port 18080")


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
        with console.status("Auditing Plex music libraries..."):
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
def plan(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to plan."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete planning report as JSON."),
    ] = False,
) -> None:
    """Plan enrichment actions for Plex albums without generating metadata."""
    source, token = _create_planning_source()

    try:
        if json_output:
            report = EnrichmentPlanner().plan_albums(source.scan_albums(library=library))
        else:
            with console.status("Planning album enrichment actions..."):
                report = EnrichmentPlanner().plan_albums(source.scan_albums(library=library))
    except BatchReviewError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to plan enrichment:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_planning_report(report)


@app.command()
def benchmark(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to benchmark."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete benchmark report as JSON."),
    ] = False,
) -> None:
    """Run read-only performance diagnostics for a Plex music library."""
    plex_url, plex_token = _require_plex_configuration()
    service = BenchmarkService(
        album_source=PlexBatchAlbumSource(plex_url, plex_token),
        cache_store=KnowledgeCacheStore(),
    )

    try:
        if json_output:
            report = service.run(library=library)
        else:
            with console.status("Benchmarking Plex library performance..."):
                report = service.run(library=library)
    except BatchReviewError as exc:
        message = _redact_secret(str(exc), plex_token.get_secret_value())
        console.print(f"[red]Unable to benchmark library:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_benchmark_report(report)


@app.command()
def capabilities() -> None:
    """Analyze Plex metadata capabilities without modifying Plex."""
    analyzer, token = _create_capability_analyzer()

    try:
        with console.status("Analyzing Plex metadata capabilities..."):
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


@preview_app.callback()
def preview(
    ctx: typer.Context,
    artist: Annotated[str | None, typer.Option("--artist", help="Artist name.")] = None,
    album: Annotated[str | None, typer.Option("--album", help="Album title.")] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this preview."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this preview."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete preview document as JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save preview JSON under exports/previews/."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show full metadata, prompt, and provider diagnostics."),
    ] = False,
    translate: Annotated[
        bool,
        typer.Option("--translate", help="Translate the current Plex summary into German."),
    ] = False,
    improve: Annotated[
        bool,
        typer.Option("--improve", help="Improve the existing German Plex summary."),
    ] = False,
) -> None:
    """Preview generated album enrichment without modifying Plex."""
    if ctx.invoked_subcommand is not None:
        return
    if artist is None or album is None:
        console.print("[red]Album preview requires --artist and --album.[/red]")
        raise typer.Exit(code=1)
    if translate and improve:
        console.print("[red]Choose either --translate or --improve, not both.[/red]")
        raise typer.Exit(code=1)

    service, token = _create_preview_service(provider_name=provider, model=model)
    prompt_name = _album_preview_prompt_name(translate=translate, improve=improve)

    try:
        document = (
            service.preview_album(artist=artist, album=album)
            if prompt_name == "album_summary"
            else service.preview_album(artist=artist, album=album, prompt_name=prompt_name)
        )
    except PreviewError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to preview album enrichment:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(document.model_dump_json(indent=2))
    else:
        _render_enrichment_preview(document, verbose=verbose)

    if save:
        export_path = _preview_export_path(artist, album)
        _write_scan_export(export_path, document)
        console.print(f"[green]Saved preview JSON to {export_path}[/green]")


@preview_app.command(name="artist")
def preview_artist(
    artist: Annotated[str | None, typer.Option("--artist", help="Artist name.")] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this preview."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this preview."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete preview document as JSON."),
    ] = False,
    save: Annotated[
        bool,
        typer.Option("--save", help="Save preview JSON under exports/previews/artists/."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show full artist metadata, prompt, and diagnostics."),
    ] = False,
) -> None:
    """Preview generated artist enrichment without modifying Plex."""
    if artist is None:
        console.print("[red]Artist preview requires --artist.[/red]")
        raise typer.Exit(code=1)

    service, token = _create_preview_service(provider_name=provider, model=model)

    try:
        document = service.preview_artist(artist=artist)
    except PreviewError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to preview artist enrichment:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(document.model_dump_json(indent=2))
    else:
        _render_artist_preview(document, verbose=verbose)

    if save:
        export_path = _artist_preview_export_path(artist)
        _write_scan_export(export_path, document)
        console.print(f"[green]Saved artist preview JSON to {export_path}[/green]")


@review_app.callback()
def review(
    ctx: typer.Context,
    artist: Annotated[
        str | None,
        typer.Option("--artist", help=ARTIST_OPTION_HELP, hidden=True),
    ] = None,
    album: Annotated[
        str | None,
        typer.Option("--album", help=ALBUM_OPTION_HELP, hidden=True),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help=AI_PROVIDER_REVIEW_HELP, hidden=True),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help=AI_MODEL_REVIEW_HELP, hidden=True),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help=JSON_REVIEW_HELP, hidden=True),
    ] = False,
    translate: Annotated[
        bool,
        typer.Option("--translate", help=TRANSLATE_REVIEW_HELP, hidden=True),
    ] = False,
    improve: Annotated[
        bool,
        typer.Option("--improve", help=IMPROVE_REVIEW_HELP, hidden=True),
    ] = False,
) -> None:
    """Review generated album metadata. Prefer `review album` for new scripts."""
    if ctx.invoked_subcommand is not None:
        return
    _review_album_workflow(
        artist=artist,
        album=album,
        provider=provider,
        model=model,
        json_output=json_output,
        translate=translate,
        improve=improve,
    )


@review_app.command(name="album")
def review_album(
    artist: Annotated[str | None, typer.Option("--artist", help=ARTIST_OPTION_HELP)] = None,
    album: Annotated[str | None, typer.Option("--album", help=ALBUM_OPTION_HELP)] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help=AI_PROVIDER_REVIEW_HELP),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help=AI_MODEL_REVIEW_HELP),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help=JSON_REVIEW_HELP),
    ] = False,
    translate: Annotated[
        bool,
        typer.Option("--translate", help=TRANSLATE_REVIEW_HELP),
    ] = False,
    improve: Annotated[
        bool,
        typer.Option("--improve", help=IMPROVE_REVIEW_HELP),
    ] = False,
) -> None:
    """Review generated album metadata."""
    _review_album_workflow(
        artist=artist,
        album=album,
        provider=provider,
        model=model,
        json_output=json_output,
        translate=translate,
        improve=improve,
    )


def _review_album_workflow(
    *,
    artist: str | None,
    album: str | None,
    provider: str | None,
    model: str | None,
    json_output: bool,
    translate: bool,
    improve: bool,
) -> None:
    """Create and render a shared album review workflow."""
    if artist is None or album is None:
        console.print("[red]Album review requires --artist and --album.[/red]")
        raise typer.Exit(code=1)
    if translate and improve:
        console.print("[red]Choose either --translate or --improve, not both.[/red]")
        raise typer.Exit(code=1)

    service, token = _create_review_service(provider_name=provider, model=model)
    prompt_name = _album_preview_prompt_name(translate=translate, improve=improve)

    try:
        document = (
            service.create_review(artist=artist, album=album)
            if prompt_name == "album_summary"
            else service.create_review(artist=artist, album=album, prompt_name=prompt_name)
        )
    except (PreviewError, ReviewError) as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to create review:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(document.model_dump_json(indent=2))
        return

    _run_review_loop(
        service,
        document,
        ReviewDebugContext(artist=artist, album=album, provider=provider, model=model),
    )


@review_app.command(name="artist")
def review_artist(
    artist: Annotated[str | None, typer.Option("--artist", help=ARTIST_OPTION_HELP)] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help=AI_PROVIDER_REVIEW_HELP),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help=AI_MODEL_REVIEW_HELP),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help=JSON_REVIEW_HELP),
    ] = False,
) -> None:
    """Interactively review generated artist metadata and optionally apply it safely."""
    service, token = _create_review_service(provider_name=provider, model=model)

    try:
        document = service.create_artist_review(artist=artist)
    except (PreviewError, ReviewError) as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to create artist review:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(document.model_dump_json(indent=2))
        return

    _run_review_loop(
        service,
        document,
        ReviewDebugContext(artist=artist, provider=provider, model=model),
    )


@apply_app.callback()
def apply(
    ctx: typer.Context,
    artist: Annotated[str | None, typer.Option("--artist", help="Artist name.")] = None,
    album: Annotated[str | None, typer.Option("--album", help="Album title.")] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this apply run."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this apply run."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete apply result as JSON."),
    ] = False,
    translate: Annotated[
        bool,
        typer.Option("--translate", help="Apply a German translation of the current summary."),
    ] = False,
    improve: Annotated[
        bool,
        typer.Option("--improve", help="Apply an improved German version of the current summary."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Override the configured minimum QA score."),
    ] = False,
) -> None:
    """Apply a generated album summary to Plex with backup, verification, and audit."""
    if ctx.invoked_subcommand is not None:
        return
    if artist is None or album is None:
        console.print("[red]Album apply requires --artist and --album.[/red]")
        raise typer.Exit(code=1)
    if translate and improve:
        console.print("[red]Choose either --translate or --improve, not both.[/red]")
        raise typer.Exit(code=1)

    service, token = _create_apply_service(provider_name=provider, model=model, force=force)
    prompt_name = _album_preview_prompt_name(translate=translate, improve=improve)

    try:
        result = (
            service.apply_album_summary(artist=artist, album=album)
            if prompt_name == "album_summary"
            else service.apply_album_summary(artist=artist, album=album, prompt_name=prompt_name)
        )
    except ApplyError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to apply album summary:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(result.model_dump_json(indent=2, by_alias=True))
    else:
        _render_apply_result(result)

    if result.status != "SUCCESS":
        raise typer.Exit(code=1)


@apply_app.command(name="artist")
def apply_artist(
    artist: Annotated[str, typer.Option("--artist", help="Artist name.")],
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this apply run."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this apply run."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete apply result as JSON."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Override the configured minimum QA score."),
    ] = False,
) -> None:
    """Apply a generated artist biography to Plex with backup, verification, and audit."""
    service, token = _create_apply_service(provider_name=provider, model=model, force=force)

    try:
        result = service.apply_artist_summary(artist=artist)
    except ApplyError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to apply artist biography:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(result.model_dump_json(indent=2, by_alias=True))
    else:
        _render_apply_result(result)

    if result.status != "SUCCESS":
        raise typer.Exit(code=1)


@batch_app.command(name="review")
def batch_review(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to process."),
    ] = None,
    missing_only: Annotated[
        bool,
        typer.Option("--missing-only/--all", help="Only process albums missing summaries."),
    ] = True,
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, help="Maximum number of matching albums to process."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this batch review."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this batch review."),
    ] = None,
    resume: Annotated[
        bool,
        typer.Option("--resume", help="Resume the matching batch job from exports/jobs/."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the final batch report as JSON."),
    ] = False,
) -> None:
    """Review multiple albums sequentially in one interactive session."""
    service, token = _create_batch_review_service(provider_name=provider, model=model)
    options = BatchReviewOptions(
        library=library,
        missing_only=missing_only,
        limit=limit,
        resume=resume,
    )

    try:
        report = service.review_albums(
            options=options,
            display=_render_batch_review_step,
            decide=_batch_review_decision,
            edit=_batch_edit_summary,
        )
    except BatchReviewError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to run batch review:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_batch_review_report(report)

    if report.failed:
        raise typer.Exit(code=1)


@library_app.command(name="plan")
def library_plan(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to process."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the library plan as JSON."),
    ] = False,
) -> None:
    """Plan a complete music library and group albums by workflow action."""
    service, token = _create_library_workflow_service()

    try:
        if json_output:
            report = service.plan_library(library=library)
        else:
            with console.status("Planning complete library workflow..."):
                report = service.plan_library(library=library)
    except LibraryWorkflowError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to plan library:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_library_plan(report)


@library_app.command(name="review")
def library_review(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to process."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this library review."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this library review."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the final library review report as JSON."),
    ] = False,
) -> None:
    """Review generated summaries for a complete library without writing to Plex."""
    _run_library_review(
        library=library,
        provider=provider,
        model=model,
        resume=False,
        json_output=json_output,
    )


@library_app.command(name="resume")
def library_resume(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to process."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for this library review."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for this library review."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the final library review report as JSON."),
    ] = False,
) -> None:
    """Resume an interrupted library review session."""
    _run_library_review(
        library=library,
        provider=provider,
        model=model,
        resume=True,
        json_output=json_output,
    )


@library_app.command(name="apply")
def library_apply(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to process."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="AI provider override for service creation."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="AI model override for service creation."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the library apply report as JSON."),
    ] = False,
) -> None:
    """Apply every approved item from the saved library review session."""
    service, token = _create_library_workflow_service(provider_name=provider, model=model)

    try:
        if json_output:
            report = service.apply_approved(library=library)
        else:
            with console.status("Applying approved library review items..."):
                report = service.apply_approved(library=library)
    except LibraryWorkflowError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to apply library reviews:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_library_review_report(report)

    if report.failed:
        raise typer.Exit(code=1)


@library_app.command(name="report")
def library_report(
    library: Annotated[
        str | None,
        typer.Option("--library", help="Plex music library title to process."),
    ] = None,
    export_json: Annotated[
        bool,
        typer.Option("--export-json", help="Export report JSON to exports/library/report.json."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the library report as JSON."),
    ] = False,
) -> None:
    """Generate a summary report for the saved library workflow session."""
    service, token = _create_library_workflow_service()

    try:
        if json_output:
            report = service.session_report(library=library)
        else:
            with console.status("Loading library workflow report..."):
                report = service.session_report(library=library)
    except LibraryWorkflowError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to report library workflow:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if export_json:
        export_path = Path("exports/library/report.json")
        _write_scan_export(export_path, report)
        console.print(f"[green]Exported library report to {export_path}[/green]")

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_library_review_report(report)


@cache_app.command(name="stats")
def cache_stats() -> None:
    """Show local knowledge cache statistics."""
    stats = KnowledgeCacheStore().stats()
    _render_cache_stats(stats)


@cache_app.command(name="list")
def cache_list() -> None:
    """List local knowledge cache entries."""
    entries = KnowledgeCacheStore().list_entries()
    _render_cache_entries(entries)


@cache_app.command(name="clear")
def cache_clear() -> None:
    """Clear all local knowledge cache entries."""
    removed = KnowledgeCacheStore().clear()
    console.print(f"[green]Removed {removed} cache entr{'y' if removed == 1 else 'ies'}.[/green]")


@debug_app.command(name="prompt")
def debug_prompt(
    copy: Annotated[
        bool,
        typer.Option("--copy", help="Copy the prompt text to the system clipboard when possible."),
    ] = False,
    save: Annotated[
        Path | None,
        typer.Option("--save", help="Save the prompt text to a file."),
    ] = None,
    stats: Annotated[
        bool,
        typer.Option("--stats", help="Show prompt character, word, token and budget statistics."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the prompt debug document as JSON."),
    ] = False,
) -> None:
    """Show the last prompt sent to an AI provider."""
    document = PromptDebugReader().read()
    if json_output:
        _print_json(document.to_dict())
        return
    if save is not None:
        _write_text_file(save, document.content)
    if copy:
        _copy_to_clipboard(document.content)
    DeveloperDebugRenderer(console).render_prompt(document, show_stats=stats)


@debug_app.command(name="meta")
def debug_meta(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print prompt metadata as JSON."),
    ] = False,
) -> None:
    """Show structured metadata for the last prompt."""
    document = PromptMetaReader().read()
    if json_output:
        _print_json(document.to_dict())
        return
    DeveloperDebugRenderer(console).render_meta(document)


@debug_app.command(name="review")
def debug_review(
    summary: Annotated[
        bool,
        typer.Option("--summary", help="Show only high-signal review diagnostics."),
    ] = False,
    section: Annotated[
        str | None,
        typer.Option(
            "--section",
            help=(
                "Show one review-log section, for example prompt, editorial, "
                "verification or coverage."
            ),
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the parsed review log as JSON."),
    ] = False,
) -> None:
    """Show the last review debug log."""
    document = ReviewLogReader().read()
    if json_output:
        _print_json(document.to_dict())
        return
    DeveloperDebugRenderer(console).render_review(document, summary=summary, section=section)


@debug_app.command(name="explain")
def debug_explain(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the explanation as JSON."),
    ] = False,
) -> None:
    """Explain why the last generated biography looks the way it does."""
    explanation = DeveloperAnalyzer().explain()
    if json_output:
        _print_json(explanation.to_dict())
        return
    DeveloperDebugRenderer(console).render_explanation(explanation)


@debug_app.command(name="doctor")
def debug_doctor(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete developer diagnostic report as JSON."),
    ] = False,
) -> None:
    """Run a full developer-mode diagnosis of current debug artifacts."""
    report = DeveloperAnalyzer().doctor()
    if json_output:
        _print_json(report.to_dict())
        return
    DeveloperDebugRenderer(console).render_doctor(report)


def _run_library_review(
    *,
    library: str | None,
    provider: str | None,
    model: str | None,
    resume: bool,
    json_output: bool,
) -> None:
    """Run a library review or resume workflow."""
    service, token = _create_library_workflow_service(provider_name=provider, model=model)

    try:
        report = service.review_library(
            library=library,
            resume=resume,
            display=_render_library_review_step,
            decide=_library_review_decision,
            edit=_batch_edit_summary,
        )
    except LibraryWorkflowError as exc:
        message = _redact_secret(str(exc), token.get_secret_value())
        console.print(f"[red]Unable to run library review:[/red] {message}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json(indent=2, by_alias=True))
    else:
        _render_library_review_report(report)

    if report.failed:
        raise typer.Exit(code=1)


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
        with console.status("Scanning albums..."):
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
        with console.status("Scanning Plex music libraries..."):
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
    plex_url, plex_token = _require_plex_configuration()

    return PlexMusicScanner(plex_url, plex_token), plex_token


def _create_plex_inspector() -> tuple[PlexMetadataInspector, SecretStr]:
    """Create a configured Plex inspector or exit with a user-facing error."""
    plex_url, plex_token = _require_plex_configuration()

    return PlexMetadataInspector(plex_url, plex_token), plex_token


def _create_metadata_auditor() -> tuple[PlexMetadataAuditor, SecretStr]:
    """Create a configured Plex metadata auditor or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    return PlexMetadataAuditor(plex_url, plex_token), plex_token


def _create_capability_analyzer() -> tuple[PlexCapabilityAnalyzer, SecretStr]:
    """Create a configured Plex capability analyzer or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    return PlexCapabilityAnalyzer(plex_url, plex_token), plex_token


def _create_write_probe() -> tuple[PlexWriteProbe, SecretStr]:
    """Create a configured Plex write probe or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    return PlexWriteProbe(plex_url, plex_token), plex_token


def _create_preview_service(
    *,
    provider_name: str | None = None,
    model: str | None = None,
) -> tuple[EnrichmentPreviewService, SecretStr]:
    """Create a configured enrichment preview service or exit with an error."""
    settings, plex_url, plex_token = _require_settings_with_plex_configuration()

    ai_settings = settings.ai
    updates: dict[str, str] = {}
    if provider_name is not None:
        updates["provider"] = provider_name
    if model is not None:
        updates["model"] = model
    if updates:
        ai_settings = ai_settings.model_copy(update=updates)

    try:
        ai_manager = AIManager(settings=ai_settings)
    except AIError as exc:
        console.print(f"[red]AI configuration error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    return EnrichmentPreviewService(plex_url, plex_token, ai_manager=ai_manager), plex_token


def _create_review_service(
    *,
    provider_name: str | None = None,
    model: str | None = None,
) -> tuple[ReviewService, SecretStr]:
    """Create a configured review service or exit with an error."""
    preview_service, token = _create_preview_service(provider_name=provider_name, model=model)
    return ReviewService(preview_service=preview_service), token


def _create_apply_service(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    force: bool = False,
) -> tuple[ApplyService, SecretStr]:
    """Create a configured apply service or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    review_service, token = _create_review_service(provider_name=provider_name, model=model)
    settings = Settings()
    return (
        ApplyService(
            review_service=review_service,
            base_url=plex_url,
            token=plex_token,
            minimum_quality_score=settings.quality.minimum_quality_score,
            verification_confidence_threshold=settings.quality.verification_confidence_threshold,
            force_quality=force,
        ),
        token,
    )


def _create_apply_service_from_review(
    review_service: ReviewService,
) -> tuple[ApplyService, SecretStr]:
    """Create a safe apply service for an already-created review workflow."""
    settings, plex_url, plex_token = _require_settings_with_plex_configuration()
    return (
        ApplyService(
            review_service=review_service,
            base_url=plex_url,
            token=plex_token,
            minimum_quality_score=settings.quality.minimum_quality_score,
            verification_confidence_threshold=settings.quality.verification_confidence_threshold,
        ),
        plex_token,
    )


def _create_batch_review_service(
    *,
    provider_name: str | None = None,
    model: str | None = None,
) -> tuple[BatchReviewService, SecretStr]:
    """Create a configured batch review service or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    review_service, token = _create_review_service(provider_name=provider_name, model=model)
    settings = Settings()
    apply_service = ApplyService(
        review_service=review_service,
        base_url=plex_url,
        token=plex_token,
        minimum_quality_score=settings.quality.minimum_quality_score,
        verification_confidence_threshold=settings.quality.verification_confidence_threshold,
    )
    batch_service = BatchReviewService(
        album_source=PlexBatchAlbumSource(plex_url, plex_token),
        review_service=review_service,
        apply_service=apply_service,
    )
    return batch_service, token


def _create_library_workflow_service(
    *,
    provider_name: str | None = None,
    model: str | None = None,
) -> tuple[LibraryWorkflowService, SecretStr]:
    """Create a configured full-library workflow service or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    review_service, token = _create_review_service(provider_name=provider_name, model=model)
    settings = Settings()
    apply_service = ApplyService(
        review_service=review_service,
        base_url=plex_url,
        token=plex_token,
        minimum_quality_score=settings.quality.minimum_quality_score,
        verification_confidence_threshold=settings.quality.verification_confidence_threshold,
    )
    workflow_service = LibraryWorkflowService(
        album_source=PlexBatchAlbumSource(plex_url, plex_token),
        review_service=review_service,
        apply_service=apply_service,
    )
    return workflow_service, token


def _create_planning_source() -> tuple[PlexBatchAlbumSource, SecretStr]:
    """Create a configured Plex album source for planning."""
    plex_url, plex_token = _require_plex_configuration()

    return PlexBatchAlbumSource(plex_url, plex_token), plex_token


def _create_enrichment_pipeline() -> tuple[EnrichmentPipeline, SecretStr]:
    """Create a configured album context pipeline or exit with an error."""
    plex_url, plex_token = _require_plex_configuration()

    return EnrichmentPipeline(plex_url, plex_token), plex_token


def _require_plex_configuration() -> tuple[AnyHttpUrl, SecretStr]:
    """Return required Plex configuration or exit with a consistent user error."""
    _, plex_url, plex_token = _require_settings_with_plex_configuration()
    return plex_url, plex_token


def _require_settings_with_plex_configuration() -> tuple[Settings, AnyHttpUrl, SecretStr]:
    """Return settings and required Plex values or exit with a consistent user error."""
    try:
        settings = Settings()
    except ValidationError as exc:
        console.print(f"[red]Configuration error:[/red] {_format_validation_error(exc)}")
        raise typer.Exit(code=1) from exc

    if not settings.has_plex_configuration:
        console.print(f"[red]Missing Plex configuration.[/red] {PLEX_CONFIGURATION_HELP}")
        raise typer.Exit(code=1)

    plex_url = settings.plex_url
    plex_token = settings.plex_token
    if plex_url is None or plex_token is None:
        console.print(f"[red]Missing Plex URL or token.[/red] {PLEX_CONFIGURATION_HELP}")
        raise typer.Exit(code=1)

    return settings, plex_url, plex_token


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
    checks.extend(_run_ai_diagnostics(settings))

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


def _run_ai_diagnostics(settings: Settings) -> list[DiagnosticCheck]:
    """Return AI provider diagnostics for doctor."""
    checks: list[DiagnosticCheck] = []
    ai_settings = settings.ai
    configured_api_key = _ai_api_key_configured(ai_settings.api_key)

    checks.append(DiagnosticCheck("AI configured provider", True, ai_settings.provider))
    checks.append(DiagnosticCheck("AI configured model", True, ai_settings.model))
    checks.append(
        DiagnosticCheck(
            "AI API key configured",
            True,
            _yes_no(configured_api_key),
        )
    )
    checks.append(_ai_provider_availability(ai_settings))
    checks.append(DiagnosticCheck("AI cache status", True, _cache_status_detail()))
    checks.append(DiagnosticCheck("AI default prompt version", True, _default_prompt_version()))

    if ai_settings.provider.strip().casefold() == "dummy" and configured_api_key:
        checks.append(
            DiagnosticCheck(
                "AI provider warning",
                True,
                (
                    "An OpenAI API key is configured, but ai.provider is dummy. "
                    "Preview/review will use DummyProvider until you set "
                    "PLEX_ENHANCER_AI__PROVIDER=openai or pass --provider openai."
                ),
            )
        )

    return checks


def _ai_api_key_configured(api_key: SecretStr | None) -> bool:
    """Return whether any AI API key source is configured."""
    configured_value = api_key.get_secret_value().strip() if api_key is not None else ""
    return bool(configured_value or environ.get("OPENAI_API_KEY", "").strip())


def _ai_provider_availability(ai_settings: AISettings) -> DiagnosticCheck:
    """Return availability diagnostics for the configured AI provider."""
    try:
        metadata = AIManager(settings=ai_settings).provider_metadata()
    except AIError as exc:
        return DiagnosticCheck("AI provider availability", False, str(exc))

    detail = (
        f"{metadata.provider} available. "
        f"Album summaries: {_yes_no(metadata.capabilities.album_summary)}. "
        f"Artist summaries: {_yes_no(metadata.capabilities.artist_summary)}. "
        f"Network required: {_yes_no(metadata.capabilities.network_required)}."
    )
    return DiagnosticCheck("AI provider availability", True, detail)


def _cache_status_detail() -> str:
    """Return a compact knowledge cache status."""
    try:
        stats = KnowledgeCacheStore().stats()
    except Exception as exc:
        return f"Unavailable: {exc}"

    return (
        f"{stats.total_entries} entries "
        f"({stats.fresh_entries} fresh, {stats.expired_entries} expired) at {stats.root}"
    )


def _default_prompt_version() -> str:
    """Return the default album prompt version."""
    try:
        return PromptRegistry().get("album_summary").version
    except Exception as exc:
        return f"Unavailable: {exc}"


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


def _render_apply_result(result: ApplyResult) -> None:
    """Render an apply workflow result."""
    table = Table(title="Plex Apply Workflow", show_lines=False)
    table.add_column("Step", style="bold")
    table.add_column("Status")
    table.add_column("Details")
    table.add_row("Status", _format_apply_status(result.status), result.message)
    policy = evaluate_review_policy(result.review)
    table.add_row("Critical validation", policy.critical_validation, "")
    table.add_row("Editorial validation", policy.editorial_validation, "")
    table.add_row("Publishable", "YES" if policy.publishable else "NO", "")
    table.add_row(
        "Backup created",
        _yes_no_plain(result.backup_created),
        result.backup_path or "",
    )
    if result.backup is not None:
        table.add_row(
            "Previous summary length",
            str(len(result.backup.previous_summary)),
            "Stored before the Plex write.",
        )
    table.add_row("Write successful", _yes_no_plain(result.write_successful), "")
    table.add_row("Verification passed", _yes_no_plain(result.verification_passed), "")
    table.add_row("Audit stored", _yes_no_plain(result.audit_stored), result.audit_path or "")
    table.add_row("Audit log", result.audit_path or "", "")
    console.print(table)

    if policy.editorial_validation == "WARNINGS" and policy.publishable:
        console.print("[yellow]Editorial warnings detected.[/yellow]")
        console.print("The generated summary is considered publishable.")
    if result.status != "SUCCESS":
        console.print(f"[red]{result.message}[/red]")


def _render_batch_review_step(step: BatchReviewStep) -> None:
    """Render one album in a batch review session."""
    review = step.review
    console.rule("Album")
    table = Table(show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Library", step.candidate.library)
    table.add_row("Artist", step.candidate.artist)
    table.add_row("Album", step.candidate.album)
    table.add_row("RatingKey", step.candidate.rating_key)
    table.add_row("Recommended action", step.plan.action.value)
    table.add_row("Plan reason", step.plan.reason)
    if review is not None:
        table.add_row("Quality", review.quality.status)
    console.print(table)

    console.rule("Current summary")
    current_summary = (
        review.current_summary if review is not None else step.candidate.current_summary
    )
    console.print(current_summary or "[dim]No current summary.[/dim]")
    if review is None:
        console.print("[yellow]Manual review recommended. No AI output generated.[/yellow]")
        return

    console.rule("Generated summary")
    console.print(review.proposed_summary or "[dim]No generated summary.[/dim]")


def _render_library_plan(report: LibraryPlanReport) -> None:
    """Render a full-library plan grouped by action."""
    table = Table(title="Library Plan")
    table.add_column("Action", style="bold")
    table.add_column("Albums", justify="right")
    table.add_column("Estimated Time")

    for group in report.groups:
        table.add_row(
            group.action.value,
            str(group.count),
            _format_duration(group.estimated_seconds),
        )

    console.print(table)
    console.print(f"Total albums: [bold]{report.total_albums}[/bold]")
    console.print(
        "Estimated processing time: "
        f"[bold]{_format_duration(report.estimated_processing_seconds)}[/bold]"
    )


def _render_library_review_step(step: LibraryReviewStep) -> None:
    """Render one album in a full-library review session."""
    console.rule("Library Review")
    table = Table(show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Artist", step.candidate.artist)
    table.add_row("Album", step.candidate.album)
    table.add_row("Planner decision", step.plan.action.value)
    table.add_row("Quality score", str(step.plan.quality.quality_score))
    table.add_row("Quality issues", ", ".join(issue.value for issue in step.plan.quality.issues))
    console.print(table)

    console.rule("Current summary")
    console.print(step.review.current_summary or "[dim]No current summary.[/dim]")
    console.rule("Generated summary")
    console.print(step.review.proposed_summary or "[dim]No generated summary.[/dim]")


def _render_library_review_report(report: LibraryReviewReport) -> None:
    """Render a full-library workflow report."""
    table = Table(title="Library Workflow Report", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Albums processed", str(report.albums_processed))
    table.add_row("Created", str(report.created))
    table.add_row("Translated", str(report.translated))
    table.add_row("Improved", str(report.improved))
    table.add_row("Skipped", str(report.skipped))
    table.add_row("Approved", str(report.approved))
    table.add_row("Applied", str(report.applied))
    table.add_row("Failed", str(report.failed))
    table.add_row("Average quality score", str(report.average_quality_score))
    table.add_row("Average generation time", f"{report.average_generation_time_seconds:.2f}s")
    table.add_row("Session", report.session_path)
    console.print(table)

    if report.quit_requested:
        console.print(
            "[yellow]Review paused. Use `plex-enhancer library resume` to continue.[/yellow]"
        )


def _batch_review_decision(step: BatchReviewStep) -> BatchDecision:
    """Prompt for one batch review decision."""
    del step
    choice = _review_choice()
    mapping = {
        "A": "APPLY",
        "E": "EDIT",
        "S": "SKIP",
        "Q": "QUIT",
    }
    return mapping.get(choice, "SKIP")


def _library_review_decision(step: LibraryReviewStep) -> BatchDecision:
    """Prompt for one library review decision."""
    del step
    choice = _review_choice()
    mapping: dict[str, BatchDecision] = {
        "A": "APPLY",
        "E": "EDIT",
        "S": "SKIP",
        "Q": "QUIT",
    }
    return mapping.get(choice, "SKIP")


def _batch_edit_summary(document: object) -> str | None:
    """Open the multiline editor for batch summary edits."""
    proposed_summary = getattr(document, "proposed_summary", "")
    return _open_multiline_editor(str(proposed_summary))


def _render_batch_review_report(report: BatchReviewReport) -> None:
    """Render the final batch review summary."""
    table = Table(title="Batch Review Summary", show_lines=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Processed", str(report.processed))
    table.add_row("Applied", str(report.applied))
    table.add_row("Skipped", str(report.skipped))
    table.add_row("Failed", str(report.failed))
    table.add_row("Quit", "yes" if report.quit_requested else "no")
    if report.average_quality_score is not None:
        table.add_row("Average QA score", f"{report.average_quality_score:.2f}")
    if report.lowest_quality_score is not None:
        table.add_row("Lowest QA score", str(report.lowest_quality_score))
    if report.highest_quality_score is not None:
        table.add_row("Highest QA score", str(report.highest_quality_score))
    table.add_row("Albums below threshold", str(report.albums_below_threshold))
    table.add_row("Albums requiring review", str(report.albums_requiring_review))
    table.add_row("Progress", report.job_path or "")
    console.print(table)


def _render_planning_report(report: PlanningReport) -> None:
    """Render enrichment plans as a Rich table."""
    table = Table(title="Enrichment Plan", show_lines=False)
    table.add_column("Album", style="bold", overflow="fold")
    table.add_column("Language")
    table.add_column("Words", justify="right")
    table.add_column("Quality", justify="right")
    table.add_column("Action")
    table.add_column("Reason / Issues", overflow="fold")

    for album in report.albums:
        table.add_row(
            f"{album.artist} - {album.album}",
            album.plan.language,
            str(album.current_summary_words),
            str(album.plan.quality.quality_score),
            album.plan.action.value,
            _planner_diagnostic(album.plan.reason, album.plan.quality.issues),
        )

    console.print(table)


def _planner_diagnostic(reason: str, issues: object) -> str:
    """Return compact planner reason and issue diagnostics."""
    issue_values = [getattr(issue, "value", str(issue)) for issue in issues]
    if not issue_values:
        return reason
    return f"{reason} Issues: {', '.join(issue_values)}"


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


def _render_enrichment_preview(
    document: EnrichmentPreviewDocument,
    *,
    verbose: bool = False,
) -> None:
    """Render an end-to-end generated enrichment preview."""
    context = document.context
    prompt = document.rendered_prompt
    generated = document.generated_summary

    console.rule("GENERATED SUMMARY")
    console.print(generated.text)

    console.rule("AI")
    ai = Table(show_header=False)
    ai.add_column("Field", style="bold")
    ai.add_column("Value")
    ai.add_row("Provider", generated.provider)
    ai.add_row("Model", generated.model)
    ai.add_row("Prompt version", generated.prompt_version)
    if verbose:
        ai.add_row("Prompt name", generated.prompt_name)
        ai.add_row("Token usage", _format_token_usage(generated.metadata))
        ai.add_row("Generation time", f"{document.generation_time_seconds:.3f}s")
        _add_prompt_budget_rows(ai, prompt.budget_diagnostics)
    console.print(ai)

    warnings = context.pipeline.warnings
    if warnings:
        console.rule("Warnings")
        for warning in warnings:
            console.print(f"[yellow]{warning}[/yellow]")

    if not verbose:
        return

    console.rule("PLEX")
    plex = Table(show_header=False)
    plex.add_column("Field", style="bold")
    plex.add_column("Value")
    plex.add_row("Artist", context.plex.artist)
    plex.add_row("Album", context.plex.album)
    plex.add_row("Year", str(context.plex.year or ""))
    plex.add_row("Current summary", context.plex.summary or "")
    plex.add_row("Genres", ", ".join(context.plex.genres))
    console.print(plex)

    console.rule("MUSICBRAINZ")
    musicbrainz = Table(show_header=False)
    musicbrainz.add_column("Field", style="bold")
    musicbrainz.add_column("Value")
    musicbrainz.add_row(
        "Match",
        _yes_no(context.musicbrainz.release_group_mbid is not None),
    )
    musicbrainz.add_row("Artist MBID", context.musicbrainz.artist_mbid or "")
    musicbrainz.add_row("Release Group", context.musicbrainz.release_group_mbid or "")
    musicbrainz.add_row("Release", context.musicbrainz.release_mbid or "")
    musicbrainz.add_row("Release Date", context.musicbrainz.release_date or "")
    musicbrainz.add_row("Match confidence", str(context.musicbrainz.confidence))
    console.print(musicbrainz)

    console.rule("WIKIPEDIA")
    wikipedia = Table(show_header=False)
    wikipedia.add_column("Field", style="bold")
    wikipedia.add_column("Value")
    wikipedia.add_row("Article status", "available" if context.wikipedia.extract else "missing")
    wikipedia.add_row("Language", context.wikipedia.language or "")
    wikipedia.add_row("Title", context.wikipedia.title or "")
    wikipedia.add_row("Extract", context.wikipedia.extract or "")
    wikipedia.add_row("Page URL", context.wikipedia.page_url or "")
    console.print(wikipedia)

    _render_fact_verification(context.fact_collection)

    console.rule("PROMPT")
    prompt_table = Table(show_header=False)
    prompt_table.add_column("Field", style="bold")
    prompt_table.add_column("Value")
    prompt_table.add_row("Prompt name", prompt.name)
    prompt_table.add_row("Prompt version", prompt.version)
    prompt_table.add_row("Variables used", ", ".join(sorted(prompt.variables)))
    _add_prompt_budget_rows(prompt_table, prompt.budget_diagnostics)
    console.print(prompt_table)

    console.rule("Warnings")
    if warnings:
        for warning in warnings:
            console.print(f"[yellow]{warning}[/yellow]")
    else:
        console.print("[green]None[/green]")


def _render_fact_verification(
    collection: FactCollection,
    *,
    categories: tuple[str, ...] = SUPPORTED_CATEGORIES,
) -> None:
    """Render deterministic fact confidence diagnostics."""
    console.rule("FACT VERIFICATION")
    table = Table(show_header=True)
    table.add_column("Fact", style="bold")
    table.add_column("Status")
    table.add_column("Confidence", justify="right")
    table.add_column("Sources")
    table.add_column("Value")

    for category in categories:
        facts = collection.by_category(category)
        if not facts:
            table.add_row(_display_category(category), "UNKNOWN", "0.00", "", "")
            continue
        fact = sorted(
            facts,
            key=lambda item: (
                item.verification_state.value == "unknown",
                -item.confidence_score,
                item.value,
            ),
        )[0]
        table.add_row(
            _display_category(category),
            fact.verification_state.value.upper(),
            f"{fact.confidence_score:.2f}",
            ", ".join(fact.supporting_sources),
            fact.value,
        )

    if collection.conflicts:
        conflict_summary = "; ".join(
            f"{fact.category}: {fact.value}" for fact in collection.conflicts
        )
    else:
        conflict_summary = "none"
    table.add_row("Conflicts", "", "", "", conflict_summary)
    console.print(table)


def _display_category(category: str) -> str:
    """Return a readable fact category label."""
    return category.replace("_", " ").title()


def _add_prompt_budget_rows(table: Table, diagnostics: dict[str, object] | None) -> None:
    """Add prompt budget diagnostics to a Rich table."""
    if not diagnostics:
        return
    table.add_row("Prompt budget", str(diagnostics.get("max_characters", "")))
    table.add_row("Current size", str(diagnostics.get("original_size", "")))
    table.add_row("Trimmed size", str(diagnostics.get("final_size", "")))
    contributions = diagnostics.get("per_source_contribution")
    if isinstance(contributions, list):
        summary = []
        for item in contributions:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            original = item.get("original_size")
            final = item.get("final_size")
            if name is not None:
                summary.append(f"{name}: {original}->{final}")
        if summary:
            table.add_row("Per-source contribution", "; ".join(summary))


def _render_artist_preview(
    document: ArtistPreviewDocument,
    *,
    verbose: bool = False,
) -> None:
    """Render an end-to-end generated artist preview."""
    context = document.context
    prompt = document.rendered_prompt
    generated = document.generated_summary

    console.rule("GENERATED BIOGRAPHY")
    console.print(generated.text)

    console.rule("AI")
    ai = Table(show_header=False)
    ai.add_column("Field", style="bold")
    ai.add_column("Value")
    ai.add_row("Provider", generated.provider)
    ai.add_row("Model", generated.model)
    ai.add_row("Prompt version", generated.prompt_version)
    if verbose:
        ai.add_row("Prompt name", generated.prompt_name)
        ai.add_row("Prompt variables", ", ".join(sorted(prompt.variables)))
        ai.add_row("Token usage", _format_token_usage(generated.metadata))
        ai.add_row("Generation time", f"{document.generation_time_seconds:.3f}s")
        _add_prompt_budget_rows(ai, prompt.budget_diagnostics)
    console.print(ai)

    warnings = context.pipeline.warnings
    if warnings:
        console.rule("Warnings")
        for warning in warnings:
            console.print(f"[yellow]{warning}[/yellow]")

    if not verbose:
        return

    console.rule("PLEX")
    plex = Table(show_header=False)
    plex.add_column("Field", style="bold")
    plex.add_column("Value")
    plex.add_row("Artist", context.plex.artist)
    plex.add_row("Current biography", context.plex.summary or "")
    plex.add_row("Genres", ", ".join(context.plex.genres))
    plex.add_row("Styles", ", ".join(context.styles))
    plex.add_row("Career years", document.career_years)
    console.print(plex)

    console.rule("MUSICBRAINZ")
    musicbrainz = Table(show_header=False)
    musicbrainz.add_column("Field", style="bold")
    musicbrainz.add_column("Value")
    musicbrainz.add_row("Artist MBID", context.musicbrainz.artist_mbid or "")
    musicbrainz.add_row("Confidence", str(context.musicbrainz.confidence))
    musicbrainz.add_row("Aliases", ", ".join(context.musicbrainz.aliases or context.aliases))
    musicbrainz.add_row("Genres", ", ".join(context.musicbrainz.genres))
    console.print(musicbrainz)

    console.rule("WIKIPEDIA")
    wikipedia = Table(show_header=False)
    wikipedia.add_column("Field", style="bold")
    wikipedia.add_column("Value")
    wikipedia.add_row("Article status", "available" if context.wikipedia.extract else "missing")
    wikipedia.add_row("Language", context.wikipedia.language or "")
    wikipedia.add_row("Title", context.wikipedia.title or "")
    wikipedia.add_row("Extract", context.wikipedia.extract or "")
    wikipedia.add_row("URL", context.wikipedia.page_url or "")
    console.print(wikipedia)

    console.rule("DISCOGS")
    discogs = Table(show_header=False)
    discogs.add_column("Field", style="bold")
    discogs.add_column("Value")
    discogs_context = document.resolved_prompt_variables.get("discogs_context")
    if isinstance(discogs_context, dict) and discogs_context:
        discogs.add_row("Status", "available")
        for key, value in discogs_context.items():
            discogs.add_row(_display_category(key), _display_prompt_value(value))
    else:
        discogs.add_row("Status", "No additional artist information available.")
    console.print(discogs)

    console.rule("LAST.FM")
    lastfm = Table(show_header=False)
    lastfm.add_column("Field", style="bold")
    lastfm.add_column("Value")
    lastfm.add_row("Biography status", "available" if context.lastfm.biography else "missing")
    lastfm.add_row("Listeners", str(context.lastfm.listeners or ""))
    lastfm.add_row("Playcount", str(context.lastfm.playcount or ""))
    lastfm.add_row("Tags", ", ".join(context.lastfm.tags))
    console.print(lastfm)

    _render_fact_verification(
        context.fact_collection,
        categories=SUPPORTED_ARTIST_CATEGORIES,
    )

    _render_quality_report(document.qa_report)

    console.rule("PROMPT")
    prompt_table = Table(show_header=False)
    prompt_table.add_column("Field", style="bold")
    prompt_table.add_column("Value")
    prompt_table.add_row("Prompt name", prompt.name)
    prompt_table.add_row("Prompt version", prompt.version)
    prompt_table.add_row("Variables used", ", ".join(sorted(prompt.variables)))
    _add_prompt_budget_rows(prompt_table, prompt.budget_diagnostics)
    for key, value in document.resolved_prompt_variables.items():
        prompt_table.add_row(_display_category(key), _display_prompt_value(value))
    console.print(prompt_table)

    console.rule("KNOWLEDGE BUILDER")
    knowledge = Table(show_header=False)
    knowledge.add_column("Field", style="bold")
    knowledge.add_column("Value")
    for key, value in document.knowledge_summary.items():
        knowledge.add_row(_display_category(key), _display_prompt_value(value))
    console.print(knowledge)

    console.rule("CONTEXT BUILDER")
    context_table = Table(show_header=False)
    context_table.add_column("Field", style="bold")
    context_table.add_column("Value")
    for source, status in document.source_availability.items():
        context_table.add_row(f"{source.title()} source", status)
    for key, value in document.context_summary.items():
        context_table.add_row(_display_category(key), _display_prompt_value(value))
    console.print(context_table)

    _render_artist_style_analysis(document)

    console.rule("Warnings")
    if warnings:
        for warning in warnings:
            console.print(f"[yellow]{warning}[/yellow]")
    else:
        console.print("[green]None[/green]")


def _render_quality_report(report: object | None) -> None:
    """Render editorial QA report when available."""
    console.rule("EDITORIAL QUALITY")
    if report is None:
        console.print("[yellow]No editorial quality report available.[/yellow]")
        return
    quality = Table(show_header=False)
    quality.add_column("Field", style="bold")
    quality.add_column("Value")
    quality.add_row("Overall score", str(report.overall_score))
    quality.add_row("Quality level", str(report.quality_level or report.overall_level or ""))
    quality.add_row("Missing topics", ", ".join(report.missing_topics))
    if report.recommendations:
        quality.add_row("Recommendations", "; ".join(str(item) for item in report.recommendations))
    console.print(quality)


def _display_prompt_value(value: object) -> str:
    """Return a readable value for verbose prompt/context diagnostics."""
    if isinstance(value, dict):
        return "; ".join(
            f"{_display_category(str(key))}: {_display_prompt_value(item)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        return ", ".join(_display_prompt_value(item) for item in value)
    if isinstance(value, bool):
        return _yes_no(value)
    return str(value)


def _render_artist_style_analysis(document: ArtistPreviewDocument) -> None:
    """Render artist style diagnostics from preview data."""
    diagnostics = document.style_diagnostics or GermanEditorialStyleEngine().analyze(
        document.generated_summary.text,
        artist=document.context.plex.artist,
        album=None,
    )
    table = Table(title="STYLE ANALYSIS", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Result")
    table.add_row("Sentence variation", diagnostics.sentence_variation)
    table.add_row("Vocabulary diversity", diagnostics.vocabulary_diversity)
    table.add_row("Repetition", diagnostics.repetition)
    table.add_row("Readability", diagnostics.readability)
    table.add_row("LLM clichés", diagnostics.llm_cliches)
    table.add_row("Passive voice", diagnostics.passive_voice)
    table.add_row("Overall style", diagnostics.overall_style)
    if diagnostics.issues:
        table.add_row("Issues", ", ".join(diagnostics.issues))
    console.print(table)


def _render_style_analysis(text: str, *, artist: str | None, album: str | None) -> None:
    """Render generated German style diagnostics."""
    diagnostics = GermanEditorialStyleEngine().analyze(text, artist=artist, album=album)
    table = Table(title="STYLE ANALYSIS", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Result")
    table.add_row("Sentence variation", diagnostics.sentence_variation)
    table.add_row("Vocabulary diversity", diagnostics.vocabulary_diversity)
    table.add_row("Repetition", diagnostics.repetition)
    table.add_row("Readability", diagnostics.readability)
    table.add_row("LLM clichés", diagnostics.llm_cliches)
    table.add_row("Passive voice", diagnostics.passive_voice)
    table.add_row("Overall style", diagnostics.overall_style)
    if diagnostics.issues:
        table.add_row("Issues", ", ".join(diagnostics.issues))
    console.print(table)


def _render_cache_stats(stats: CacheStats) -> None:
    """Render local knowledge cache statistics."""
    table = Table(title="Knowledge Cache")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Location", str(stats.root))
    table.add_row("Total entries", str(stats.total_entries))
    table.add_row("Fresh entries", str(stats.fresh_entries))
    table.add_row("Expired entries", str(stats.expired_entries))
    for kind, count in stats.by_kind.items():
        table.add_row(f"{kind.value.title()} entries", str(count))
    for source, count in sorted(stats.by_source.items()):
        table.add_row(f"{source} entries", str(count))
    console.print(table)


def _render_cache_entries(entries: list[CacheEntryInfo]) -> None:
    """Render local knowledge cache entries."""
    if not entries:
        console.print("[yellow]No cache entries found.[/yellow]")
        return

    table = Table(title="Knowledge Cache Entries")
    table.add_column("Kind")
    table.add_column("Source")
    table.add_column("Cached at")
    table.add_column("Status")
    table.add_column("Path")
    for entry in entries:
        table.add_row(
            entry.kind.value,
            entry.source,
            entry.cached_at.isoformat(),
            "expired" if entry.expired else "fresh",
            str(entry.path),
        )
    console.print(table)


def _render_benchmark_report(report: BenchmarkReport) -> None:
    """Render benchmark diagnostics."""
    table = Table(title="Performance Benchmark")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Library", report.library or "All music libraries")
    table.add_row("Albums scanned", str(report.albums_scanned))
    table.add_row("Scan duration", f"{report.scan_duration_seconds:.4f}s")
    table.add_row("Throughput", f"{report.throughput_per_hour:.2f} albums/hour")
    table.add_row("CPU time", f"{report.cpu_time_seconds:.4f}s")
    table.add_row("Memory", f"{report.memory_mb:.2f} MiB")
    table.add_row("Cache entries", str(report.cache_entries))
    table.add_row("Expired cache entries", str(report.cache_expired_entries))
    if report.cache_hit_ratio_estimate is not None:
        table.add_row("Cache freshness", f"{report.cache_hit_ratio_estimate:.2%}")
    for provider, duration in sorted(report.provider_timings.items()):
        table.add_row(f"{provider} timing", f"{duration:.4f}s")
    if report.slowest_operations:
        table.add_row("Slowest operations", ", ".join(report.slowest_operations))
    table.add_row("Recommendations", "\n".join(report.recommendations))
    console.print(table)


def _format_token_usage(metadata: dict[str, object]) -> str:
    """Return token usage from generated summary metadata."""
    prompt_tokens = metadata.get("prompt_tokens")
    completion_tokens = metadata.get("completion_tokens")
    if prompt_tokens is None and completion_tokens is None:
        return "not reported"

    return f"prompt={prompt_tokens or 0}, completion={completion_tokens or 0}"


def _review_choice() -> str:
    """Prompt for one review workflow choice."""
    return typer.prompt("[A] Apply  [E] Edit  [S] Skip  [Q] Quit").strip().upper()[:1]


def _open_multiline_editor(initial_text: str) -> str | None:
    """Open a terminal editor for multiline summary edits."""
    edited = click_edit(text=initial_text)
    if edited is None:
        return None

    return edited.strip()


def _run_review_loop(
    service: ReviewService,
    document: ReviewDocument,
    debug_context: ReviewDebugContext,
) -> None:
    """Run the shared interactive review loop."""
    renderer = ReviewRenderer(console)
    debug_logger = ReviewDebugLogger()
    _render_review_document(renderer, debug_logger, debug_context, document)

    while True:
        choice = _review_choice()
        if choice == "A":
            policy = evaluate_review_policy(document)
            if not policy.apply_allowed:
                for message in [*policy.critical_failures, *policy.messages]:
                    console.print(f"[red]{message}[/red]")
                console.print("[red]Generated summary must pass validation before Apply.[/red]")
                continue
            if policy.editorial_validation == "WARNINGS":
                console.print("[yellow]Editorial warnings detected.[/yellow]")
                console.print("The generated summary is considered publishable.")
                console.print("You may still Apply this summary.")
                if not typer.confirm("Continue?", default=True):
                    continue

            apply_service, _ = _create_apply_service_from_review(service)
            result = apply_service.apply_review(document)
            _render_apply_result(result)
            if result.status != "SUCCESS":
                raise typer.Exit(code=1)
            return

        if choice == "E":
            edited_text = _open_multiline_editor(document.proposed_summary)
            if edited_text is None:
                console.print("[yellow]Edit cancelled.[/yellow]")
                continue

            document = service.update_summary(document, edited_text)
            _render_review_document(renderer, debug_logger, debug_context, document)
            continue

        if choice == "S":
            console.print("[yellow]Skipped. No changes were made.[/yellow]")
            return

        if choice == "Q":
            console.print("[yellow]Quit. No changes were made.[/yellow]")
            return

        console.print("[red]Choose A, E, S, or Q.[/red]")


def _render_review_document(
    renderer: ReviewRenderer,
    debug_logger: ReviewDebugLogger,
    debug_context: ReviewDebugContext,
    document: ReviewDocument,
) -> None:
    """Render a review document and refresh the temporary debug log."""
    debug_logger.write(document, debug_context)
    renderer.render(document)


def _yes_no(value: bool) -> str:
    """Return a Rich status label."""
    return "[green]yes[/green]" if value else "[red]no[/red]"


def _yes_no_plain(value: bool) -> str:
    """Return a plain yes/no value."""
    return "yes" if value else "no"


def _format_duration(seconds: int) -> str:
    """Return a compact human-readable duration."""
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes == 0:
        return f"{remaining_seconds}s"

    hours, remaining_minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{remaining_minutes}m {remaining_seconds}s"

    return f"{hours}h {remaining_minutes}m"


def _format_probe_status(status: str) -> str:
    """Return a Rich-formatted write probe status."""
    if status == "SUCCESS":
        return "[green]SUCCESS[/green]"
    if status == "READ_ONLY":
        return "[yellow]READ_ONLY[/yellow]"
    if status == "FAILED":
        return "[red]FAILED[/red]"

    return status


def _format_apply_status(status: str) -> str:
    """Return a Rich-formatted apply status."""
    if status == "SUCCESS":
        return "[green]SUCCESS[/green]"

    return "[red]FAILED[/red]"


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
    write_text_atomic(export_path, scan_export.model_dump_json(indent=2, by_alias=True) + "\n")


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


def _preview_export_path(artist: str, album: str) -> Path:
    """Return the export path for saved preview output."""
    filename = f"{_safe_export_segment(artist)}-{_safe_export_segment(album)}.json"
    return Path("exports") / "previews" / filename


def _artist_preview_export_path(artist: str) -> Path:
    """Return the export path for saved artist preview output."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"Artist-Preview-{_safe_export_segment(artist)}-{timestamp}.json"
    return Path("exports") / "previews" / "artists" / filename


def _album_preview_prompt_name(*, translate: bool, improve: bool) -> str:
    """Return the album prompt template selected by preview options."""
    if translate:
        return "album_translate"
    if improve:
        return "album_improve"

    return "album_summary"


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

    write_text_atomic(env_path, "\n".join(updated_lines) + "\n")


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


def _print_json(payload: object) -> None:
    """Print a JSON-serializable payload."""
    console.print_json(dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _write_text_file(path: Path, content: str) -> None:
    """Write text to a user-selected file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(path, content)
    console.print(f"[green]Saved debug output to {path}[/green]")


def _copy_to_clipboard(content: str) -> None:
    """Copy text to the system clipboard when a supported command is available."""
    if not content:
        console.print("[yellow]Nothing to copy.[/yellow]")
        return
    command = _clipboard_command()
    if command is None:
        console.print("[yellow]No supported clipboard command found.[/yellow]")
        return
    try:
        subprocess.run(  # noqa: S603 - fixed command chosen from known clipboard tools.
            command,
            input=content,
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        console.print("[yellow]Unable to copy prompt to the clipboard.[/yellow]")
    else:
        console.print("[green]Copied prompt to clipboard.[/green]")


def _clipboard_command() -> list[str] | None:
    """Return a platform clipboard command."""
    if sys.platform == "darwin" and Path("/usr/bin/pbcopy").exists():
        return ["/usr/bin/pbcopy"]
    if sys.platform.startswith("win"):
        return ["clip"]
    for command in ("wl-copy", "xclip", "xsel"):
        executable = which(command)
        if executable:
            if command == "xclip":
                return [executable, "-selection", "clipboard"]
            if command == "xsel":
                return [executable, "--clipboard", "--input"]
            return [executable]
    return None


if __name__ == "__main__":
    app()
