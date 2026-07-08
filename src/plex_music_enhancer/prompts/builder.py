"""Prompt construction from enrichment context."""

from __future__ import annotations

from plex_music_enhancer.enrichment.models import AlbumContext, ArtistContext
from plex_music_enhancer.prompts.registry import PromptRegistry
from plex_music_enhancer.prompts.renderer import PromptRenderer, RenderedPrompt


class PromptBuilder:
    """Build rendered prompts from normalized context models."""

    def __init__(
        self,
        *,
        registry: PromptRegistry | None = None,
        renderer: PromptRenderer | None = None,
    ) -> None:
        """Create a prompt builder."""
        self._registry = registry or PromptRegistry()
        self._renderer = renderer or PromptRenderer()

    def build_album_summary_prompt(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> RenderedPrompt:
        """Build an album summary prompt from AlbumContext."""
        template = self._registry.get(prompt_name)
        variables = {
            "artist": context.plex.artist,
            "album": context.plex.album,
            "genres": _first_list(context.musicbrainz.genres, context.plex.genres)
            or ["No genres available"],
            "release_date": context.musicbrainz.release_date or str(context.plex.year or "Unknown"),
            "wikipedia_extract": context.wikipedia.extract or "No Wikipedia extract available.",
            "current_summary": context.plex.summary or "No current Plex summary.",
            "language": "de",
        }
        return self._renderer.render(
            name=template.name,
            version=template.version,
            template=template.template,
            variables=variables,
        )

    def build_artist_summary_prompt(self, context: ArtistContext) -> RenderedPrompt:
        """Build an artist summary prompt from ArtistContext."""
        template = self._registry.get("artist_summary")
        variables = {
            "artist": context.plex.artist,
            "album": "",
            "genres": _first_list(context.musicbrainz.genres, context.plex.genres)
            or ["No genres available"],
            "release_date": context.musicbrainz.begin_date or "",
            "wikipedia_extract": context.wikipedia.extract or "No reference extract available.",
            "current_summary": context.plex.summary or "No current summary.",
            "language": context.wikipedia.language or "de",
        }
        return self._renderer.render(
            name=template.name,
            version=template.version,
            template=template.template,
            variables=variables,
        )


def _first_list(primary: list[str], fallback: list[str]) -> list[str]:
    """Return the first populated list."""
    return primary if primary else fallback
