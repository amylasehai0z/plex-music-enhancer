"""Developer-mode diagnostics REST endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from plex_music_enhancer.developer import (
    DeveloperAnalyzer,
    PromptDebugReader,
    PromptMetaReader,
    ReviewLogReader,
)

router = APIRouter()


@router.get("/prompt")
async def debug_prompt() -> dict[str, Any]:
    """Return the latest prompt debug document."""
    return PromptDebugReader().read().to_dict()


@router.get("/meta")
async def debug_meta() -> dict[str, Any]:
    """Return the latest prompt metadata debug document."""
    return PromptMetaReader().read().to_dict()


@router.get("/review")
async def debug_review() -> dict[str, Any]:
    """Return the latest parsed review debug log."""
    return ReviewLogReader().read().to_dict()


@router.get("/explain")
async def debug_explain() -> dict[str, Any]:
    """Return the developer explainability analysis."""
    return DeveloperAnalyzer().explain().to_dict()


@router.get("/doctor")
async def debug_doctor() -> dict[str, Any]:
    """Return the full developer diagnostics report."""
    return DeveloperAnalyzer().doctor().to_dict()
