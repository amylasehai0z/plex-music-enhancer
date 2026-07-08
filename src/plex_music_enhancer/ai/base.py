"""Abstract AI provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from plex_music_enhancer.ai.models import (
    AICapabilities,
    AIProviderMetadata,
    GeneratedSummary,
)
from plex_music_enhancer.prompts.renderer import RenderedPrompt


class AIProvider(ABC):
    """Common interface implemented by AI generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable provider name."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the configured provider model name."""

    @abstractmethod
    def validate_configuration(self) -> None:
        """Validate provider configuration before generation."""

    @abstractmethod
    def capabilities(self) -> AICapabilities:
        """Return provider capabilities."""

    @abstractmethod
    def provider_metadata(self) -> AIProviderMetadata:
        """Return provider metadata for diagnostics and reporting."""

    @abstractmethod
    def generate_album_summary(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an album summary from a rendered prompt."""

    @abstractmethod
    def generate_artist_summary(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an artist summary from a rendered prompt."""
