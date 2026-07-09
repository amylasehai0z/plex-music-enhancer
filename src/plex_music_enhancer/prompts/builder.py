"""Prompt construction from enrichment context."""

from __future__ import annotations

from plex_music_enhancer.editorial import ArtistEditorialComposer, EditorialComposer
from plex_music_enhancer.editorial.composer import render_editorial_context
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
        editorial_composer: EditorialComposer | None = None,
        artist_editorial_composer: ArtistEditorialComposer | None = None,
    ) -> None:
        """Create a prompt builder."""
        self._registry = registry or PromptRegistry()
        self._renderer = renderer or PromptRenderer()
        self._editorial_composer = editorial_composer or EditorialComposer()
        self._artist_editorial_composer = artist_editorial_composer or ArtistEditorialComposer()

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
            "additional_metadata": _album_additional_metadata(
                context,
                composer=self._editorial_composer,
            ),
        }
        return self._renderer.render(
            name=template.name,
            version=template.version,
            template=template.template,
            variables=variables,
        )

    def build_artist_summary_prompt(self, context: ArtistContext) -> RenderedPrompt:
        """Build an artist summary prompt from ArtistContext."""
        template = self._registry.get("artist_biography")
        variables = {
            "artist": context.plex.artist,
            "album": "",
            "genres": _first_list(context.genres, context.musicbrainz.genres, context.plex.genres)
            or ["No genres available"],
            "release_date": context.musicbrainz.begin_date or "",
            "wikipedia_extract": context.wikipedia.extract or "No reference extract available.",
            "current_summary": context.plex.summary or "No current summary.",
            "language": context.wikipedia.language or "de",
            "additional_metadata": _artist_additional_metadata(
                context,
                composer=self._artist_editorial_composer,
            ),
        }
        return self._renderer.render(
            name=template.name,
            version=template.version,
            template=template.template,
            variables=variables,
        )


def _first_list(*lists: list[str]) -> list[str]:
    """Return the first populated list."""
    for values in lists:
        if values:
            return values
    return []


def _album_additional_metadata(
    context: AlbumContext,
    *,
    composer: EditorialComposer | None = None,
) -> str:
    """Return editorial album guidance for prompt context."""
    selected_composer = composer or EditorialComposer()
    return render_editorial_context(selected_composer.compose_album(context))


def _artist_additional_metadata(
    context: ArtistContext,
    *,
    composer: ArtistEditorialComposer | None = None,
) -> str:
    """Return editorial artist guidance for prompt context."""
    selected_composer = composer or ArtistEditorialComposer()
    return render_editorial_context(selected_composer.compose_artist(context))


