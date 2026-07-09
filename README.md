# Plex Music Enhancer

Plex Music Enhancer is a production-grade command line application for auditing, planning, generating, reviewing and safely applying high-quality German music metadata to Plex music libraries.

It combines authoritative metadata providers with GPT-5.5 and a deterministic editorial pipeline to produce fact-based, natural sounding album descriptions while keeping the user in complete control before anything is written back to Plex.

---

## Quick Links

- 📘 **German User Manual (PDF)** – `assets/pdf/Plex-Music-Enhancer-Handbuch-v1.0.pdf`
- 🚀 Getting Started – `docs/getting-started.md`
- ⚙️ Configuration – `docs/configuration.md`
- 🤖 AI & Editorial Pipeline – `docs/editorial.md`
- 📚 Command Reference – `docs/commands.md`
- 🔍 Troubleshooting – `docs/troubleshooting.md`
- 📋 Changelog – `CHANGELOG.md`

---

# Features

- Modern Typer CLI with Rich user interface
- Read-only planning before any modification
- Interactive review workflow
- Safe Apply process including backup and verification
- GPT-5.5 powered German editorial generation
- Editorial Style Engine
- Editorial Quality Engine
- Metadata verification engine
- MusicBrainz integration
- Wikipedia integration
- Discogs integration
- Last.fm integration
- Provider cache
- Incremental processing
- Batch processing
- Full library workflow
- Complete audit trail
- Export and reporting
- Docker support
- GitHub Actions
- Extensive automated test suite

---

# Requirements

- Python 3.12+
- Plex Media Server
- Plex Token
- OpenAI API Key (optional)
- Internet connection for metadata providers

---

# Installation

Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev,ai,metadata]"
```

Run the interactive configuration

```bash
plex-enhancer login
```

Verify your installation

```bash
plex-enhancer doctor
```

---

# Configuration

Example environment variables

```bash
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=your-token

PLEX_ENHANCER_AI__PROVIDER=openai
PLEX_ENHANCER_AI__MODEL=gpt-5.5

OPENAI_API_KEY=sk-...
```

Optional metadata providers

```bash
PLEX_ENHANCER_DISCOGS__TOKEN=...
PLEX_ENHANCER_LASTFM__API_KEY=...
```

Performance options

```bash
PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS=4
PLEX_ENHANCER_PERFORMANCE__INCREMENTAL_MODE=true
```

---

# Supported Metadata Providers

| Provider | Purpose |
|-----------|---------|
| Plex | Read existing metadata and write approved summaries |
| MusicBrainz | Artist and release identification |
| Wikipedia | Encyclopedic context |
| Discogs | Producers, labels, credits and release information |
| Last.fm | Artist biographies and community information |
| OpenAI | AI text generation |
| Dummy | Local testing provider |

---

# Safe First Run

```bash
plex-enhancer doctor

plex-enhancer scan --export-json

plex-enhancer audit --export-json

plex-enhancer library plan --library "Music"
```

These commands never modify Plex.

---

# Typical Workflow

Preview metadata

```bash
plex-enhancer preview \
    --artist "Jennifer Rush" \
    --album "Credo"
```

Review

```bash
plex-enhancer review \
    --artist "Jennifer Rush" \
    --album "Credo"
```

Apply

```bash
plex-enhancer apply \
    --artist "Jennifer Rush" \
    --album "Credo"
```

---

# AI Editorial Pipeline

```
Plex
    │
    ▼
Metadata Collection
    │
    ▼
MusicBrainz
    │
    ▼
Wikipedia
    │
    ▼
Discogs
    │
    ▼
Last.fm
    │
    ▼
Context Builder
    │
    ▼
Knowledge Builder
    │
    ▼
Editorial Style Engine
    │
    ▼
GPT-5.5
    │
    ▼
Editorial Quality Engine
    │
    ▼
Review
    │
    ▼
Apply
```

The pipeline is designed to minimize hallucinations by grounding generation in verified metadata whenever possible.

---

# Safety Model

## Read-only commands

- doctor
- audit
- scan
- plan
- metadata
- context
- preview
- review (until Apply is confirmed)
- library plan
- library review

## Write commands

- apply
- library apply
- review (after confirmation)

Before every write operation Plex Music Enhancer

- creates a backup
- writes metadata
- reloads the album
- verifies the result
- stores an audit record

---

# Documentation

## 📘 German User Manual

A complete German handbook is available as PDF.

**Download**

- `assets/pdf/Plex-Music-Enhancer-Handbuch-v1.0.pdf`

The handbook covers

- Installation
- Configuration
- Every CLI command
- Complete workflows
- AI pipeline
- Editorial Style Engine
- Review System
- Providers
- Cache
- Troubleshooting
- FAQ
- Glossary

The PDF is also available in the GitHub Releases section.

---

## Technical Documentation

- Architecture
- Getting Started
- Configuration
- Commands
- Editorial Engine
- AI Generation
- Review System
- Cache
- Performance
- Verification
- Developer Guide
- Release Notes
- Changelog

---

# Troubleshooting

First run

```bash
plex-enhancer doctor
```

If OpenAI is not used

- verify `OPENAI_API_KEY`
- verify provider selection

If metadata is incomplete

- verify provider configuration
- clear provider cache

If Apply fails

- inspect Review warnings
- inspect Quality checks

---

# Development

Install developer dependencies

```bash
make install
```

Formatting

```bash
make format
```

Lint

```bash
make lint
```

Tests

```bash
make test
```

Install pre-commit hooks

```bash
pre-commit install
```

---

# Docker

```bash
docker compose run --rm plex-music-enhancer doctor
```

---

# Roadmap

Current release

- ✅ Version 1.0

Planned

- Web UI
- Native desktop application
- Additional metadata providers
- Multi-language generation
- Extended verification
- Plugin ecosystem

---

# Contributing

Contributions, feature requests and bug reports are welcome.

Please read

- CONTRIBUTING.md

before submitting pull requests.

---

# License

MIT License

---

# Acknowledgements

This project builds upon the excellent work of

- Plex
- MusicBrainz
- Wikipedia
- Discogs
- Last.fm
- OpenAI
- Typer
- Rich