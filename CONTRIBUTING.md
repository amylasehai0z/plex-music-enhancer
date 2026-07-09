# Contributing

Thank you for helping improve Plex Music Enhancer.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
make install
pre-commit install
```

## Before Opening a Pull Request

Run:

```bash
make validate
```

For provider or network-adjacent changes, tests must use mocks. Unit tests must not call real
MusicBrainz, Wikipedia, Discogs, Last.fm, OpenAI or Plex services.

## Safety Rules

- Do not write to Plex outside the explicit apply and probe execution paths.
- Preserve backups and audit records for write workflows.
- Do not print Plex tokens or AI/provider API keys.
- Keep provider failures isolated and recoverable.
- Keep generated metadata fact-bound to collected context.

## Code Style

- Python 3.12+.
- Fully typed public models and services.
- Pydantic models for serializable data.
- Ruff and Black for style.
- Focused tests for every behavior change.

## Documentation

Update documentation when changing CLI behavior, configuration, prompts, provider behavior,
quality checks, apply safety or release operations.
