"""CLI tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from plex_music_enhancer.cli import DiagnosticCheck, app
from plex_music_enhancer.constants import __version__
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
from plex_music_enhancer.services import (
    AlbumMetadata,
    AlbumMetadataDocument,
    EnrichmentPreviewDocument,
    MatchResult,
    MusicBrainzEnrichmentMetadata,
    PlexAlbumMetadata,
    PlexAlbumPreview,
    PreviewError,
    ProviderPreviewStatus,
)

runner = CliRunner()


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
        plex=PlexAlbumPreview(
            title="Pastel Blues",
            artist="Nina Simone",
            current_summary="Current Plex summary",
            year=1965,
            genres=["Jazz", "Soul"],
        ),
        provider=ProviderPreviewStatus(
            name="MusicBrainz",
            reachable=True,
            match_found=True,
            metadata_available=True,
        ),
        metadata=_metadata_document(),
        ready_for_ai_enrichment=True,
    )


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "Python version" in result.stdout
    assert "Configuration" in result.stdout
    assert "Plex connection" in result.stdout


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


def test_preview_command_renders_readiness(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            assert artist == "Nina Simone"
            assert album == "Pastel Blues"
            return _preview_document()

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr(
        "plex_music_enhancer.cli.EnrichmentPreviewService",
        lambda url, token: FakePreviewService(),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 0
    assert "Plex Album" in result.stdout
    assert "Pastel Blues" in result.stdout
    assert "Current Plex summary" in result.stdout
    assert "Provider Checks" in result.stdout
    assert "Provider reachable" in result.stdout
    assert "Match found" in result.stdout
    assert "Metadata available" in result.stdout
    assert "artist-mbid" in result.stdout
    assert "release-group-mbid" in result.stdout
    assert "This album is ready for AI enrichment." in result.stdout
    assert "secret-token" not in result.stdout


def test_preview_command_reports_errors(monkeypatch) -> None:
    class FakePreviewService:
        def preview_album(self, *, artist: str, album: str) -> EnrichmentPreviewDocument:
            del artist, album
            raise PreviewError("No Plex album found with token secret-token")

    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")
    monkeypatch.setattr(
        "plex_music_enhancer.cli.EnrichmentPreviewService",
        lambda url, token: FakePreviewService(),
    )

    result = runner.invoke(
        app,
        ["preview", "--artist", "Nina Simone", "--album", "Pastel Blues"],
    )

    assert result.exit_code == 1
    assert "Unable to preview album enrichment" in result.stdout
    assert "REDACTED" in result.stdout
    assert "secret-token" not in result.stdout


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
