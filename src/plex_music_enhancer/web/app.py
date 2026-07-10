"""FastAPI application factory for Plex Music Enhancer."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from plex_music_enhancer.api.models import API_VERSION
from plex_music_enhancer.web.errors import register_exception_handlers
from plex_music_enhancer.web.routers import (
    albums,
    apply,
    artists,
    config,
    debug,
    library,
    logs,
    preview,
    providers,
    review,
    statistics,
    system,
)


def create_app():
    """Create the FastAPI application."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover - exercised when web extra is absent.
        msg = 'FastAPI is not installed. Install Plex Music Enhancer with the "web" extra.'
        raise RuntimeError(msg) from exc

    app = FastAPI(
        title="Plex Music Enhancer API",
        version=version("plex-music-enhancer"),
        openapi_url=f"/api/{API_VERSION}/openapi.json",
        docs_url=f"/api/{API_VERSION}/docs",
        redoc_url=f"/api/{API_VERSION}/redoc",
    )
    register_exception_handlers(app)
    prefix = f"/api/{API_VERSION}"
    app.include_router(system.router, prefix=f"{prefix}/system", tags=["system"])
    app.include_router(config.router, prefix=f"{prefix}/config", tags=["config"])
    app.include_router(providers.router, prefix=f"{prefix}/providers", tags=["providers"])
    app.include_router(library.router, prefix=f"{prefix}/library", tags=["library"])
    app.include_router(artists.router, prefix=f"{prefix}/artists", tags=["artists"])
    app.include_router(albums.router, prefix=f"{prefix}/albums", tags=["albums"])
    app.include_router(review.router, prefix=f"{prefix}/review", tags=["review"])
    app.include_router(preview.router, prefix=f"{prefix}/preview", tags=["preview"])
    app.include_router(apply.router, prefix=f"{prefix}/apply", tags=["apply"])
    app.include_router(statistics.router, prefix=f"{prefix}/statistics", tags=["statistics"])
    app.include_router(logs.router, prefix=f"{prefix}/logs", tags=["logs"])
    app.include_router(debug.router, prefix=f"{prefix}/debug", tags=["debug"])
    static_dir = Path(__file__).resolve().parent / "static"
    index_path = static_dir / "index.html"
    if index_path.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="frontend-assets")
        logo_dir = static_dir / "logo"
        if logo_dir.exists():
            app.mount("/logo", StaticFiles(directory=logo_dir), name="frontend-logo")

        @app.get("/", include_in_schema=False)
        async def frontend_index() -> FileResponse:
            return FileResponse(index_path)

        @app.get("/{path:path}", include_in_schema=False)
        async def frontend_spa_fallback(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API endpoint not found.")
            return FileResponse(index_path)

    return app


app = create_app()
