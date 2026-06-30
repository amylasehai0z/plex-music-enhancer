"""Minimal Plex API client used for diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from defusedxml import ElementTree
from pydantic import AnyHttpUrl, SecretStr


@dataclass(frozen=True, slots=True)
class PlexConnectionResult:
    """Result of a Plex connectivity check."""

    ok: bool
    status_code: int | None = None
    server_name: str | None = None
    message: str | None = None


class PlexClient:
    """Small Plex API client for health checks.

    Metadata enrichment is intentionally out of scope for the initial project
    foundation. This client only validates that a configured Plex server can be
    reached and authenticated.
    """

    def __init__(
        self,
        base_url: AnyHttpUrl,
        token: SecretStr,
        *,
        timeout_seconds: float,
    ) -> None:
        """Create a Plex client.

        Args:
            base_url: Base URL of the Plex server.
            token: Plex authentication token.
            timeout_seconds: Request timeout in seconds.

        """
        self._base_url = str(base_url).rstrip("/")
        self._token = token
        self._timeout_seconds = timeout_seconds

    def check_connection(self) -> PlexConnectionResult:
        """Attempt to connect to the Plex server root endpoint."""
        try:
            response = httpx.get(
                self._build_url("/"),
                headers={"X-Plex-Token": self._token.get_secret_value()},
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException:
            return PlexConnectionResult(ok=False, message="Connection timed out.")
        except httpx.RequestError as exc:
            return PlexConnectionResult(ok=False, message=str(exc))

        if response.status_code == httpx.codes.UNAUTHORIZED:
            return PlexConnectionResult(
                ok=False,
                status_code=response.status_code,
                message="Authentication failed. Check the Plex token.",
            )

        if response.is_error:
            return PlexConnectionResult(
                ok=False,
                status_code=response.status_code,
                message=f"Plex returned HTTP {response.status_code}.",
            )

        return PlexConnectionResult(
            ok=True,
            status_code=response.status_code,
            server_name=_extract_server_name(response.text),
            message="Connected successfully.",
        )

    def _build_url(self, path: str) -> str:
        """Build an absolute Plex API URL."""
        return f"{self._base_url}{path}"


def _extract_server_name(xml_text: str) -> str | None:
    """Extract a Plex server name from the root XML response."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return None

    return root.attrib.get("friendlyName") or root.attrib.get("machineIdentifier")
