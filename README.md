# Plex Music Enhancer

Plex Music Enhancer is a production-minded CLI for auditing, planning, previewing,
reviewing, and safely applying German music metadata summaries to Plex music
libraries.

The beta is designed for real Plex libraries from hundreds to very large collections. It keeps
planning, preview, and review read-only, creates backups before writes, verifies
applied summaries after reload, and stores audit records for every apply run.

## Features

- Typer CLI with Rich reports and guided interactive review
- Plex library scanning, inspection, audit, and capability diagnostics
- Smart planner for `CREATE`, `TRANSLATE`, `IMPROVE`, `REVIEW`, and `SKIP`
- MusicBrainz and Wikipedia metadata collection with local caching
- Prompt engine with album create, translate, and improve templates
- AI abstraction with Dummy and OpenAI providers
- Safe apply workflow with backup, write, reload verification, and audit JSON
- Batch and full-library review sessions with resume support
- Performance diagnostics, incremental processing state, and scalable provider scheduling
- Ruff, Black, Pytest, pre-commit, GitHub Actions, Docker, and Compose

## Requirements

- Python 3.12+
- Plex server URL and token
- Optional OpenAI API key when `ai.provider=openai`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev,ai,metadata]"
```

## Configuration

Interactive setup:

```bash
plex-enhancer login
```

Environment variables:

```bash
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=your-plex-token
PLEX_ENHANCER_AI__PROVIDER=dummy
```

OpenAI preview:

```bash
PLEX_ENHANCER_AI__PROVIDER=openai
PLEX_ENHANCER_AI__MODEL=gpt-5.5
OPENAI_API_KEY=sk-...
```

Optional metadata providers:

```bash
PLEX_ENHANCER_DISCOGS__TOKEN=discogs-token
PLEX_ENHANCER_LASTFM__API_KEY=lastfm-key
```

Performance settings:

```bash
PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS=4
PLEX_ENHANCER_PERFORMANCE__INCREMENTAL_MODE=true
PLEX_ENHANCER_PERFORMANCE__DATABASE_LOCATION=~/.plex-enhancer/processing.sqlite3
```

See [Configuration](docs/configuration.md) for the complete settings reference.

## Supported Providers

- Plex: source library metadata and write target
- MusicBrainz: authoritative artist and album identity, dates, tags and structured metadata
- Wikipedia: encyclopedic summaries and contextual background
- Discogs: optional credits, labels, catalog and production information
- Last.fm: optional biography, community tags and listening context
- OpenAI: optional production AI generation provider
- Dummy: deterministic local AI provider for tests and dry runs

## Safe First Run

```bash
plex-enhancer doctor
plex-enhancer scan --export-json
plex-enhancer audit --export-json
plex-enhancer benchmark --library "Music"
plex-enhancer library plan --library "Music"
```

These commands do not modify Plex.

## Caching and Verification

Provider results are cached locally under `~/.plex-enhancer/cache/`. Cache entries include source,
schema and timing metadata so stale data can be refreshed safely. The verification engine compares
facts across collected providers and passes confidence information into editorial and QA stages.

## Editorial and Quality Engines

The editorial layer prepares structured writing guidance from verified facts. The German style
engine and Editorial QA engine evaluate generated text for readability, repetition, formatting,
metadata coverage and factual confidence. QA is deterministic and does not call AI.

## Common Workflows

Preview one album without writing:

```bash
plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues"
plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues" --translate
plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues" --improve
```

Review and approve interactively:

```bash
plex-enhancer review --artist "Nina Simone" --album "Pastel Blues"
```

Apply one approved generated summary with backup and verification:

```bash
plex-enhancer apply --artist "Nina Simone" --album "Pastel Blues"
```

Process a full library:

```bash
plex-enhancer library plan --library "Music"
plex-enhancer library review --library "Music"
plex-enhancer library apply --library "Music"
plex-enhancer library report --library "Music" --export-json
```

## Safety Model

Read-only commands:

- `doctor`
- `scan`
- `audit`
- `plan`
- `capabilities`
- `match`
- `metadata`
- `context`
- `preview`
- `batch review` until the user chooses Apply
- `library plan`
- `library review`
- `library resume`
- `library report`

Write commands:

- `apply`
- `review` only when Apply is chosen
- `batch review` only when Apply is chosen
- `library apply`
- `probe write --execute`, which performs a reversible verification write

Before normal apply writes, the app stores a backup under `exports/backups/`,
reloads the Plex object, verifies the expected summary, and writes an audit
record under `exports/audit/`.

## Documentation

- [Architecture overview](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [OpenAI setup](docs/openai.md)
- [Prompt system](docs/prompts.md)
- [Content quality](docs/content-quality.md)
- [Editorial engine](docs/editorial.md)
- [Planner](docs/planner.md)
- [Verification](docs/verification.md)
- [Quality engine](docs/quality.md)
- [Review workflow](docs/review.md)
- [Apply workflow](docs/apply.md)
- [Batch workflow](docs/batch.md)
- [Library workflow](docs/library-workflow.md)
- [Performance and scalability](docs/performance.md)
- [Developer guide](docs/developer.md)
- [Release checklist](RELEASE.md)
- [Changelog](CHANGELOG.md)

## Troubleshooting

- Run `plex-enhancer doctor` first. It checks Plex configuration, AI provider selection, cache status
  and prompt availability.
- If preview uses `DummyProvider`, check `PLEX_ENHANCER_AI__PROVIDER` and `OPENAI_API_KEY`.
- If provider metadata is missing, verify optional Discogs or Last.fm credentials and cache age.
- If apply is blocked, inspect review quality and QA warnings, then edit or use a lower configured
  quality threshold only when appropriate.
- If large library runs are slow, run `plex-enhancer benchmark --library "Music"` and review
  [Performance and scalability](docs/performance.md).

## Development

Install development dependencies:

```bash
make install
```

Run tests:

```bash
make test
```

Run linting and formatting checks:

```bash
make lint
make format
```

Install pre-commit hooks:

```bash
pre-commit install
```

## Docker

```bash
docker compose run --rm plex-music-enhancer doctor
```

## License

This project is licensed under the MIT License.
