"""Metadata provider integrations."""

from plex_music_enhancer.providers.base import AlbumMetadata, ArtistMetadata, MetadataProvider
from plex_music_enhancer.providers.discogs import DiscogsProvider
from plex_music_enhancer.providers.lastfm import LastFMProvider
from plex_music_enhancer.providers.manager import ProviderManager
from plex_music_enhancer.providers.musicbrainz import MusicBrainzProvider
from plex_music_enhancer.providers.wikipedia import WikipediaProvider

__all__ = [
    "AlbumMetadata",
    "ArtistMetadata",
    "DiscogsProvider",
    "LastFMProvider",
    "MetadataProvider",
    "MusicBrainzProvider",
    "ProviderManager",
    "WikipediaProvider",
]
