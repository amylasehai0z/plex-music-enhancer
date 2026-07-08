"""Provider-independent AI generation layer."""

from plex_music_enhancer.ai.base import AIProvider
from plex_music_enhancer.ai.dummy import DummyProvider
from plex_music_enhancer.ai.exceptions import (
    AIError,
    AIProviderConfigurationError,
    AIProviderNotFoundError,
    AIProviderNotImplementedError,
    AIProviderRequestError,
)
from plex_music_enhancer.ai.manager import AIManager
from plex_music_enhancer.ai.models import (
    AICapabilities,
    AIProviderMetadata,
    GeneratedSummary,
)
from plex_music_enhancer.ai.openai import OpenAIProvider
from plex_music_enhancer.ai.registry import AIProviderRegistry, create_default_registry

__all__ = [
    "AICapabilities",
    "AIError",
    "AIManager",
    "AIProvider",
    "AIProviderConfigurationError",
    "AIProviderMetadata",
    "AIProviderNotFoundError",
    "AIProviderNotImplementedError",
    "AIProviderRequestError",
    "AIProviderRegistry",
    "DummyProvider",
    "GeneratedSummary",
    "OpenAIProvider",
    "create_default_registry",
]
