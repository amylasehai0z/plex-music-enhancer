"""MusicBrainz provider package."""

from plex_music_enhancer.providers.musicbrainz.client import MusicBrainzClient
from plex_music_enhancer.providers.musicbrainz.models import (
    MusicBrainzAlbumMetadata,
    MusicBrainzAlbumSearchResult,
    MusicBrainzAlias,
    MusicBrainzArtistMetadata,
    MusicBrainzArtistSearchResult,
)
from plex_music_enhancer.providers.musicbrainz.provider import MusicBrainzProvider

__all__ = [
    "MusicBrainzAlias",
    "MusicBrainzAlbumMetadata",
    "MusicBrainzAlbumSearchResult",
    "MusicBrainzArtistMetadata",
    "MusicBrainzArtistSearchResult",
    "MusicBrainzClient",
    "MusicBrainzProvider",
]
