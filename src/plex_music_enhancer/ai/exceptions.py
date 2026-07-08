"""AI subsystem exceptions."""

from __future__ import annotations


class AIError(Exception):
    """Base exception for AI generation failures."""


class AIProviderConfigurationError(AIError):
    """Raised when an AI provider is not configured correctly."""


class AIProviderNotFoundError(AIError):
    """Raised when an unknown AI provider name is requested."""


class AIProviderNotImplementedError(AIError):
    """Raised when a known AI provider has not been implemented yet."""


class AIProviderRequestError(AIError):
    """Raised when an AI provider request fails."""
