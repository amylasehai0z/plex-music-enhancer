# Plex Music Enhancer

Plex Music Enhancer is a production-minded CLI for auditing, planning, previewing,
reviewing, and safely applying German music metadata summaries to Plex music
libraries.

The beta is designed for real Plex libraries with hundreds of albums. It keeps
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

## Safe First Run

```bash
plex-enhancer doctor
plex-enhancer scan --export-json
plex-enhancer audit --export-json
plex-enhancer library plan --library "Music"
```

These commands do not modify Plex.

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
- `review`
- `batch review` until the user chooses Apply
- `library plan`
- `library review`
- `library resume`
- `library report`

Write commands:

- `apply`
- `batch review` only when Apply is chosen
- `library apply`
- `probe write --execute`, which performs a reversible verification write

Before normal apply writes, the app stores a backup under `exports/backups/`,
reloads the Plex object, verifies the expected summary, and writes an audit
record under `exports/audit/`.

## Documentation

- [OpenAI setup](docs/openai.md)
- [Prompt system](docs/prompts.md)
- [Content quality](docs/content-quality.md)
- [Planner](docs/planner.md)
- [Review workflow](docs/review.md)
- [Apply workflow](docs/apply.md)
- [Batch workflow](docs/batch.md)
- [Library workflow](docs/library-workflow.md)

## Development

Run tests:

```bash
pytest
```

Run linting and formatting checks:

```bash
ruff check .
black --check .
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
