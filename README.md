# Plex Music Enhancer

Plex Music Enhancer is a Python CLI foundation for future Plex music metadata
workflows. The first milestone intentionally focuses on production-ready project
structure, configuration, diagnostics, and delivery tooling. Metadata enrichment
is not implemented yet.

## Features

- Python 3.12+ package using a `src/` layout
- Typer CLI with Rich diagnostics
- Pydantic Settings configuration from environment variables or `.env`
- Minimal Plex connectivity check
- Ruff, Black, Pytest, pre-commit, GitHub Actions
- Dockerfile and Docker Compose setup

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

Copy the example environment file and add your Plex details:

```bash
cp .env.example .env
```

Required settings:

```bash
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=your-plex-token
```

## CLI

Print the installed version:

```bash
plex-enhancer version
```

Run diagnostics:

```bash
plex-enhancer doctor
```

The doctor command checks the Python version, validates configuration, verifies
the Plex URL setting, attempts a Plex connection, and prints a Rich diagnostics
table.

## Development

Run the test suite:

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

Build and run the diagnostics command:

```bash
docker compose run --rm plex-music-enhancer
```

## License

This project is licensed under the MIT License.