def _legacy_album_additional_metadata(context: AlbumContext) -> str:
    """Return legacy structured album metadata for compatibility tests and debugging."""
    lines: list[str] = []
    genres = context.genres or _first_list(context.musicbrainz.genres, context.plex.genres)
    release_date = context.release_date or context.musicbrainz.release_date
    if release_date is None and context.plex.year is not None:
        release_date = str(context.plex.year)

    _append_list(lines, "Producers", context.producers)
    _append_list(lines, "Executive producers", context.executive_producers)
    _append_list(lines, "Composers", context.composers)
    _append_list(lines, "Lyricists", context.lyricists)
    _append_list(lines, "Arrangers", context.arrangers)
    _append_list(lines, "Orchestrators", context.orchestrators)
    _append_list(lines, "Conductors", context.conductors)
    _append_list(lines, "Mixing engineers", context.mixing_engineers)
    _append_list(lines, "Mastering engineers", context.mastering_engineers)
    _append_list(lines, "Sound engineers", context.sound_engineers)
    _append_list(lines, "Discogs producers", context.discogs.producer)
    _append_list(lines, "Discogs engineers", context.discogs.engineer)
    _append_list(lines, "Discogs mastering", context.discogs.mastering)
    _append_list(lines, "Discogs mixed by", context.discogs.mixed_by)
    _append_list(lines, "Labels", context.labels)
    _append_list(lines, "Discogs labels", context.discogs.labels)
    _append_value(lines, "Catalog number", context.catalog_number)
    _append_list(lines, "Discogs catalog numbers", context.discogs.catalog_numbers)
    _append_value(lines, "Barcode", context.barcode)
    _append_value(lines, "Release country", context.release_country)
    _append_value(lines, "Recording period", context.recording_period)
    _append_value(lines, "Recording location", context.recording_location)
    _append_value(lines, "Discogs recording location", context.discogs.recording_location)
    _append_value(lines, "Discogs recording dates", context.discogs.recording_dates)
    _append_list(lines, "Studios", context.studios)
    _append_list(lines, "Discogs formats", context.discogs.formats)
    _append_list(lines, "Genres", genres)
    _append_list(lines, "Secondary genres", context.secondary_genres)
    _append_list(lines, "Tags", context.tags)
    _append_list(lines, "Last.fm artist tags", context.lastfm_artist.tags)
    _append_list(lines, "Last.fm album tags", context.lastfm.tags)
    _append_list(lines, "Community tags", _dedupe(context.lastfm_artist.tags + context.lastfm.tags))
    _append_value(lines, "Release date", release_date)
    _append_value(lines, "First release date", context.first_release_date)
    _append_list(lines, "Chart positions", context.chart_positions)
    _append_list(lines, "Certifications", context.certifications)
    _append_list(lines, "Notable singles", context.notable_singles)
    _append_list(lines, "Guest musicians", context.guest_musicians)
    _append_list(lines, "Discogs guest musicians", context.discogs.guest_musicians)
    _append_list(lines, "Discogs personnel", context.discogs.personnel)
    _append_list(lines, "Discogs credits", context.discogs.credits)
    _append_value(lines, "Discogs notes", context.discogs.notes)
    _append_list(lines, "Featured artists", context.featured_artists)
    _append_list(lines, "Orchestras", context.orchestras)
    _append_list(lines, "Choirs", context.choirs)
    _append_list(lines, "Publishers", context.publishers)
    _append_value(lines, "Artist history", context.artist_history)
    _append_value(lines, "Last.fm artist biography", context.lastfm_artist.biography)
    _append_value(lines, "Last.fm artist short biography", context.lastfm_artist.short_biography)
    _append_list(lines, "Last.fm similar artists", context.lastfm_artist.similar_artists)
    _append_value(lines, "Career phase", context.career_phase)
    _append_value(lines, "Discography position", context.discography_position)
    _append_number(lines, "Album sequence number", context.album_sequence_number)
    _append_related_album(
        lines,
        "Previous album",
        context.previous_album,
        context.previous_album_year,
    )
    _append_related_album(lines, "Next album", context.next_album, context.next_album_year)
    _append_value(lines, "Years active", context.years_active)
    _append_list(lines, "Current lineup", context.current_lineup)
    _append_value(lines, "Lineup changes", context.lineup_changes)
    _append_value(lines, "Commercial peak", context.commercial_peak)
    _append_value(lines, "Genre evolution", context.genre_evolution)
    _append_list(lines, "Major influences", context.major_influences)
    _append_value(lines, "Historical context", context.historical_context)
    _append_flag(lines, "Debut album", context.is_debut_album)
    _append_flag(lines, "Comeback album", context.is_comeback_album)
    _append_flag(lines, "Final album", context.is_final_album)
    _append_flag(lines, "Live album", context.is_live_album)
    _append_flag(lines, "Compilation", context.is_compilation)
    _append_flag(lines, "Soundtrack", context.is_soundtrack)
    _append_number(lines, "Track count", context.track_count)
    _append_value(lines, "Total duration", context.total_duration)
    _append_value(lines, "Opening track", context.opening_track)
    _append_value(lines, "Closing track", context.closing_track)
    _append_value(lines, "Longest track", context.longest_track)
    _append_value(lines, "Shortest track", context.shortest_track)
    _append_list(lines, "Instrumental tracks", context.instrumental_tracks)
    _append_list(lines, "Cover versions", context.cover_versions)
    _append_list(lines, "Notable tracks", context.notable_tracks)
    _append_list(lines, "Singles", context.singles)
    _append_list(lines, "Hit singles", context.hit_singles)
    _append_list(lines, "Promotional singles", context.promotional_singles)
    _append_flag(lines, "Concept album", context.concept_album)
    _append_flag(lines, "Continuous mix", context.continuous_mix)
    _append_list(lines, "Album highlights", context.album_highlights)
    _append_value(lines, "Signature song", context.signature_song)
    _append_value(lines, "Best-known song", context.best_known_song)
    _append_list(lines, "Stylistic highlights", context.stylistic_highlights)
    _append_list(lines, "Experimental elements", context.experimental_elements)
    _append_list(lines, "Recurring themes", context.recurring_themes)
    _append_value(lines, "Critical consensus", context.critical_consensus)
    _append_value(lines, "Commercial summary", context.commercial_summary)
    _append_value(lines, "Legacy summary", context.legacy_summary)
    _append_value(lines, "Last.fm album summary", context.lastfm.summary)
    _append_value(lines, "Last.fm album wiki", context.lastfm.wiki)
    _append_value(lines, "Last.fm URL", context.lastfm.url)
    _append_list(lines, "Knowledge graph", context.knowledge_graph.summaries)
    return "\n".join(lines) if lines else "No additional structured metadata supplied."


def _append_value(lines: list[str], label: str, value: str | None) -> None:
    """Append a scalar metadata line when populated."""
    if value:
        lines.append(f"{label}: {value}")


def _append_list(lines: list[str], label: str, values: list[str]) -> None:
    """Append a list metadata line when populated."""
    if values:
        lines.append(f"{label}: {', '.join(values)}")


def _append_number(lines: list[str], label: str, value: int | None) -> None:
    """Append a numeric metadata line when populated."""
    if value is not None:
        lines.append(f"{label}: {value}")


def _append_flag(lines: list[str], label: str, value: bool) -> None:
    """Append a boolean fact only when true."""
    if value:
        lines.append(f"{label}: yes")


def _append_related_album(
    lines: list[str],
    label: str,
    title: str | None,
    year: int | None,
) -> None:
    """Append a neighboring album line when populated."""
    if title is None:
        return
    suffix = f" ({year})" if year is not None else ""
    lines.append(f"{label}: {title}{suffix}")


def _dedupe(values: list[str]) -> list[str]:
    """Return values with case-insensitive duplicates removed."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = value.strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result
