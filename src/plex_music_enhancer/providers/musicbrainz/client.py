"""HTTP client for the official MusicBrainz Web Service API."""

from __future__ import annotations

from threading import Lock
from time import monotonic, sleep
from typing import Any

import httpx

from plex_music_enhancer.constants import __version__

MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RATE_LIMIT_SECONDS = 1.0
DEFAULT_RETRIES = 2
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class MusicBrainzClient:
    """Synchronous MusicBrainz API client with rate limiting and retries."""

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        base_url: str = MUSICBRAINZ_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        user_agent: str | None = None,
    ) -> None:
        """Create a MusicBrainz API client."""
        self._base_url = base_url.rstrip("/")
        self._rate_limit_seconds = rate_limit_seconds
        self._retries = retries
        self._lock = Lock()
        self._last_request_at: float | None = None
        self._headers = {
            "Accept": "application/json",
            "User-Agent": user_agent or _default_user_agent(),
        }
        self._client = http_client or httpx.Client(
            timeout=timeout_seconds,
            headers=self._headers,
        )

    def get_json(self, endpoint: str, *, params: dict[str, object]) -> dict[str, Any]:
        """Fetch JSON from a MusicBrainz endpoint."""
        with self._lock:
            self._wait_for_rate_limit()
            response = self._request_with_retries(endpoint, params=params)
            self._last_request_at = monotonic()

        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _request_with_retries(
        self,
        endpoint: str,
        *,
        params: dict[str, object],
    ) -> httpx.Response:
        """Request an endpoint and retry transient failures."""
        last_error: httpx.RequestError | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(
                    f"{self._base_url}/{endpoint.lstrip('/')}",
                    params={**params, "fmt": "json"},
                    headers=self._headers,
                )
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == self._retries:
                    raise

                self._sleep_before_retry(attempt)
                continue

            if response.status_code not in TRANSIENT_STATUS_CODES:
                return response

            if attempt == self._retries:
                return response

            self._sleep_before_retry(attempt)

        if last_error is not None:
            raise last_error

        raise RuntimeError("MusicBrainz request retry loop exited unexpectedly.")

    def _wait_for_rate_limit(self) -> None:
        """Wait until the next MusicBrainz request is allowed."""
        if self._last_request_at is None or self._rate_limit_seconds <= 0:
            return

        elapsed = monotonic() - self._last_request_at
        wait_seconds = self._rate_limit_seconds - elapsed
        if wait_seconds > 0:
            sleep(wait_seconds)

    def _sleep_before_retry(self, attempt: int) -> None:
        """Sleep briefly before retrying a transient failure."""
        if self._rate_limit_seconds <= 0:
            return

        sleep(self._rate_limit_seconds * (attempt + 1))


def _default_user_agent() -> str:
    """Return the project User-Agent required by MusicBrainz."""
    return f"plex-music-enhancer/{__version__} ( https://github.com/plex-music-enhancer )"
