"""Readers for temporary developer-mode debug artifacts."""

from __future__ import annotations

import json
import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from plex_music_enhancer.ai.openai import PROMPT_DEBUG_METADATA_PATH
from plex_music_enhancer.developer.models import (
    PromptDebugDocument,
    PromptDebugStats,
    PromptMetaDocument,
    ReviewLogDocument,
)
from plex_music_enhancer.review.debug import PROMPT_DEBUG_DUMP_PATH, REVIEW_DEBUG_LOG_PATH


class PromptDebugReader:
    """Read the exact prompt text last sent to an AI provider."""

    def __init__(
        self,
        path: Path | None = None,
        meta_path: Path | None = None,
    ) -> None:
        """Create a prompt reader."""
        self._path = path or PROMPT_DEBUG_DUMP_PATH
        self._meta_path = meta_path or PROMPT_DEBUG_METADATA_PATH

    def read(self) -> PromptDebugDocument:
        """Read prompt text and compute local statistics."""
        content = _read_text(self._path)
        meta = _read_json(self._meta_path)
        stats = PromptDebugStats(
            characters=len(content),
            words=len(content.split()),
            estimated_tokens=_estimate_tokens(content),
            budget=_int_or_none(meta.get("max_prompt_characters")),
            prompt_version=_str_or_none(meta.get("prompt_version")),
        )
        return PromptDebugDocument(
            path=self._path,
            exists=self._path.exists(),
            content=content,
            stats=stats,
        )


class PromptMetaReader:
    """Read structured prompt metadata written by the AI provider."""

    def __init__(self, path: Path | None = None) -> None:
        """Create a metadata reader."""
        self._path = path or PROMPT_DEBUG_METADATA_PATH

    def read(self) -> PromptMetaDocument:
        """Read prompt metadata without raising on missing or malformed files."""
        return PromptMetaDocument(
            path=self._path,
            exists=self._path.exists(),
            payload=_read_json(self._path),
        )


class ReviewLogReader:
    """Read and parse the temporary review debug log."""

    _SECTION_PATTERN = re.compile(r"^===\s+(.+?)\s+=+\s*$", re.MULTILINE)

    def __init__(self, path: Path | None = None) -> None:
        """Create a review-log reader."""
        self._path = path or REVIEW_DEBUG_LOG_PATH

    def read(self) -> ReviewLogDocument:
        """Read the review log and split it into named sections."""
        content = _read_text(self._path)
        return ReviewLogDocument(
            path=self._path,
            exists=self._path.exists(),
            content=content,
            sections=self._sections(content),
        )

    def _sections(self, content: str) -> dict[str, str]:
        """Return section names and contents from a review debug log."""
        matches = list(self._SECTION_PATTERN.finditer(content))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            name = " ".join(match.group(1).strip().split())
            sections[name] = content[start:end].strip()
        return sections


def _read_text(path: Path) -> str:
    """Read text from a file, returning an empty string on failure."""
    with suppress(OSError, UnicodeDecodeError):
        return path.read_text(encoding="utf-8")
    return ""


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from a file without raising."""
    with suppress(OSError, UnicodeDecodeError, json.JSONDecodeError):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return {}


def _estimate_tokens(text: str) -> int:
    """Return a conservative local token estimate."""
    return max(1, round(len(text) / 4)) if text else 0


def _int_or_none(value: object) -> int | None:
    """Return an integer when possible."""
    return value if isinstance(value, int) else None


def _str_or_none(value: object) -> str | None:
    """Return a string when possible."""
    return value if isinstance(value, str) else None
