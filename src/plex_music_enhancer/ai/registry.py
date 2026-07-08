"""AI provider registry."""

from __future__ import annotations

from collections.abc import Callable

from plex_music_enhancer.ai.base import AIProvider
from plex_music_enhancer.ai.dummy import DummyProvider
from plex_music_enhancer.ai.exceptions import (
    AIProviderNotFoundError,
    AIProviderNotImplementedError,
)
from plex_music_enhancer.config import AISettings

ProviderFactory = Callable[[AISettings | None], AIProvider]

SUPPORTED_PROVIDER_NAMES = ("dummy", "openai", "ollama")


class AIProviderRegistry:
    """Registry for AI provider factories."""

    def __init__(self) -> None:
        """Create an empty provider registry."""
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        """Register a provider factory."""
        normalized_name = _normalize_provider_name(name)
        if normalized_name not in SUPPORTED_PROVIDER_NAMES:
            msg = f'Unknown AI provider "{name}".'
            raise AIProviderNotFoundError(msg)

        self._factories[normalized_name] = factory

    def create(self, name: str, settings: AISettings | None = None) -> AIProvider:
        """Create a provider by name."""
        normalized_name = _normalize_provider_name(name)
        if normalized_name not in SUPPORTED_PROVIDER_NAMES:
            supported = ", ".join(SUPPORTED_PROVIDER_NAMES)
            msg = f'Unknown AI provider "{name}". Supported providers: {supported}.'
            raise AIProviderNotFoundError(msg)

        factory = self._factories.get(normalized_name)
        if factory is None:
            msg = f'AI provider "{normalized_name}" is known but not implemented yet.'
            raise AIProviderNotImplementedError(msg)

        return factory(settings)

    def provider_names(self) -> list[str]:
        """Return all supported provider names."""
        return list(SUPPORTED_PROVIDER_NAMES)

    def implemented_provider_names(self) -> list[str]:
        """Return currently implemented provider names."""
        return sorted(self._factories)


def create_default_registry() -> AIProviderRegistry:
    """Create the default AI provider registry."""
    from plex_music_enhancer.ai.openai import OpenAIProvider

    registry = AIProviderRegistry()
    registry.register("dummy", lambda settings: DummyProvider())
    registry.register("openai", lambda settings: OpenAIProvider(settings=settings))
    return registry


def _normalize_provider_name(name: str) -> str:
    """Normalize a provider name."""
    return name.strip().casefold()
