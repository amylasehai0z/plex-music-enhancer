"""Debug log REST endpoints."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from plex_music_enhancer.ai.openai import PROMPT_DEBUG_METADATA_PATH
from plex_music_enhancer.review.debug import PROMPT_DEBUG_DUMP_PATH, REVIEW_DEBUG_LOG_PATH

router = APIRouter()


@router.get("/review")
async def review_log() -> dict[str, Any]:
    """Return the temporary review debug log."""
    return _text_log(REVIEW_DEBUG_LOG_PATH)


@router.get("/prompt")
async def prompt_log() -> dict[str, Any]:
    """Return the temporary OpenAI prompt debug log."""
    payload = _text_log(PROMPT_DEBUG_DUMP_PATH)
    payload["metadata"] = _json_log(PROMPT_DEBUG_METADATA_PATH)
    return payload


def _text_log(path: Path) -> dict[str, Any]:
    """Return a text log payload."""
    with suppress(OSError):
        return {"path": str(path), "exists": True, "content": path.read_text(encoding="utf-8")}
    return {"path": str(path), "exists": False, "content": ""}


def _json_log(path: Path) -> dict[str, Any]:
    """Return a JSON-ish log payload without raising."""
    with suppress(OSError):
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    return {}
