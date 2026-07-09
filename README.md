# Plex Music Enhancer

Plex Music Enhancer is a production-grade, safe, review-first command line tool for improving Plex music metadata with AI-assisted, metadata-driven German album and artist descriptions.

It combines Plex library data, external music providers, a Knowledge Builder, GPT-5.5, an Editorial Style Engine, metadata verification, and a controlled Review & Apply workflow. The goal is simple: better Plex music descriptions without uncontrolled writes or invented facts.

## 📘 Documentation

- German User Manual (PDF) – `assets/pdf/Plex-Music-Enhancer-Handbuch.pdf`
- Getting Started – `docs/getting-started.md`
- Configuration – `docs/configuration.md`
- Command Reference – `docs/commands.md`
- AI & Editorial Pipeline – `docs/editorial.md`
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
plex-enhancer apply \
  --artist "Jennifer Rush" \
  --album "Credo" \
  --provider openai
```

Preview and Review are safe and do not modify Plex. Apply writes only after review validation, backup creation and verification.

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
make pdf
```

Install pre-commit hooks:

```bash
pre-commit install
```

Docker example:

```bash
docker compose run --rm plex-music-enhancer doctor
```

## Roadmap

Current:

- Stable metadata generation
- Editorial pipeline
- Review & Apply
- Knowledge Builder
- German handbook

Planned:

- Web UI
- Desktop application
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
