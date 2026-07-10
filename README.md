# Plex Music Enhancer

[![CI](https://github.com/amylasehai0z/plex-music-enhancer/actions/workflows/ci.yml/badge.svg)](https://github.com/amylasehai0z/plex-music-enhancer/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/container-GHCR-blue?logo=github)](https://github.com/amylasehai0z/plex-music-enhancer/pkgs/container/plex-music-enhancer)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Plex Music Enhancer is a production-grade, safe, review-first command line tool for improving Plex music metadata with AI-assisted, metadata-driven German album and artist descriptions.

It combines Plex library data, external music providers, a Knowledge Builder, GPT-5.5, an Editorial Style Engine, metadata verification, and a controlled Review & Apply workflow. The goal is simple: better Plex music descriptions without uncontrolled writes or invented facts.

## 📘 Documentation

- German User Manual (PDF) – `assets/pdf/Plex-Music-Enhancer-Handbuch.pdf`
- Getting Started – `docs/getting-started.md`
- Configuration – `docs/configuration.md`
- Command Reference – `docs/commands.md`
- AI & Editorial Pipeline – `docs/editorial.md`
- Backend API – `docs/backend-api.md`
- Web Interface – `docs/web-ui.md`
- Docker, Portainer & Synology – `docs/docker.md`
- Web Architecture – `docs/web-architecture.md`
- Developer Mode – `docs/developer-mode.md`
- Troubleshooting – `docs/troubleshooting.md`
- Developer Guide – `docs/developer.md`
- Changelog – `CHANGELOG.md`

## Highlights

- GPT-5.5 generation for German music descriptions
- Editorial Style Engine and Editorial Quality Engine
- Metadata Verification Engine
- Knowledge Builder and Context Builder
- MusicBrainz, Wikipedia, Discogs and Last.fm metadata
- Safe Apply workflow with automatic backup, reload verification and audit trail
- Provider cache for faster repeated runs
- Batch processing and full library workflow
- Docker support
- GitHub Actions
- Extensive automated test suite

## Requirements

- Python 3.12+
- Plex Media Server
- Plex token
- OpenAI API key for GPT-5.5 generation
- Optional API credentials for Discogs and Last.fm

## Installation

```bash
python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install ".[dev,ai,metadata]"

plex-enhancer login
plex-enhancer doctor
```

On Windows, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Configuration

Plex credentials can be configured interactively:

```bash
plex-enhancer login
```

Example environment configuration:

```bash
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=your-plex-token

PLEX_ENHANCER_AI__PROVIDER=openai
PLEX_ENHANCER_AI__MODEL=gpt-5.5
PLEX_ENHANCER_AI__MAX_PROMPT_CHARACTERS=20000
OPENAI_API_KEY=sk-...
```

Optional provider configuration:

```bash
PLEX_ENHANCER_DISCOGS__TOKEN=...
PLEX_ENHANCER_LASTFM__API_KEY=...
```

## Workflow

The standard workflow is Preview, Review, Apply.

```bash
plex-enhancer preview \
  --artist "Jennifer Rush" \
  --album "Credo" \
  --provider openai
```

Artist biographies use the same safe preview path:

```bash
plex-enhancer preview artist \
  --artist "Jennifer Rush" \
  --provider openai \
  --verbose
```

Verbose artist preview highlights source availability, verified facts, resolved prompt context,
career years, Discogs-only additions, prompt budget diagnostics, style analysis and editorial
recommendations. Saved artist previews include the same diagnostics as JSON under
`exports/previews/artists/`.

Large artist or album contexts are reduced automatically before generation. The Prompt Budget
Manager preserves verified structured metadata first, trims long provider biographies at natural
boundaries and reports source contributions in verbose preview output.

```bash
plex-enhancer review album \
  --artist "Jennifer Rush" \
  --album "Credo" \
  --provider openai
```

```bash
plex-enhancer review artist \
  --artist "Jennifer Rush" \
  --provider openai
```

```bash
plex-enhancer apply \
  --artist "Jennifer Rush" \
  --album "Credo" \
  --provider openai
```

Preview and Review are safe and do not modify Plex. Apply writes only after review validation, backup creation and verification.

Temporary developer diagnostics are written during AI review runs:

- `/tmp/openai_prompt.txt` contains the exact prompt sent to OpenAI.
- `/tmp/openai_prompt_meta.json` contains prompt length, target, provider, model, word limits and
  budget metadata.
- `/tmp/plex_review.log` contains the rendered review sections, QA summary, token usage when
  reported, generation time, command context, prompt budget, used sources, prompt decisions,
  prompt quality, coverage-vs-evidence analysis and prompt utilization.

The debug log also explains adaptive prompt trimming. `PROMPT DECISIONS` lists included, removed and
trimmed evidence, while `PROMPT QUALITY` reports redundancy, source balance, historical coverage and
the prompt efficiency score. `EVIDENCE RANKING` shows which source blocks carried the strongest
editorial value, `EVIDENCE COVERAGE` compares high-value evidence with the generated biography, and
`EDITORIAL BALANCE` checks whether opening, career, major works, later development and legacy are
represented. Prompt compression removes repeated claims and keeps historically useful evidence ahead
of administrative metadata.

Developer Mode exposes those files through structured commands without running
AI again:

```bash
plex-enhancer debug prompt --stats
plex-enhancer debug meta
plex-enhancer debug review --summary
plex-enhancer debug explain
plex-enhancer debug doctor
```

## Pipeline

```text
Plex
↓
Metadata Collection
↓
MusicBrainz
↓
Wikipedia
↓
Discogs
↓
Last.fm
↓
Context Builder
↓
Knowledge Builder
↓
Editorial Style Engine
↓
GPT-5.5
↓
Editorial Quality Engine
↓
Verification Engine
↓
Review
↓
Apply
```

Generation is grounded in collected and verified metadata. The prompt pipeline is designed to prefer supported facts, avoid unsupported claims, and keep the user in control before Plex is changed.

## Safety Model

Read-only commands include:

- `doctor`
- `scan`
- `audit`
- `plan`
- `match`
- `metadata`
- `context`
- `preview`
- `review` until Apply is confirmed
- `library plan`
- `library review`
- `cache stats`
- `cache list`

Write-capable commands include:

- `apply`
- `review` after explicit Apply confirmation
- `library apply`
- `cache clear`

Before writing metadata to Plex, the Apply workflow creates a backup, writes the approved summary, reloads the Plex object, verifies the stored text and records an audit trail.

## German User Manual

The complete German user manual is available as a PDF:

```text
assets/pdf/Plex-Music-Enhancer-Handbuch.pdf
```

The handbook covers:

- Installation
- Configuration
- CLI reference
- Workflows
- Editorial Engine
- Providers
- Cache
- Performance
- Troubleshooting
- FAQ
- Glossary

The handbook is regenerated with every `make pdf` run and is attached to GitHub Releases under the same stable filename:

```bash
make pdf
```

The PDF build uses `assets/logo/plex-music-enhancer-logo.pdf` for LaTeX output. SVG logo assets are used for GitHub, README and web contexts.

## Development

```bash
make install
make format
make lint
make test
make web-test
make web-build
make pdf
```

Install pre-commit hooks:

```bash
pre-commit install
```

Docker example:

```bash
docker compose up -d
```

The container image is published to GitHub Container Registry:

```text
ghcr.io/amylasehai0z/plex-music-enhancer
```

Images are built for `linux/amd64` and `linux/arm64`, so the same image can run
on Intel/AMD hosts and ARM-based Synology systems.
Published images include OCI metadata, SBOM and provenance attestations.

Common tags:

| Tag | Purpose |
| --- | --- |
| `latest` | current default branch image |
| `main` | current `main` branch image |
| `develop` | optional integration branch image |
| `v1.0.0` | immutable release image |

The container listens on port `8080`; the default compose setup maps host port
`1008` to container port `8080`. Persistent folders are mounted at `/config`,
`/cache`, `/logs` and optionally `/music`.

Local Docker validation:

```bash
docker build -t plex-music-enhancer:local .
docker compose config
docker run --rm plex-music-enhancer:local plex-enhancer --help
docker run --rm plex-music-enhancer:local plex-enhancer serve --help
docker compose up -d
until curl --fail --silent http://127.0.0.1:1008/api/v1/system/health; do sleep 1; done
docker compose down
```

Portainer is the recommended Docker management interface. Import
`docker-compose.yml` as a Portainer Stack or create a single container from the
GHCR image, then configure volumes, environment variables, port mapping and the
healthcheck in Portainer.

Recommended deployment workflow:

```text
Git Push
↓
GitHub Actions
↓
Tests
↓
Docker Image Build
↓
Push to GHCR
↓
Portainer
↓
Pull the new image
↓
Restart the container
```

Image updates are intentionally manual. The user decides in Portainer when a new
image is pulled, applied or rolled back to an older GHCR tag.

## Release Management

A version tag is enough to create a complete release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The tag triggers GitHub Actions:

```text
Git Tag
↓
GitHub Actions
↓
Tests
↓
Python Wheel
↓
Source Distribution
↓
Docker Smoke Tests
↓
Multi-Arch Docker Image
↓
GHCR
↓
GitHub Release
↓
Release Artifacts
```

GitHub Releases are created or updated automatically for `v*.*.*` tags. Release
assets include the Python wheel, source distribution, build report, Docker
analysis and release readiness report. GHCR receives the matching release image
and SemVer tags.

## Web Interface and REST API

The optional FastAPI backend serves the React web interface and the REST API from one process:

```bash
python -m pip install ".[web]"
plex-enhancer serve
```

The default URL is `http://127.0.0.1:8080/`. OpenAPI documentation is available at:

- Swagger UI: `http://127.0.0.1:8080/api/v1/docs`
- ReDoc: `http://127.0.0.1:8080/api/v1/redoc`
- OpenAPI JSON: `http://127.0.0.1:8080/api/v1/openapi.json`

For container deployments, a host port such as `1008` can still be mapped to
container port `8080`.

The web UI is built with React, TypeScript, Vite, React Router, TanStack Query,
Mantine and Monaco. It contains no business logic; every workflow calls the
existing REST API, which reuses the same preview, review, apply, configuration
and debug services as the CLI.

The Review IDE shows the current Plex text, the generated text, a Monaco diff,
QA, editorial validation, verification, prompt budget, coverage and explainability
panels. Developer Mode reveals additional Prompt Decisions, Evidence Ranking,
token usage, timing and review-log diagnostics without changing backend behavior.
Artists and albums can be searched, filtered, sorted and selected in the GUI.
The Activity Panel, Live Log and REST Explorer expose existing backend status and
debug data for day-to-day work without replacing the CLI.

## Roadmap

Current:

- Stable metadata generation
- Editorial pipeline
- Review & Apply
- Knowledge Builder
- German handbook
- Internal backend API preparation
- FastAPI REST backend
- React web interface

Planned:

- Phase 6: Desktop application
- Additional providers
- Multi-language generation
- Extended verification
- Plugin ecosystem

## Contributing

Contributions, bug reports and documentation improvements are welcome. See `CONTRIBUTING.md` before opening pull requests.

## License

MIT License. See `LICENSE`.

## Acknowledgements

Plex Music Enhancer builds on Plex, MusicBrainz, Wikipedia, Discogs, Last.fm, OpenAI, Typer, Rich, Pydantic and httpx.
