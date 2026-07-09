"""Album context enrichment pipeline."""

from plex_music_enhancer.enrichment.models import (
    AlbumContext,
    ArtistContext,
    DiscogsAlbumContext,
    DiscogsArtistContext,
    LastFMAlbumContext,
    LastFMArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)

__all__ = [
    "AlbumContext",
    "ArtistContext",
    "DiscogsAlbumContext",
    "DiscogsArtistContext",
    "LastFMAlbumContext",
    "LastFMArtistContext",
    "EnrichmentPipeline",
    "EnrichmentPipelineError",
    "MusicBrainzAlbumContext",
    "MusicBrainzArtistContext",
    "PipelineContext",
    "PlexAlbumContext",
    "PlexArtistContext",
    "WikipediaAlbumContext",
    "WikipediaArtistContext",
]


def __getattr__(name: str) -> object:
    """Lazily expose pipeline classes without importing service dependencies early."""
    if name in {"EnrichmentPipeline", "EnrichmentPipelineError"}:
        from plex_music_enhancer.enrichment.pipeline import (
            EnrichmentPipeline,
            EnrichmentPipelineError,
        )

        exports = {
            "EnrichmentPipeline": EnrichmentPipeline,
            "EnrichmentPipelineError": EnrichmentPipelineError,
        }
        return exports[name]

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
