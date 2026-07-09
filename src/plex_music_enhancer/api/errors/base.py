"""Versioned backend API error types."""

from __future__ import annotations

from typing import Any


class APIError(Exception):
    """Base class for errors that can later be mapped to API responses."""

    code = "api_error"
    status_code = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        """Create an API error with optional structured details."""
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_problem(self) -> dict[str, Any]:
        """Return a stable RFC-7807-like error payload."""
        return {
            "code": self.code,
            "message": self.message,
            "statusCode": self.status_code,
            "details": self.details,
        }


class ConfigurationAPIError(APIError):
    """Raised when configuration is missing or invalid."""

    code = "configuration_error"
    status_code = 400


class ProviderAPIError(APIError):
    """Raised when an external metadata or AI provider fails."""

    code = "provider_error"
    status_code = 502


class VerificationAPIError(APIError):
    """Raised when fact verification cannot be completed."""

    code = "verification_error"
    status_code = 422


class ReviewAPIError(APIError):
    """Raised when a review document cannot be created or updated."""

    code = "review_error"
    status_code = 422


class PromptAPIError(APIError):
    """Raised when prompt rendering or budgeting fails."""

    code = "prompt_error"
    status_code = 422


class PlexAPIError(APIError):
    """Raised when Plex access fails."""

    code = "plex_error"
    status_code = 502


class ValidationAPIError(APIError):
    """Raised when an API request is structurally valid but not acceptable."""

    code = "validation_error"
    status_code = 400
