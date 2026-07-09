# Backend API

Plex Music Enhancer contains an internal backend API layer, an optional FastAPI
REST backend, and a packaged React web interface. The web interface is a thin
REST client and contains no business logic.

The goal is to define stable request/response boundaries so the CLI and a later
web interface can use the same application services.

## Package Layout

```text
src/plex_music_enhancer/api/
    __init__.py
    models.py
    errors/
    routers/
    schemas/
    services/
```

- `models.py` defines versioned request and response models.
- `errors/` contains a shared error hierarchy.
- `services/` contains adapters around existing application services.
- `schemas/` re-exports the stable models for future OpenAPI generation.
- `routers/` contains versioned FastAPI route adapters.

## API Versioning

The internal API starts with:

```text
v1
```

Future HTTP endpoints should use:

```text
/api/v1/
```

Breaking changes should create a new version instead of changing existing field
names silently.

## Starting the REST Server

Install the optional web extra and start Uvicorn through the CLI:

```bash
python -m pip install ".[web]"
plex-enhancer serve
```

Available URLs:

- Web interface: `http://127.0.0.1:1008/`
- Swagger UI: `http://127.0.0.1:1008/api/v1/docs`
- ReDoc: `http://127.0.0.1:1008/api/v1/redoc`
- OpenAPI JSON: `http://127.0.0.1:1008/api/v1/openapi.json`

## Implemented Endpoints

- `GET /api/v1/system/health`
- `GET /api/v1/system/version`
- `GET /api/v1/config`
- `PUT /api/v1/config`
- `GET /api/v1/providers`
- `GET /api/v1/statistics`
- `GET /api/v1/logs/review`
- `GET /api/v1/logs/prompt`
- `POST /api/v1/review/artist`
- `POST /api/v1/review/album`
- `POST /api/v1/preview`
- `POST /api/v1/apply`

Router namespaces also exist for `/api/v1/library`, `/api/v1/artists`, and
`/api/v1/albums`. They return stable empty structures until the corresponding
service-backed list endpoints are added.

## Data Models

Important v1 models include:

- `AlbumReviewRequest`
- `ArtistReviewRequest`
- `AlbumReviewResponse`
- `ArtistReviewResponse`
- `PreviewRequest`
- `PreviewResponse`
- `ApplyRequest`
- `ApplyResponse`
- `ReviewDocument`
- `PromptAnalysis`
- `QualityAnalysis`
- `EditorialAnalysis`
- `VerificationAnalysis`
- `ProviderInfo`
- `LibraryArtist`
- `LibraryAlbum`
- `StatisticsResponse`
- `ConfigurationResponse`

Models are immutable Pydantic models and use stable, descriptive JSON aliases
such as `ratingKey`, `currentSummary`, `promptTokens`, and `apiVersion`.

## ReviewDocument

`ReviewDocument` is the central exchange structure for review-related clients.
It contains:

- current summary
- generated summary
- proposed summary
- unified diff
- QA status
- editorial analysis
- verification analysis
- prompt budget
- prompt decisions
- prompt quality
- prompt efficiency
- prompt utilization
- evidence ranking
- evidence coverage
- editorial coverage
- editorial balance
- missed opportunities
- provider and model
- timing
- token usage
- debug metadata

The existing CLI still serializes the current domain `ReviewDocument`. The new
API mapper can convert that document into the stable internal API document. A
future migration can switch CLI JSON output to the API document once users have
had a compatibility window.

## Unified Service Interfaces

New API service adapters use request models:

```python
ReviewAPIService.review(AlbumReviewRequest(...))
ReviewAPIService.review(ArtistReviewRequest(...))
ApplyAPIService.apply(ApplyRequest(...))
ConfigurationAPIService.configuration()
```

The adapters reuse existing services and do not duplicate business logic.
FastAPI dependencies create these adapters and can be overridden in tests.

## Error Model

All future API-facing failures should derive from `APIError`:

- `ConfigurationAPIError`
- `ProviderAPIError`
- `VerificationAPIError`
- `ReviewAPIError`
- `PromptAPIError`
- `PlexAPIError`
- `ValidationAPIError`

Each error exposes `to_problem()`, a stable problem-style payload that can later
be mapped to HTTP responses. FastAPI exception handlers perform this mapping
centrally.

## Logging and Debug Data

The current review debug log is still text-based. Its underlying data is now
represented in `PromptAnalysis`, `DebugMeta`, `QualityAnalysis`,
`EditorialAnalysis`, and `VerificationAnalysis`.

Future REST clients should consume these structured fields instead of parsing
`/tmp/plex_review.log`.

REST log endpoints expose the same temporary debug files used by the CLI:

- `/tmp/openai_prompt.txt`
- `/tmp/openai_prompt_meta.json`
- `/tmp/plex_review.log`

## Performance Notes

The following operations can be long-running and should remain service-driven so
they can later move behind job queues or async adapters:

- preview
- review
- translation
- improvement
- AI generation
- Plex scanning
- cache listing and clearing
- library workflows

The current code remains synchronous. No async refactor is performed in this
milestone.

## Web Build

The React source lives in the repository-level `web/` directory. It uses React,
TypeScript, Vite, React Router, TanStack Query, Mantine, Monaco Editor and
Monaco Diff Editor.

Useful development commands:

```bash
cd web
npm install
npm test
npm run build
```

The production build is written to:

```text
src/plex_music_enhancer/web/static/
```

FastAPI serves that directory from the same process as the REST API. If no build
exists, REST endpoints still work and the frontend routes are not registered.

## Security Preparation

The package contains placeholders for future middleware. API keys, bearer
tokens, session authentication, CORS, and trusted-host checks are not enabled
yet and should be added before exposing the API outside a trusted local network.

## Roadmap

### Phase 1: Architecture

Completed: shared contracts, configuration service, and web package structure.

### Phase 2: Internal API

Completed in this milestone: versioned models, error hierarchy, service
adapters, and domain-to-API mappers.

### Phase 3: FastAPI

Completed: FastAPI application factory, dependency injection, exception
handlers, OpenAPI, Swagger UI, ReDoc, and Uvicorn start command.

### Phase 4: REST Endpoints

Completed for system, configuration, providers, statistics, logs, review,
preview, and apply. Library, artist, and album list namespaces are prepared.

### Phase 5: React

Build a review-first browser interface on top of the REST API.

### Phase 6: Desktop App

Wrap the web interface in a desktop shell only after the API and browser UI are
stable.
