# Web Backend and Static Frontend

This package contains the optional FastAPI REST backend for Plex Music Enhancer
and serves the built React frontend from `static/` when it is available.

Layout:

- `app.py`: FastAPI application factory.
- `dependencies.py`: service dependency factories for runtime and tests.
- `routers/`: versioned REST route adapters.
- `middleware/`: placeholders for future auth, CORS, and trusted-host middleware.
- `responses/`: placeholders for shared response helpers.
- `schemas/`: web-specific request and response schema adapters.
- `contracts/`: web-facing imports or adapters around shared application contracts.
- `static/`: packaged Vite build output served by FastAPI.
- `frontend/`: package-adjacent notes for frontend integration.

The React source lives in the repository-level `web/` directory. It consumes
only the REST API and contains no business logic.

Start with:

```bash
plex-enhancer serve
```

The web interface is available at `/`. OpenAPI is available at
`/api/v1/openapi.json`, Swagger UI at `/api/v1/docs`, and ReDoc at
`/api/v1/redoc`.
