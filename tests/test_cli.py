"""CLI tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tomllib import loads

from pydantic import SecretStr
from typer.testing import CliRunner

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.ai.dummy import DUMMY_SUMMARY_TEXT
from plex_music_enhancer.apply import ApplyResult
from plex_music_enhancer.batch import BatchAlbumCandidate, BatchReviewOptions, BatchReviewReport
from plex_music_enhancer.cache import CacheKind, KnowledgeCacheStore
from plex_music_enhancer.cli import DiagnosticCheck, app
from plex_music_enhancer.constants import __version__
from plex_music_enhancer.editorial import GermanEditorialStyleEngine
from plex_music_enhancer.enrichment import (
    AlbumContext,
    ArtistContext,
    DiscogsArtistContext,
    LastFMArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.plex import (
    AlbumAuditFinding,
    AlbumScanExport,
    AlbumScanItem,
    AlbumWriteVerificationReport,
    ArtistAuditFinding,
    ArtistScanExport,
    ArtistScanItem,
    AuditStatistics,
    InspectChild,
    InspectedPlexObject,
    InspectImage,
    LibraryAuditResult,
    LibraryCapability,
    MetadataAuditReport,
    MusicLibraryScanExport,
    MusicLibraryStats,
    ObjectCapabilityAnalysis,
    PlexCapabilityAnalysis,
    PlexScannerError,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.review import QualityReport, ReviewDocument
from plex_music_enhancer.services import (
    AlbumMetadata,
    AlbumMetadataDocument,
    ArtistPreviewDocument,
    EnrichmentPreviewDocument,
    MatchResult,
    MusicBrainzEnrichmentMetadata,
    PlexAlbumMetadata,
    PreviewError,
)

runner = CliRunner()


def test_serve_help_documents_default_port_8080() -> None:
    result = runner.invoke(app, ["serve", "--help"])

    assert result.exit_code == 0
    assert "[default: 8080]" in result.stdout
    assert "PLEX_ENHANCER_WEB__PORT" in result.stdout


def _metadata_document() -> AlbumMetadataDocument:
    return AlbumMetadataDocument(
        plex=PlexAlbumMetadata(
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary=None,
        ),
        musicbrainz=MusicBrainzEnrichmentMetadata(
            matched=True,
            confidence=96,
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            primary_type="Album",
            secondary_types=[],
            genres=["jazz", "soul"],
            tags=["blues"],
        ),
        metadata=AlbumMetadata(
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            genres=["jazz", "soul"],
            summary=None,
            sources=["plex", "musicbrainz"],
            confidence=96,
        ),
    )


def _album_context() -> AlbumContext:
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Current Plex summary",
            genres=["Jazz", "Soul"],
            styles=["Vocal Jazz"],
            moods=["Melancholy"],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            genres=["jazz"],
            tags=["blues"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(
            language="en",
            title="Pastel Blues",
            extract="Wikipedia summary",
            page_url="https://en.wikipedia.org/wiki/Pastel_Blues",
            thumbnail_url="https://example.test/pastel.jpg",
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )


def _match_result() -> MatchResult:
    return MatchResult(
        matched=True,
        confidence=96,
        artist_mbid="artist-mbid",
        release_group_mbid="release-group-mbid",
        release_mbid="release-mbid",
        artist_name="Nina Simone",
        album_title="Pastel Blues",
        first_release_date="1965-10",
        release_year=1965,
        primary_type="Album",
        secondary_types=["Compilation"],
        score_breakdown={"album_similarity": 100.0},
        warnings=["Release year is missing or distant from the requested year."],
    )


def _preview_document() -> EnrichmentPreviewDocument:
    return EnrichmentPreviewDocument(
        context=_album_context(),
        rendered_prompt=RenderedPrompt(
            name="album_summary",
            version="1.0",
            rendered_text="Artist: Nina Simone\nAlbum: Pastel Blues\nLanguage: de\n",
            variables={
                "artist": "Nina Simone",
                "album": "Pastel Blues",
                "language": "de",
            },
            template="Artist: {{artist}}\nAlbum: {{album}}\nLanguage: {{language}}\n",
        ),
        generated_summary=GeneratedSummary(
            language="en",
            text=DUMMY_SUMMARY_TEXT,
            provider="dummy",
            model="dummy-v1",
            prompt_name="dummy_album_summary",
            prompt_version="1.0",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=1.0,
            source_count=3,
            metadata={"artist": "Nina Simone", "album": "Pastel Blues"},
        ),
        generation_time_seconds=0.123,
    )


def _artist_preview_document() -> ArtistPreviewDocument:
    return ArtistPreviewDocument(
        context=ArtistContext(
            plex=PlexArtistContext(
                rating_key="100",
                artist="Nina Simone",
                summary="Current artist summary",
                genres=["Jazz"],
            ),
            musicbrainz=MusicBrainzArtistContext(
                artist_mbid="artist-mbid",
                artist_name="Nina Simone",
                genres=["jazz"],
                confidence=100,
            ),
            wikipedia=WikipediaArtistContext(
                language="de",
                title="Nina Simone",
                extract="Wikipedia biography",
                page_url="https://de.wikipedia.org/wiki/Nina_Simone",
            ),
            discogs=DiscogsArtistContext(
                profile="Discogs career profile",
                active_years="1954-2003",
                styles=["Vocal Jazz"],
            ),
            lastfm=LastFMArtistContext(
                biography="Last.fm biography",
                tags=["soul"],
                listeners=1000,
                playcount=2000,
            ),
            pipeline=PipelineContext(
                collected_sources=["plex", "musicbrainz", "wikipedia"],
                missing_fields=[],
                warnings=[],
                ready_for_generation=True,
            ),
            active_years="1954-2003",
            styles=["Vocal Jazz"],
            labels=["Philips"],
        ),
        rendered_prompt=RenderedPrompt(
            name="artist_summary",
            version="1.0",
            rendered_text="Artist: Nina Simone\nLanguage: de\n",
            variables={"artist": "Nina Simone", "language": "de"},
            template="Artist: {{artist}}\nLanguage: {{language}}\n",
            budget_diagnostics={
                "max_characters": 20000,
                "original_size": 42,
                "final_size": 42,
                "trimmed_size": 0,
                "trimmed": False,
                "per_source_contribution": [
                    {
                        "name": "artist",
                        "original_size": 11,
                        "final_size": 11,
                        "trimmed": False,
                    }
                ],
            },
        ),
        generated_summary=GeneratedSummary(
            language="de",
            text=_german_summary(),
            provider="dummy",
            model="dummy-v1",
            prompt_name="artist_summary",
            prompt_version="1.0",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=1.0,
            source_count=3,
            metadata={"artist": "Nina Simone"},
        ),
        generation_time_seconds=0.123,
        style_diagnostics=GermanEditorialStyleEngine().analyze(
            _german_summary(),
            artist="Nina Simone",
        ),
        career_years="1954-2003",
        source_availability={
            "plex": "available",
            "musicbrainz": "available",
            "wikipedia": "available",
            "discogs": "available",
            "lastfm": "available",
        },
        editorial_recommendations=["Important albums available but not mentioned."],
        resolved_prompt_variables={
            "artist": "Nina Simone",
            "genres": ["Jazz"],
            "styles": ["Vocal Jazz"],
            "career_years": "1954-2003",
            "discogs_context": {
                "profile": "Discogs career profile",
                "active_years": "1954-2003",
                "styles": ["Vocal Jazz"],
            },
            "lastfm_context": {"tags": ["soul"], "listeners": 1000, "playcount": 2000},
            "wikipedia_extract": "Wikipedia biography",
            "current_summary": "Current artist summary",
        },
        knowledge_summary={
            "fact_count": 3,
            "verified_count": 2,
            "probable_count": 1,
            "conflict_count": 0,
            "missing_facts": [],
        },
        context_summary={
            "collected_sources": ["plex", "musicbrainz", "wikipedia"],
            "missing_fields": [],
            "warnings": [],
            "ready_for_generation": True,
        },
    )


def _review_document(
    *, status: str = "PASS", proposed_summary: str | None = None
) -> ReviewDocument:
    """Return a review document fixture."""
    return ReviewDocument(
        preview=_preview_document(),
        current_summary="Aktuelle Plex-Zusammenfassung.",
        proposed_summary=proposed_summary or _german_summary(),
        diff=(
            "--- current summary\n"
            "+++ generated summary\n"
            "-Aktuelle Plex-Zusammenfassung.\n"
            "+Neue Zusammenfassung."
        ),
        quality=QualityReport(
            status=status,  # type: ignore[arg-type]
            checks={
                "not_empty": status != "FAILED",
                "language_is_german": True,
                "length_in_range": status == "PASS",
                "no_markdown": True,
                "no_bullet_lists": True,
                "no_placeholder_text": True,
            },
            warnings=[] if status == "PASS" else ["Needs review."],
            failures=[] if status != "FAILED" else ["Summary is empty."],
            word_count=90 if status == "PASS" else 0,
        ),
    )


def _artist_review_document() -> ReviewDocument:
    """Return an artist review document fixture."""
    return ReviewDocument(
        preview=_artist_preview_document(),
        current_summary="Current artist summary",
        proposed_summary=_german_summary(),
        diff="--- current summary\n+++ generated summary\n",
        quality=QualityReport(
            status="PASS",
            checks={
                "not_empty": True,
                "language_is_german": True,
                "length_in_range": True,
                "no_markdown": True,
                "no_bullet_lists": True,
                "no_placeholder_text": True,
            },
            warnings=[],
            failures=[],
            word_count=90,
        ),
    )


def _german_summary() -> str:
    """Return valid German summary fixture."""
    words = [
        "Das",
        "Album",
        "ist",
        "eine",
        "sachliche",
        "Beschreibung",
        "mit",
        "verifizierbaren",
        "Angaben",
        "und",
        "neutraler",
        "Sprache",
    ]
    return " ".join(words[index % len(words)] for index in range(90)) + "."


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ == "1.0.0"
    assert result.stdout.strip() == "plex-enhancer 1.0.0"


def test_pyproject_uses_constants_as_canonical_version_source() -> None:
    pyproject = loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dynamic"] == ["version"]
    assert "version" not in pyproject["project"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == ("src/plex_music_enhancer/constants.py")


def test_root_help_includes_examples() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Examples" in result.stdout
    assert "plex-enhancer doctor" in result.stdout


def test_library_help_includes_examples() -> None:
    result = runner.invoke(app, ["library", "--help"])

    assert result.exit_code == 0
    assert "Examples" in result.stdout
    assert "plex-enhancer library plan" in result.stdout


def test_doctor_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "Python version" in result.stdout
    assert "Configuration" in result.stdout
    assert "Plex connection" in result.stdout
    assert "AI configured provider" in result.stdout
    assert "dummy" in result.stdout
    assert "AI provider availability" in result.stdout
    assert "AI cache status" in result.stdout
    assert "AI default prompt version" in result.stdout


def test_doctor_warns_when_dummy_provider_uses_openai_key(monkeypatch) -> None:
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_AI__PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "AI configured provider" in result.stdout
    assert "dummy" in result.stdout
    assert "AI API key configured" in result.stdout
    assert "yes" in result.stdout
    assert "AI provider warning" in result.stdout
    assert "An OpenAI API key is configured" in result.stdout
    assert "ai.provider is dummy" in result.stdout
    assert "DummyProvider" in result.stdout


def test_doctor_reports_openai_provider_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PLEX_ENHANCER_AI__PROVIDER", "openai")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "AI configured provider" in result.stdout
    assert "openai" in result.stdout
    assert "AI API key configured" in result.stdout
    assert "no" in result.stdout
    assert "AI provider availability" in result.stdout
    assert "OpenAI provider requires OPENAI_API_KEY" in result.stdout


def test_cache_commands_manage_local_entries(monkeypatch, tmp_path: Path) -> None:
    store = KnowledgeCacheStore(root=tmp_path / "cache")
    store.write(
        kind=CacheKind.ALBUMS,
        source="musicbrainz",
        key="album-key",
        payload={"title": "Pastel Blues"},
    )
    monkeypatch.setattr("plex_music_enhancer.cli.KnowledgeCacheStore", lambda: store)

    stats_result = runner.invoke(app, ["cache", "stats"])
    list_result = runner.invoke(app, ["cache", "list"])
    clear_result = runner.invoke(app, ["cache", "clear"])

    assert stats_result.exit_code == 0
    assert "Total entries" in stats_result.stdout
    assert "1" in stats_result.stdout
    assert list_result.exit_code == 0
    assert "musicbrainz" in list_result.stdout
    assert clear_result.exit_code == 0
    assert "Removed 1 cache entry" in clear_result.stdout
    assert store.list_entries() == []


def test_login_saves_env_and_runs_doctor(monkeypatch, tmp_path: Path) -> None:
    class FakePlexServer:
        def __init__(self, url: str, token: str) -> None:
            self.url = url
            self.token = token
            self.friendlyName = "Test Plex"

    prompts: list[tuple[str, bool]] = []
    answers = iter(["http://localhost:32400/", "secret-token"])

    def fake_prompt(text: str, *, hide_input: bool = False) -> str:
        prompts.append((text, hide_input))
        return next(answers)

    monkeypatch.setattr("plex_music_enhancer.cli.typer.prompt", fake_prompt)
    monkeypatch.setattr("plex_music_enhancer.cli.PlexServer", FakePlexServer)
    monkeypatch.setattr(
        "plex_music_enhancer.cli._run_diagnostics",
        lambda: [DiagnosticCheck("Plex connection", True, "Connected successfully.")],
    )

    monkeypatch.chdir(tmp_path)
    Path(".env").write_text(
        "UNRELATED=value\nPLEX_ENHANCER_PLEX_URL=http://old\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["login"])

    assert result.exit_code == 0
    assert "Plex login saved successfully." in result.stdout
    assert "secret-token" not in result.stdout
    assert prompts == [("Plex server URL", False), ("Plex token", True)]
    assert Path(".env").read_text(encoding="utf-8") == (
        "UNRELATED=value\n"
        "PLEX_ENHANCER_PLEX_URL=http://localhost:32400\n"
        "PLEX_ENHANCER_PLEX_TOKEN=secret-token\n"
    )


def test_login_rejects_invalid_url(monkeypatch, tmp_path: Path) -> None:
    answers = iter(["not-a-url", "secret-token"])
    monkeypatch.setattr(
        "plex_music_enhancer.cli.typer.prompt",
        lambda text, hide_input=False: next(answers),
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["login"])

    assert result.exit_code == 1
    assert "Invalid Plex URL" in result.stdout
    assert "secret-token" not in result.stdout
    assert not Path(".env").exists()


def test_login_redacts_token_from_connection_errors(monkeypatch, tmp_path: Path) -> None:
    class FakePlexServer:
        def __init__(self, url: str, token: str) -> None:
            msg = f"Could not connect with token {token}"
            raise RuntimeError(msg)

    answers = iter(["http://localhost:32400", "secret-token"])
    monkeypatch.setattr(
        "plex_music_enhancer.cli.typer.prompt",
        lambda text, hide_input=False: next(answers),
    )
    monkeypatch.setattr("plex_music_enhancer.cli.PlexServer", FakePlexServer)

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["login"])

    assert result.exit_code == 1
    assert "Unable to connect to Plex" in result.stdout
    assert "REDACTED" in result.stdout
    assert "secret-token" not in result.stdout
    assert not Path(".env").exists()


def test_context_album_renders_and_saves_json(monkeypatch, tmp_path: Path) -> None:
    class FakePipeline:
        def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            return _album_context()

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_enrichment_pipeline",
        lambda: (FakePipeline(), SecretStr("secret-token")),
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["context", "album", "--artist", "Nina Simone", "--album", "Pastel Blues", "--save"],
    )

    export_path = Path("exports/context/Nina-Simone-Pastel-Blues.json")
    assert result.exit_code == 0
    assert "PLEX" in result.stdout
    assert "MUSICBRAINZ" in result.stdout
    assert "WIKIPEDIA" in result.stdout
    assert "PIPELINE STATUS" in result.stdout
    assert "READY FOR GENERATION" in result.stdout
    assert export_path.exists()
    assert '"ready_for_generation": true' in export_path.read_text(encoding="utf-8")


def test_match_command_renders_musicbrainz_match(monkeypatch) -> None:
    class FakeMusicBrainzMatcher:
        def match_album(self, *, artist_name: str, album_title: str) -> MatchResult:
            assert artist_name == "Nina Simone"
            assert album_title == "Pastel Blues"
            return _match_result()

    monkeypatch.setattr("plex_music_enhancer.cli.MusicBrainzMatcher", FakeMusicBrainzMatcher)

    result = runner.invoke(
        app,
        ["match", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "MusicBrainz Match" in result.stdout
    assert "Nina Simone" in result.stdout
    assert "Pastel Blues" in result.stdout
    assert "96" in result.stdout
    assert "artist-mbid" in result.stdout
    assert "release-group-mbid" in result.stdout
    assert "release-mbid" in result.stdout
    assert "Compilation" in result.stdout
    assert "Release year is missing" in result.stdout


def test_match_command_prints_json(monkeypatch) -> None:
    class FakeMusicBrainzMatcher:
        def match_album(self, *, artist_name: str, album_title: str) -> MatchResult:
            del artist_name, album_title
            return _match_result()

    monkeypatch.setattr("plex_music_enhancer.cli.MusicBrainzMatcher", FakeMusicBrainzMatcher)

    result = runner.invoke(
        app,
        ["match", "--artist", "Nina Simone", "--album", "Pastel Blues", "--json"],
    )

    assert result.exit_code == 0
    assert '"matched": true' in result.stdout
    assert '"release_group_mbid": "release-group-mbid"' in result.stdout
    assert '"score_breakdown": {' in result.stdout


def test_match_command_reports_errors(monkeypatch) -> None:
    class FakeMusicBrainzMatcher:
        def match_album(self, *, artist_name: str, album_title: str) -> MatchResult:
            del artist_name, album_title
            raise RuntimeError("MusicBrainz unavailable")

    monkeypatch.setattr("plex_music_enhancer.cli.MusicBrainzMatcher", FakeMusicBrainzMatcher)

    result = runner.invoke(
        app,
        ["match", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 1
    assert "Unable to match MusicBrainz metadata" in result.stdout
    assert "MusicBrainz unavailable" in result.stdout


def test_preview_command_renders_generated_summary(monkeypatch) -> None:
    factory_calls: list[tuple[str | None, str | None]] = []

    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            return _preview_document()

    def fake_create_preview_service(
        *,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> tuple[FakePreviewService, SecretStr]:
        factory_calls.append((provider_name, model))
        return FakePreviewService(), SecretStr("secret-token")

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        fake_create_preview_service,
    )

    result = runner.invoke(
        app,
        [
            "preview",
            "--artist",
            "Nina Simone",
            "--album",
            "Pastel Blues",
            "--provider",
            "openai",
            "--model",
            "gpt-5.5",
        ],
    )

    assert result.exit_code == 0
    assert factory_calls == [("openai", "gpt-5.5")]
    assert "AI" in result.stdout
    assert "GENERATED SUMMARY" in result.stdout
    assert "dummy" in result.stdout
    assert "dummy-v1" in result.stdout
    assert "Prompt version" in result.stdout
    assert "1.0" in result.stdout
    assert "deterministic test summary" in result.stdout
    assert "DummyProvider" in result.stdout
    assert "MUSICBRAINZ" not in result.stdout
    assert "PROMPT" not in result.stdout
    assert "Token usage" not in result.stdout
    assert "secret-token" not in result.stdout


def test_preview_artist_command_renders_generated_biography(monkeypatch) -> None:
    class FakePreviewService:
        def preview_artist(self, *, artist: str) -> ArtistPreviewDocument:
            assert artist == "Nina Simone"
            return _artist_preview_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(app, ["preview", "artist", "--artist", "Nina Simone"])

    assert result.exit_code == 0
    assert "GENERATED BIOGRAPHY" in result.stdout
    assert "AI" in result.stdout
    assert "dummy-v1" in result.stdout
    assert "MUSICBRAINZ" not in result.stdout
    assert "FACT VERIFICATION" not in result.stdout
    assert "STYLE ANALYSIS" not in result.stdout


def test_preview_artist_command_verbose_renders_diagnostics(monkeypatch) -> None:
    class FakePreviewService:
        def preview_artist(self, *, artist: str) -> ArtistPreviewDocument:
            assert artist == "Nina Simone"
            return _artist_preview_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "artist", "--artist", "Nina Simone", "--verbose"],
    )

    assert result.exit_code == 0
    assert "MUSICBRAINZ" in result.stdout
    assert "WIKIPEDIA" in result.stdout
    assert "DISCOGS" in result.stdout
    assert "LAST.FM" in result.stdout
    assert "FACT VERIFICATION" in result.stdout
    assert "STYLE ANALYSIS" in result.stdout
    assert "EDITORIAL QUALITY" in result.stdout
    assert "KNOWLEDGE BUILDER" in result.stdout
    assert "CONTEXT BUILDER" in result.stdout
    assert "Prompt variables" in result.stdout
    assert "Prompt budget" in result.stdout
    assert "Per-source contribution" in result.stdout
    assert "Token usage" in result.stdout
    assert "Career years" in result.stdout
    assert "1954-2003" in result.stdout
    assert "Discogs Context" in result.stdout
    assert "Wikipedia Extract" in result.stdout
    assert "Fact Count" in result.stdout
    assert "Plex source" in result.stdout
    assert "Discogs career profile" in result.stdout


def test_preview_artist_command_discogs_fallback_avoids_duplicate_content(monkeypatch) -> None:
    class FakePreviewService:
        def preview_artist(self, *, artist: str) -> ArtistPreviewDocument:
            assert artist == "Nina Simone"
            document = _artist_preview_document()
            variables = dict(document.resolved_prompt_variables)
            variables.pop("discogs_context", None)
            return document.model_copy(
                update={
                    "source_availability": {
                        **document.source_availability,
                        "discogs": "missing",
                    },
                    "resolved_prompt_variables": variables,
                }
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "artist", "--artist", "Nina Simone", "--verbose"],
    )

    assert result.exit_code == 0
    assert "No additional artist information available" in result.stdout


def test_preview_artist_command_saves_json(monkeypatch, tmp_path: Path) -> None:
    class FakePreviewService:
        def preview_artist(self, *, artist: str) -> ArtistPreviewDocument:
            assert artist == "Nina Simone"
            return _artist_preview_document()

    class FixedDateTime:
        @classmethod
        def now(cls) -> datetime:
            return datetime(2026, 7, 9, 12, 30, 45)

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )
    monkeypatch.setattr("plex_music_enhancer.cli.datetime", FixedDateTime)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["preview", "artist", "--artist", "Nina Simone", "--save"])

    export_path = Path("exports/previews/artists/Artist-Preview-Nina-Simone-20260709-123045.json")
    exported = export_path.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert export_path.exists()
    assert '"context": {' in exported
    assert '"rendered_prompt": {' in exported
    assert '"generated_summary": {' in exported
    assert '"style_diagnostics": {' in exported
    assert '"budget_diagnostics": {' in exported
    assert '"career_years": "1954-2003"' in exported
    assert '"source_availability": {' in exported
    assert '"editorial_recommendations": [' in exported
    assert '"resolved_prompt_variables": {' in exported
    assert '"knowledge_summary": {' in exported
    assert '"context_summary": {' in exported
    assert "Saved artist preview JSON" in result.stdout


def test_preview_command_uses_translate_prompt(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(
            self,
            *,
            artist: str,
            album: str,
            prompt_name: str = "album_summary",
        ) -> EnrichmentPreviewDocument:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            assert prompt_name == "album_translate"
            document = _preview_document()
            return document.model_copy(
                update={
                    "rendered_prompt": document.rendered_prompt.model_copy(
                        update={"name": "album_translate"}
                    )
                }
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues", "--translate", "--json"],
    )

    assert result.exit_code == 0
    assert '"name": "album_translate"' in result.stdout


def test_preview_command_uses_improve_prompt(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(
            self,
            *,
            artist: str,
            album: str,
            prompt_name: str = "album_summary",
        ) -> EnrichmentPreviewDocument:
            del artist, album
            assert prompt_name == "album_improve"
            document = _preview_document()
            return document.model_copy(
                update={
                    "rendered_prompt": document.rendered_prompt.model_copy(
                        update={"name": "album_improve"}
                    )
                }
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues", "--improve", "--json"],
    )

    assert result.exit_code == 0
    assert '"name": "album_improve"' in result.stdout


def test_preview_command_rejects_translate_and_improve_together() -> None:
    result = runner.invoke(
        app,
        [
            "preview",
            "--artist",
            "Nina Simone",
            "--album",
            "Pastel Blues",
            "--translate",
            "--improve",
        ],
    )

    assert result.exit_code == 1
    assert "Choose either --translate or --improve" in result.stdout


def test_preview_command_verbose_renders_diagnostics(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            del artist, album
            return _preview_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues", "--verbose"],
    )

    assert result.exit_code == 0
    assert "PLEX" in result.stdout
    assert "MUSICBRAINZ" in result.stdout
    assert "WIKIPEDIA" in result.stdout
    assert "FACT VERIFICATION" in result.stdout
    assert "PROMPT" in result.stdout
    assert "Current Plex summary" in result.stdout
    assert "Match confidence" in result.stdout
    assert "Article status" in result.stdout
    assert "Release Date" in result.stdout
    assert "Conflicts" in result.stdout
    assert "Prompt name" in result.stdout
    assert "Variables used" in result.stdout
    assert "Token usage" in result.stdout
    assert "Generation time" in result.stdout
    assert "release-group-mbid" in result.stdout


def test_preview_command_prints_json(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            del artist, album
            return _preview_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues", "--json"],
    )

    assert result.exit_code == 0
    assert '"context": {' in result.stdout
    assert '"rendered_prompt": {' in result.stdout
    assert '"generated_summary": {' in result.stdout
    assert '"provider": "dummy"' in result.stdout
    assert DUMMY_SUMMARY_TEXT in result.stdout


def test_preview_command_saves_json(monkeypatch, tmp_path: Path) -> None:
    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            del artist, album
            return _preview_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues", "--save"],
    )

    export_path = Path("exports/previews/Nina-Simone-Pastel-Blues.json")
    exported = export_path.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert export_path.exists()
    assert '"context": {' in exported
    assert '"rendered_prompt": {' in exported
    assert '"generated_summary": {' in exported
    assert "Saved preview JSON" in result.stdout


def test_preview_command_reports_errors(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            del artist, album
            raise PreviewError("No Plex album found with token secret-token")

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_preview_service",
        lambda provider_name=None, model=None: (FakePreviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 1
    assert "Unable to preview album enrichment" in result.stdout
    assert "REDACTED" in result.stdout
    assert "secret-token" not in result.stdout


def test_review_command_apply_uses_safe_apply_workflow(monkeypatch) -> None:
    class FakeReviewService:
        def create_review(self, *, artist: str, album: str) -> ReviewDocument:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            return _review_document(status="PASS")

        def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
            del document, edited_summary
            raise AssertionError("update_summary should not be called")

    class FakeApplyService:
        def apply_review(self, document: ReviewDocument) -> ApplyResult:
            assert document.quality.status == "PASS"
            return ApplyResult(
                status="SUCCESS",
                artist="Nina Simone",
                album="Pastel Blues",
                rating_key="42",
                backup_created=True,
                write_successful=True,
                verification_passed=True,
                audit_stored=True,
                backup_path="exports/backups/backup.json",
                audit_path="exports/audit/audit.json",
                message="Summary written and verified successfully.",
                review=document,
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_review_service",
        lambda provider_name=None, model=None: (FakeReviewService(), SecretStr("secret-token")),
    )
    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_apply_service_from_review",
        lambda review_service: (FakeApplyService(), SecretStr("secret-token")),
    )
    monkeypatch.setattr("plex_music_enhancer.cli._review_choice", lambda: "A")

    result = runner.invoke(
        app,
        ["review", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "CURRENT SUMMARY" in result.stdout
    assert "GENERATED SUMMARY" in result.stdout
    assert "UNIFIED DIFF" in result.stdout
    assert "PASS" in result.stdout
    assert "Plex Apply Workflow" in result.stdout
    assert "Write successful" in result.stdout


def test_review_album_command_prints_json(monkeypatch) -> None:
    class FakeReviewService:
        def create_review(self, *, artist: str, album: str) -> ReviewDocument:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            return _review_document(status="PASS")

        def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
            del document, edited_summary
            raise AssertionError("update_summary should not be called")

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_review_service",
        lambda provider_name=None, model=None: (FakeReviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["review", "album", "--artist", "Nina Simone", "--album", "Pastel Blues", "--json"],
    )

    assert result.exit_code == 0
    assert '"current_summary": "Aktuelle Plex-Zusammenfassung."' in result.stdout
    assert '"name": "album_summary"' in result.stdout


def test_review_help_lists_album_and_artist_commands() -> None:
    result = runner.invoke(app, ["review", "--help"])

    assert result.exit_code == 0
    assert "review album" in result.stdout
    assert "review artist" in result.stdout
    assert "album" in result.stdout
    assert "artist" in result.stdout
    assert "AI provider override for this review" not in result.stdout


def test_review_album_help_shows_album_options() -> None:
    result = runner.invoke(app, ["review", "album", "--help"])

    assert result.exit_code == 0
    assert "--artist" in result.stdout
    assert "--album" in result.stdout
    assert "--translate" in result.stdout
    assert "--improve" in result.stdout


def test_review_artist_command_prints_json(monkeypatch) -> None:
    class FakeReviewService:
        def create_artist_review(self, *, artist: str) -> ReviewDocument:
            assert artist == "Nina Simone"
            return _artist_review_document()

        def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
            del document, edited_summary
            raise AssertionError("update_summary should not be called")

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_review_service",
        lambda provider_name=None, model=None: (FakeReviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(app, ["review", "artist", "--artist", "Nina Simone", "--json"])

    assert result.exit_code == 0
    assert '"artist": "Nina Simone"' in result.stdout
    assert '"prompt_name": "artist_summary"' in result.stdout


def test_review_command_edit_then_skip(monkeypatch) -> None:
    class FakeReviewService:
        def __init__(self) -> None:
            self.edited_summary: str | None = None

        def create_review(self, *, artist: str, album: str) -> ReviewDocument:
            del artist, album
            return _review_document(status="WARNINGS")

        def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
            del document
            self.edited_summary = edited_summary
            return _review_document(status="PASS", proposed_summary=edited_summary)

    service = FakeReviewService()
    choices = iter(["E", "S"])
    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_review_service",
        lambda provider_name=None, model=None: (service, SecretStr("secret-token")),
    )
    monkeypatch.setattr("plex_music_enhancer.cli._review_choice", lambda: next(choices))
    monkeypatch.setattr(
        "plex_music_enhancer.cli._open_multiline_editor",
        lambda initial_text: _german_summary(),
    )

    result = runner.invoke(
        app,
        ["review", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert service.edited_summary == _german_summary()
    assert "WARNINGS" in result.stdout
    assert "PASS" in result.stdout
    assert "Skipped. No changes were made." in result.stdout


def test_review_command_blocks_apply_when_quality_failed(monkeypatch) -> None:
    choices = iter(["A", "Q"])

    class FakeReviewService:
        def create_review(self, *, artist: str, album: str) -> ReviewDocument:
            del artist, album
            return _review_document(status="FAILED")

        def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
            del document, edited_summary
            raise AssertionError("update_summary should not be called")

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_review_service",
        lambda provider_name=None, model=None: (FakeReviewService(), SecretStr("secret-token")),
    )
    monkeypatch.setattr("plex_music_enhancer.cli._review_choice", lambda: next(choices))

    result = runner.invoke(
        app,
        ["review", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "FAILED" in result.stdout
    assert "Generated summary must pass validation before Apply." in result.stdout
    assert "Quit. No changes were made." in result.stdout


def test_review_command_prints_json(monkeypatch) -> None:
    class FakeReviewService:
        def create_review(self, *, artist: str, album: str) -> ReviewDocument:
            del artist, album
            return _review_document(status="PASS")

        def update_summary(self, document: ReviewDocument, edited_summary: str) -> ReviewDocument:
            del document, edited_summary
            raise AssertionError("update_summary should not be called")

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_review_service",
        lambda provider_name=None, model=None: (FakeReviewService(), SecretStr("secret-token")),
    )

    result = runner.invoke(
        app,
        ["review", "--artist", "Nina Simone", "--album", "Pastel Blues", "--json"],
    )

    assert result.exit_code == 0
    assert '"current_summary": "Aktuelle Plex-Zusammenfassung."' in result.stdout
    assert '"quality": {' in result.stdout
    assert '"status": "PASS"' in result.stdout


def test_apply_command_renders_success(monkeypatch) -> None:
    class FakeApplyService:
        def apply_album_summary(self, *, artist: str, album: str) -> ApplyResult:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            return ApplyResult(
                status="SUCCESS",
                artist="Nina Simone",
                album="Pastel Blues",
                rating_key="42",
                backup_created=True,
                write_successful=True,
                verification_passed=True,
                audit_stored=True,
                backup_path="exports/backups/backup.json",
                audit_path="exports/audit/audit.json",
                message="Summary written and verified successfully.",
                review=_review_document(status="PASS"),
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_apply_service",
        lambda provider_name=None, model=None, force=False: (
            FakeApplyService(),
            SecretStr("secret-token"),
        ),
    )

    result = runner.invoke(
        app,
        ["apply", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "Backup created" in result.stdout
    assert "Write successful" in result.stdout
    assert "Verification passed" in result.stdout
    assert "Audit stored" in result.stdout
    assert "Audit log" in result.stdout


def test_apply_artist_command_renders_success(monkeypatch) -> None:
    class FakeApplyService:
        def apply_artist_summary(self, *, artist: str) -> ApplyResult:
            assert artist == "Nina Simone"
            return ApplyResult(
                status="SUCCESS",
                artist="Nina Simone",
                album="artist",
                rating_key="100",
                backup_created=True,
                write_successful=True,
                verification_passed=True,
                audit_stored=True,
                backup_path="exports/backups/backup.json",
                audit_path="exports/audit/audit.json",
                message="Summary written and verified successfully.",
                review=_artist_review_document(),
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_apply_service",
        lambda provider_name=None, model=None, force=False: (
            FakeApplyService(),
            SecretStr("secret-token"),
        ),
    )

    result = runner.invoke(app, ["apply", "artist", "--artist", "Nina Simone"])

    assert result.exit_code == 0
    assert "Backup created" in result.stdout
    assert "Write successful" in result.stdout
    assert "Verification passed" in result.stdout


def test_apply_command_exits_nonzero_on_failed_verification(monkeypatch) -> None:
    class FakeApplyService:
        def apply_album_summary(self, *, artist: str, album: str) -> ApplyResult:
            del artist, album
            return ApplyResult(
                status="FAILED",
                artist="Nina Simone",
                album="Pastel Blues",
                rating_key="42",
                backup_created=True,
                write_successful=True,
                verification_passed=False,
                audit_stored=True,
                backup_path="exports/backups/backup.json",
                audit_path="exports/audit/audit.json",
                message="Summary write completed, but verification failed after reload.",
                review=_review_document(status="PASS"),
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_apply_service",
        lambda provider_name=None, model=None, force=False: (
            FakeApplyService(),
            SecretStr("secret-token"),
        ),
    )

    result = runner.invoke(
        app,
        ["apply", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 1
    assert "FAILED" in result.stdout
    assert "verification failed" in result.stdout


def test_batch_review_command_renders_summary(monkeypatch) -> None:
    class FakeBatchReviewService:
        def review_albums(self, *, options: BatchReviewOptions, display, decide, edit):
            assert options.library == "Music"
            assert options.missing_only is True
            assert options.limit == 2
            assert options.resume is True
            assert display is not None
            assert decide is not None
            assert edit is not None
            return BatchReviewReport(
                processed=2,
                applied=1,
                skipped=1,
                failed=0,
                job_path="exports/jobs/batch-review-Music-missing.json",
            )

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_batch_review_service",
        lambda provider_name=None, model=None: (
            FakeBatchReviewService(),
            SecretStr("secret-token"),
        ),
    )

    result = runner.invoke(
        app,
        [
            "batch",
            "review",
            "--library",
            "Music",
            "--missing-only",
            "--limit",
            "2",
            "--resume",
        ],
    )

    assert result.exit_code == 0
    assert "Batch Review Summary" in result.stdout
    assert "Processed" in result.stdout
    assert "Applied" in result.stdout
    assert "Skipped" in result.stdout


def test_plan_command_renders_recommendations(monkeypatch) -> None:
    class FakePlanningSource:
        def scan_albums(self, *, library: str | None = None):
            assert library == "Music"
            return [
                BatchAlbumCandidate(
                    rating_key="42",
                    library="Music",
                    artist="Nina Simone",
                    album="Pastel Blues",
                    current_summary=None,
                )
            ]

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_planning_source",
        lambda: (FakePlanningSource(), SecretStr("secret-token")),
    )

    result = runner.invoke(app, ["plan", "--library", "Music"])

    assert result.exit_code == 0
    assert "Enrichment Plan" in result.stdout
    assert "Pastel Blues" in result.stdout
    assert "CREATE" in result.stdout


def test_plan_command_prints_json(monkeypatch) -> None:
    class FakePlanningSource:
        def scan_albums(self, *, library: str | None = None):
            del library
            return [
                BatchAlbumCandidate(
                    rating_key="43",
                    library="Music",
                    artist="Nina Simone",
                    album="Wild Is the Wind",
                    current_summary=(
                        "The album is an English summary with enough language markers "
                        "and a clear tone."
                    ),
                )
            ]

    monkeypatch.setattr(
        "plex_music_enhancer.cli._create_planning_source",
        lambda: (FakePlanningSource(), SecretStr("secret-token")),
    )

    result = runner.invoke(app, ["plan", "--json"])

    assert result.exit_code == 0
    assert '"action": "TRANSLATE"' in result.stdout
    assert '"language": "english"' in result.stdout


def test_capabilities_exports_json(monkeypatch, tmp_path: Path) -> None:
    class FakePlexCapabilityAnalyzer:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def analyze(self) -> PlexCapabilityAnalysis:
            return PlexCapabilityAnalysis(
                plex_server_version="1.40.0",
                platform="Linux",
                libraries=[
                    LibraryCapability(
                        library_id="42",
                        library_title="Music",
                        agent="tv.plex.agents.music",
                        scanner="Plex Music",
                    )
                ],
                api_capabilities=["update"],
                samples=[
                    ObjectCapabilityAnalysis(
                        object_type="artist",
                        rating_key="100",
                        title="Nina Simone",
                        available_attributes=["guid", "summary", "title"],
                        writable_attributes=["summary", "title"],
                        read_only_attributes=["guid"],
                        api_capabilities=["edit"],
                    )
                ],
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr(
        "plex_music_enhancer.cli.PlexCapabilityAnalyzer",
        FakePlexCapabilityAnalyzer,
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["capabilities"])

    assert result.exit_code == 0
    assert "Plex Metadata Capabilities" in result.stdout
    assert "1.40.0" in result.stdout
    assert "secret-token" not in result.stdout
    assert Path("exports/capabilities.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "plexServerVersion": "1.40.0",\n'
        '  "platform": "Linux",\n'
        '  "libraries": [\n'
        "    {\n"
        '      "libraryId": "42",\n'
        '      "libraryTitle": "Music",\n'
        '      "agent": "tv.plex.agents.music",\n'
        '      "scanner": "Plex Music"\n'
        "    }\n"
        "  ],\n"
        '  "apiCapabilities": [\n'
        '    "update"\n'
        "  ],\n"
        '  "samples": [\n'
        "    {\n"
        '      "objectType": "artist",\n'
        '      "ratingKey": "100",\n'
        '      "title": "Nina Simone",\n'
        '      "availableAttributes": [\n'
        '        "guid",\n'
        '        "summary",\n'
        '        "title"\n'
        "      ],\n"
        '      "writableAttributes": [\n'
        '        "summary",\n'
        '        "title"\n'
        "      ],\n"
        '      "readOnlyAttributes": [\n'
        '        "guid"\n'
        "      ],\n"
        '      "apiCapabilities": [\n'
        '        "edit"\n'
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_audit_exports_json(monkeypatch, tmp_path: Path) -> None:
    class FakePlexMetadataAuditor:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def audit(self) -> MetadataAuditReport:
            statistics = AuditStatistics(
                artist_total=1,
                artist_biography_present=1,
                artist_biography_missing=0,
                artist_biography_unknown=0,
                album_total=1,
                album_summary_present=1,
                album_summary_missing=0,
                album_summary_unknown=0,
                languages={"german": 0, "english": 1, "other": 0},
            )
            artist = ArtistAuditFinding(
                rating_key="100",
                title="Nina Simone",
                biography="present",
                language="english",
            )
            album = AlbumAuditFinding(
                rating_key="200",
                title="Pastel Blues",
                parent_artist="Nina Simone",
                summary="present",
                language="english",
            )
            library = LibraryAuditResult(
                library_id="42",
                library_title="Music",
                statistics=statistics,
                artists=[artist],
                albums=[album],
            )
            return MetadataAuditReport(
                statistics=statistics,
                libraries=[library],
                artists=[artist],
                albums=[album],
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr(
        "plex_music_enhancer.cli.PlexMetadataAuditor",
        FakePlexMetadataAuditor,
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["audit", "--export-json"])

    assert result.exit_code == 0
    assert "Library: Music" in result.stdout
    assert "Biography present" in result.stdout
    assert "Summary present" in result.stdout
    assert "secret-token" not in result.stdout
    assert Path("exports/audit.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "statistics": {\n'
        '    "artistTotal": 1,\n'
        '    "artistBiographyPresent": 1,\n'
        '    "artistBiographyMissing": 0,\n'
        '    "artistBiographyUnknown": 0,\n'
        '    "albumTotal": 1,\n'
        '    "albumSummaryPresent": 1,\n'
        '    "albumSummaryMissing": 0,\n'
        '    "albumSummaryUnknown": 0,\n'
        '    "languages": {\n'
        '      "german": 0,\n'
        '      "english": 1,\n'
        '      "other": 0\n'
        "    }\n"
        "  },\n"
        '  "libraries": [\n'
        "    {\n"
        '      "libraryId": "42",\n'
        '      "libraryTitle": "Music",\n'
        '      "statistics": {\n'
        '        "artistTotal": 1,\n'
        '        "artistBiographyPresent": 1,\n'
        '        "artistBiographyMissing": 0,\n'
        '        "artistBiographyUnknown": 0,\n'
        '        "albumTotal": 1,\n'
        '        "albumSummaryPresent": 1,\n'
        '        "albumSummaryMissing": 0,\n'
        '        "albumSummaryUnknown": 0,\n'
        '        "languages": {\n'
        '          "german": 0,\n'
        '          "english": 1,\n'
        '          "other": 0\n'
        "        }\n"
        "      },\n"
        '      "artists": [\n'
        "        {\n"
        '          "ratingKey": "100",\n'
        '          "title": "Nina Simone",\n'
        '          "biography": "present",\n'
        '          "language": "english"\n'
        "        }\n"
        "      ],\n"
        '      "albums": [\n'
        "        {\n"
        '          "ratingKey": "200",\n'
        '          "title": "Pastel Blues",\n'
        '          "parentArtist": "Nina Simone",\n'
        '          "summary": "present",\n'
        '          "language": "english"\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "artists": [\n'
        "    {\n"
        '      "ratingKey": "100",\n'
        '      "title": "Nina Simone",\n'
        '      "biography": "present",\n'
        '      "language": "english"\n'
        "    }\n"
        "  ],\n"
        '  "albums": [\n'
        "    {\n"
        '      "ratingKey": "200",\n'
        '      "title": "Pastel Blues",\n'
        '      "parentArtist": "Nina Simone",\n'
        '      "summary": "present",\n'
        '      "language": "english"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_metadata_album_renders_report(monkeypatch) -> None:
    class FakeMetadataEnrichmentPipeline:
        def enrich_album(
            self,
            *,
            artist: str,
            album: str,
            year: int | None = None,
        ) -> AlbumMetadataDocument:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            assert year is None
            return _metadata_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli.MetadataEnrichmentPipeline",
        FakeMetadataEnrichmentPipeline,
    )

    result = runner.invoke(
        app,
        ["metadata", "album", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "PLEX" in result.stdout
    assert "MUSICBRAINZ" in result.stdout
    assert "NORMALIZED METADATA" in result.stdout
    assert "release-group-mbid" in result.stdout
    assert "jazz" in result.stdout


def test_metadata_album_saves_json(monkeypatch, tmp_path: Path) -> None:
    class FakeMetadataEnrichmentPipeline:
        def enrich_album(
            self,
            *,
            artist: str,
            album: str,
            year: int | None = None,
        ) -> AlbumMetadataDocument:
            del artist, album, year
            return _metadata_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli.MetadataEnrichmentPipeline",
        FakeMetadataEnrichmentPipeline,
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["metadata", "album", "--artist", "Nina Simone", "--album", "Pastel Blues", "--save"],
    )

    assert result.exit_code == 0
    assert "Saved metadata JSON" in result.stdout
    assert Path("exports/metadata/Nina-Simone-Pastel-Blues.json").exists()


def test_metadata_album_prints_json(monkeypatch) -> None:
    class FakeMetadataEnrichmentPipeline:
        def enrich_album(
            self,
            *,
            artist: str,
            album: str,
            year: int | None = None,
        ) -> AlbumMetadataDocument:
            del artist, album, year
            return _metadata_document()

    monkeypatch.setattr(
        "plex_music_enhancer.cli.MetadataEnrichmentPipeline",
        FakeMetadataEnrichmentPipeline,
    )

    result = runner.invoke(
        app,
        ["metadata", "album", "--artist", "Nina Simone", "--album", "Pastel Blues", "--json"],
    )

    assert result.exit_code == 0
    assert '"release_group_mbid": "release-group-mbid"' in result.stdout
    assert '"sources": [' in result.stdout


def test_probe_write_reports_album_summary_dry_run(monkeypatch) -> None:
    class FakePlexWriteProbe:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def verify_album_summary(
            self,
            *,
            artist_name: str,
            album_title: str,
            execute: bool,
        ) -> AlbumWriteVerificationReport:
            assert artist_name == "Nina Simone"
            assert album_title == "Pastel Blues"
            assert execute is False
            return AlbumWriteVerificationReport(
                status="DRY_RUN",
                executed=False,
                library="Music",
                rating_key="200",
                title="Pastel Blues",
                artist=artist_name,
                album=album_title,
                current_summary="Album summary",
                available_edit_methods=["batchEdits", "editSummary", "saveEdits", "reload"],
                edit_summary_exists=True,
                original_summary_length=len("Album summary"),
                explanation="Dry run only. Plex was not modified.",
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr("plex_music_enhancer.cli.PlexWriteProbe", FakePlexWriteProbe)

    result = runner.invoke(
        app,
        ["probe", "write", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "Plex Write Verification" in result.stdout
    assert "DRY_RUN" in result.stdout
    assert "Pastel Blues" in result.stdout
    assert "Album summary" in result.stdout
    assert "editSummary" in result.stdout
    assert "saveEdits" in result.stdout
    assert "secret-token" not in result.stdout


def test_scan_displays_music_libraries(monkeypatch) -> None:
    class FakePlexMusicScanner:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def scan(self) -> MusicLibraryScanExport:
            return MusicLibraryScanExport(
                libraries=[
                    MusicLibraryStats(
                        library_id="42",
                        library_title="Music",
                        library_uuid="music-uuid",
                        scanner="Plex Music",
                        agent="tv.plex.agents.music",
                        artist_count=3,
                        album_count=7,
                        track_count=99,
                    )
                ]
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr("plex_music_enhancer.cli.PlexMusicScanner", FakePlexMusicScanner)

    result = runner.invoke(app, ["scan"])

    assert result.exit_code == 0
    assert "Plex Music Libraries" in result.stdout
    assert "Music" in result.stdout
    assert "99" in result.stdout
    assert "secret-token" not in result.stdout


def test_scan_exports_json(monkeypatch, tmp_path: Path) -> None:
    class FakePlexMusicScanner:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def scan(self) -> MusicLibraryScanExport:
            return MusicLibraryScanExport(
                libraries=[
                    MusicLibraryStats(
                        library_id="42",
                        library_title="Music",
                        library_uuid="music-uuid",
                        scanner="Plex Music",
                        agent="tv.plex.agents.music",
                        artist_count=3,
                        album_count=7,
                        track_count=99,
                    )
                ]
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr("plex_music_enhancer.cli.PlexMusicScanner", FakePlexMusicScanner)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["scan", "--export-json"])

    assert result.exit_code == 0
    assert "Exported music library scan" in result.stdout
    assert Path("exports/libraries.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "libraries": [\n'
        "    {\n"
        '      "library_id": "42",\n'
        '      "library_title": "Music",\n'
        '      "library_uuid": "music-uuid",\n'
        '      "scanner": "Plex Music",\n'
        '      "agent": "tv.plex.agents.music",\n'
        '      "artist_count": 3,\n'
        '      "album_count": 7,\n'
        '      "track_count": 99\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_scan_reports_missing_configuration(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["scan"])

    assert result.exit_code == 1
    assert "Missing Plex configuration" in result.stdout
    assert "plex-enhancer login" in result.stdout


def test_scan_reports_scanner_errors_without_token(monkeypatch) -> None:
    class FakePlexMusicScanner:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def scan(self) -> MusicLibraryScanExport:
            msg = "Connection failed with secret-token"
            raise PlexScannerError(msg)

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr("plex_music_enhancer.cli.PlexMusicScanner", FakePlexMusicScanner)

    result = runner.invoke(app, ["scan"])

    assert result.exit_code == 1
    assert "Unable to scan Plex libraries" in result.stdout
    assert "REDACTED" in result.stdout
    assert "secret-token" not in result.stdout


def test_scan_artists_exports_json(monkeypatch, tmp_path: Path) -> None:
    class FakePlexMusicScanner:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def scan_artists(self, progress_callback: object = None) -> ArtistScanExport:
            return ArtistScanExport(
                artists=[
                    ArtistScanItem(
                        rating_key="100",
                        title="Nina Simone",
                        guid="plex://artist/100",
                        summary="Artist summary",
                        genres=["Jazz", "Soul"],
                        country="United States",
                        artwork_url="/library/metadata/100/art",
                        thumb_url="/library/metadata/100/thumb",
                        album_count=2,
                    )
                ]
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr("plex_music_enhancer.cli.PlexMusicScanner", FakePlexMusicScanner)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["scan", "artists", "--export-json"])

    assert result.exit_code == 0
    assert "Plex Artists" in result.stdout
    assert "Nina Simone" in result.stdout
    assert Path("exports/artists.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "artists": [\n'
        "    {\n"
        '      "ratingKey": "100",\n'
        '      "title": "Nina Simone",\n'
        '      "guid": "plex://artist/100",\n'
        '      "summary": "Artist summary",\n'
        '      "genres": [\n'
        '        "Jazz",\n'
        '        "Soul"\n'
        "      ],\n"
        '      "country": "United States",\n'
        '      "artworkUrl": "/library/metadata/100/art",\n'
        '      "thumbUrl": "/library/metadata/100/thumb",\n'
        '      "albumCount": 2\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_scan_albums_exports_json(monkeypatch, tmp_path: Path) -> None:
    class FakePlexMusicScanner:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def scan_albums(self) -> AlbumScanExport:
            return AlbumScanExport(
                albums=[
                    AlbumScanItem(
                        rating_key="200",
                        title="Pastel Blues",
                        parent_artist="Nina Simone",
                        guid="plex://album/200",
                        year=1965,
                        originally_available_at="1965-10-01",
                        summary="Album summary",
                        genres=["Jazz"],
                        styles=["Vocal Jazz"],
                        moods=["Reflective"],
                        leaf_count=9,
                        thumb="/library/metadata/200/thumb",
                        artwork="/library/metadata/200/art",
                    )
                ]
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr("plex_music_enhancer.cli.PlexMusicScanner", FakePlexMusicScanner)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["scan", "albums", "--export-json"])

    assert result.exit_code == 0
    assert "Plex Albums" in result.stdout
    assert "Pastel Blues" in result.stdout
    assert Path("exports/albums.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "albums": [\n'
        "    {\n"
        '      "ratingKey": "200",\n'
        '      "title": "Pastel Blues",\n'
        '      "parentArtist": "Nina Simone",\n'
        '      "guid": "plex://album/200",\n'
        '      "year": 1965,\n'
        '      "originallyAvailableAt": "1965-10-01",\n'
        '      "summary": "Album summary",\n'
        '      "genres": [\n'
        '        "Jazz"\n'
        "      ],\n"
        '      "styles": [\n'
        '        "Vocal Jazz"\n'
        "      ],\n"
        '      "moods": [\n'
        '        "Reflective"\n'
        "      ],\n"
        '      "leafCount": 9,\n'
        '      "thumb": "/library/metadata/200/thumb",\n'
        '      "artwork": "/library/metadata/200/art"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_inspect_requires_exactly_one_lookup() -> None:
    result = runner.invoke(app, ["inspect", "artist"])

    assert result.exit_code == 1
    assert "Provide exactly one of --id or --name" in result.stdout


def test_inspect_artist_prints_json(monkeypatch) -> None:
    class FakePlexMetadataInspector:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def inspect(self, target: object, *, rating_key: str | None, name: str | None) -> object:
            return InspectedPlexObject(
                object_type="artist",
                rating_key=rating_key,
                guid="plex://artist/100",
                title="Nina Simone",
                attributes={"title": "Nina Simone", "summary": "Artist summary"},
                media=[{"audioCodec": "flac"}],
                images=[InspectImage(kind="thumb", value="/thumb")],
                children=[InspectChild(kind="album", rating_key="200", title="Pastel Blues")],
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr(
        "plex_music_enhancer.cli.PlexMetadataInspector",
        FakePlexMetadataInspector,
    )

    result = runner.invoke(app, ["inspect", "artist", "--id", "100", "--json"])

    assert result.exit_code == 0
    assert '"ratingKey": "100"' in result.stdout
    assert '"title": "Nina Simone"' in result.stdout
    assert "secret-token" not in result.stdout


def test_inspect_album_saves_json(monkeypatch, tmp_path: Path) -> None:
    class FakePlexMetadataInspector:
        def __init__(self, url: object, token: object) -> None:
            self.url = url
            self.token = token

        def inspect(self, target: object, *, rating_key: str | None, name: str | None) -> object:
            return InspectedPlexObject(
                object_type="album",
                rating_key="200",
                guid="plex://album/200",
                title=name,
                attributes={"title": name},
                media=[],
                images=[],
                children=[],
            )

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr(
        "plex_music_enhancer.cli.PlexMetadataInspector",
        FakePlexMetadataInspector,
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["inspect", "album", "--name", "Pastel Blues", "--save"])

    assert result.exit_code == 0
    assert "Saved inspection JSON" in result.stdout
    assert Path("exports/inspect/album-200.json").read_text(encoding="utf-8") == (
        "{\n"
        '  "objectType": "album",\n'
        '  "ratingKey": "200",\n'
        '  "guid": "plex://album/200",\n'
        '  "title": "Pastel Blues",\n'
        '  "attributes": {\n'
        '    "title": "Pastel Blues"\n'
        "  },\n"
        '  "media": [],\n'
        '  "images": [],\n'
        '  "children": []\n'
        "}\n"
    )
