"""Wikipedia metadata provider package."""

from plex_music_enhancer.providers.wikipedia.client import WikipediaClient
from plex_music_enhancer.providers.wikipedia.provider import WikipediaProvider, WikipediaSummary

__all__ = ["WikipediaClient", "WikipediaProvider", "WikipediaSummary"]
