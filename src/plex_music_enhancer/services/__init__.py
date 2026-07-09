"""Application services."""

from plex_music_enhancer.services.configuration import ConfigurationService
from plex_music_enhancer.services.enrichment import (
    AlbumMetadata,
    AlbumMetadataDocument,
    MetadataEnrichmentPipeline,
    MusicBrainzEnrichmentMetadata,
    PlexAlbumMetadata,
)
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult, MusicBrainzMatcher
from plex_music_enhancer.services.preview import (
    ArtistPreviewDocument,
    EnrichmentPreviewDocument,
    EnrichmentPreviewService,
    PreviewError,
)

__all__ = [
    "AlbumMetadata",
    "AlbumMetadataDocument",
    "ArtistPreviewDocument",
    "ConfigurationService",
    "EnrichmentPreviewDocument",
    "EnrichmentPreviewService",
    "MatchResult",
    "MetadataEnrichmentPipeline",
    "MusicBrainzEnrichmentMetadata",
    "MusicBrainzMatcher",
    "PlexAlbumMetadata",
    "PreviewError",
]
