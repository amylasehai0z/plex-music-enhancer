"""Library REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def library_overview() -> dict[str, list[object]]:
    """Return a placeholder library overview."""
    return {"libraries": []}
