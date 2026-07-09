# Changelog

All notable changes to Plex Music Enhancer are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses semantic versioning.

## [1.0.0] - 2026-07-09

### Added

- Stable public CLI for scanning, auditing, planning, previewing, reviewing and applying Plex music metadata.
- Multi-source enrichment from Plex, MusicBrainz, Wikipedia, Discogs and Last.fm.
- Fact verification, editorial composition, German style analysis and deterministic QA reporting.
- Safe apply workflow with backups, reload verification and audit records.
- Batch and full-library workflows with resumable progress.
- Performance infrastructure for provider scheduling, retries, metrics, cache invalidation and SQLite processing state.
- `plex-enhancer benchmark` for read-only performance diagnostics.
- Release, architecture, configuration, developer and performance documentation.

### Changed

- Project metadata now reflects production/stable release readiness.
- Documentation now matches the implemented review and apply workflows.

### Security

- Secrets remain redacted from CLI error messages and diagnostic output.

## [0.9.0] - 2026-07-09

### Added

- Provider scheduler with bounded concurrency for independent metadata sources.
- SQLite processing database and incremental processing fingerprints.
- Unified retry helper, metrics collector, throughput tracker and benchmark reporting.
- Cache schema metadata and partial invalidation support.

## [0.8.0] - 2026-07-09

### Added

- Editorial Quality Assurance engine for generated German album and artist descriptions.
- Review and apply integration for QA reports and configurable quality thresholds.

## [0.7.0] - 2026-07-09

### Added

- Discogs and Last.fm optional provider integrations.
- Expanded enrichment context for credits, production details, community tags and biographies.

## [0.6.0] - 2026-07-09

### Added

- Artist biography workflows for preview, review and apply.
- Richer album context, knowledge graph support and editorial track intelligence.

## [0.5.0] - 2026-07-09

### Added

- OpenAI provider integration and German preview workflow.
- Prompt engine with Markdown templates and rendered prompt models.

## [0.4.0] - 2026-07-09

### Added

- Review, apply, batch and library workflows with backups and audit records.
- Translation and improvement workflows for existing Plex summaries.

## [0.3.0] - 2026-07-09

### Added

- MusicBrainz matching, metadata enrichment pipeline and public match command.
- Wikipedia provider and enrichment preview.

## [0.2.0] - 2026-07-09

### Added

- Plex scanning, inspection, audit, capability analysis and write probing.
- JSON exports for scanner, audit and diagnostics.

## [0.1.0] - 2026-07-09

### Added

- Initial Python 3.12 src-layout project foundation.
- Typer CLI, Rich output, Pydantic Settings, Ruff, Black, Pytest, GitHub Actions, Docker, MIT license and pre-commit.
