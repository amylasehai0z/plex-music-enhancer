"""Metadata provider integrations."""

from plex_music_enhancer.providers.base import AlbumMetadata, ArtistMetadata, MetadataProvider
from plex_music_enhancer.providers.manager import ProviderManager
from plex_music_enhancer.providers.musicbrainz import MusicBrainzProvider
from plex_music_enhancer.providers.wikipedia import WikipediaProvider

__all__ = [
    "AlbumMetadata",
    "ArtistMetadata",
    "MetadataProvider",
    "MusicBrainzProvider",
    "ProviderManager",
    "WikipediaProvider",
]
