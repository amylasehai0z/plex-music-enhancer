"""HTTP client for the official Wikipedia REST API."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from plex_music_enhancer.constants import __version__

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = f"plex-music-enhancer/{__version__} (wikipedia provider)"


class WikipediaClient:
    """Small synchronous client for Wikipedia REST endpoints."""

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        """Create a Wikipedia REST client."""
        self._client = http_client or httpx.Client(timeout=timeout_seconds)
        self._headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }

    def search_titles(
        self,
        query: str,
        *,
        language: str,
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        """Search Wikipedia page titles for a language edition."""
        response = self._client.get(
            f"https://{language}.wikipedia.org/w/rest.php/v1/search/title",
            params={"q": query, "limit": limit},
            headers=self._headers,
        )
        response.raise_for_status()
        payload = response.json()
        pages = payload.get("pages") if isinstance(payload, dict) else None
        if not isinstance(pages, list):
            return []

        return [page for page in pages if isinstance(page, dict)]

    def get_summary(self, title: str, *, language: str) -> dict[str, Any] | None:
        """Fetch a Wikipedia page summary for a language edition."""
        response = self._client.get(
            f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
            headers=self._headers,
        )
        if response.status_code == httpx.codes.NOT_FOUND:
            return None

        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
