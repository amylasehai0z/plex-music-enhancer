"""Application services."""

from plex_music_enhancer.services.enrichment import (
    AlbumMetadata,
    AlbumMetadataDocument,
    MetadataEnrichmentPipeline,
    MusicBrainzEnrichmentMetadata,
    PlexAlbumMetadata,
)
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult, MusicBrainzMatcher
from plex_music_enhancer.services.preview import (
    EnrichmentPreviewDocument,
    EnrichmentPreviewService,
    PlexAlbumPreview,
    PreviewError,
    ProviderPreviewStatus,
)

__all__ = [
    "AlbumMetadata",
    "AlbumMetadataDocument",
    "EnrichmentPreviewDocument",
    "EnrichmentPreviewService",
    "MatchResult",
    "MetadataEnrichmentPipeline",
    "MusicBrainzEnrichmentMetadata",
    "MusicBrainzMatcher",
    "PlexAlbumPreview",
    "PlexAlbumMetadata",
    "PreviewError",
    "ProviderPreviewStatus",
]
