"""AI provider manager."""

from __future__ import annotations

from plex_music_enhancer.ai.base import AIProvider
from plex_music_enhancer.ai.models import (
    AICapabilities,
    AIProviderMetadata,
    GeneratedSummary,
)
from plex_music_enhancer.ai.registry import AIProviderRegistry, create_default_registry
from plex_music_enhancer.config import AISettings, Settings
from plex_music_enhancer.enrichment.models import AlbumContext, ArtistContext
from plex_music_enhancer.prompts.builder import PromptBuilder
from plex_music_enhancer.prompts.renderer import RenderedPrompt


class AIManager:
    """Load, validate, and dispatch requests to the configured AI provider."""

    def __init__(
        self,
        *,
        settings: AISettings | None = None,
        registry: AIProviderRegistry | None = None,
        provider: AIProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Create an AI manager."""
        self._settings = settings or Settings().ai
        self._registry = registry or create_default_registry()
        self._provider = provider or self._registry.create(
            self._settings.provider,
            settings=self._settings,
        )
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._provider.validate_configuration()

    @property
    def provider(self) -> AIProvider:
        """Return the configured AI provider."""
        return self._provider

    def capabilities(self) -> AICapabilities:
        """Return configured provider capabilities."""
        return self._provider.capabilities()

    def provider_metadata(self) -> AIProviderMetadata:
        """Return configured provider metadata."""
        return self._provider.provider_metadata()

    def generate_album_summary(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> GeneratedSummary:
        """Generate an album summary using the configured provider."""
        prompt = self.render_album_summary_prompt(context, prompt_name=prompt_name)
        return self.generate_album_summary_from_prompt(prompt)

    def render_album_summary_prompt(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> RenderedPrompt:
        """Render an album summary prompt from album context."""
        return self._prompt_builder.build_album_summary_prompt(context, prompt_name=prompt_name)

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an album summary from a rendered prompt."""
        return self._provider.generate_album_summary(prompt)

    def generate_artist_summary(self, context: ArtistContext) -> GeneratedSummary:
        """Generate an artist summary using the configured provider."""
        prompt = self.render_artist_summary_prompt(context)
        return self.generate_artist_summary_from_prompt(prompt)

    def render_artist_summary_prompt(self, context: ArtistContext) -> RenderedPrompt:
        """Render an artist summary prompt from artist context."""
        return self._prompt_builder.build_artist_summary_prompt(context)

    def generate_artist_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an artist summary from a rendered prompt."""
        return self._provider.generate_artist_summary(prompt)
