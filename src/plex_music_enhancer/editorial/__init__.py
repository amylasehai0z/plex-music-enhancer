"""Editorial composition for album prompts."""

from plex_music_enhancer.editorial.artist import ArtistEditorialComposer
from plex_music_enhancer.editorial.composer import EditorialComposer
from plex_music_enhancer.editorial.models import EditorialContext, EditorialFact
from plex_music_enhancer.editorial.style import (
    GermanEditorialStyleEngine,
    GermanStyleDiagnostics,
    GermanStyleResult,
)

__all__ = [
    "EditorialComposer",
    "ArtistEditorialComposer",
    "EditorialContext",
    "EditorialFact",
    "GermanEditorialStyleEngine",
    "GermanStyleDiagnostics",
    "GermanStyleResult",
]
