"""Prompt construction from enrichment context."""

from __future__ import annotations

from logging import DEBUG, getLogger
from re import split, sub

from plex_music_enhancer.config import Settings
from plex_music_enhancer.editorial import ArtistEditorialComposer, EditorialComposer
from plex_music_enhancer.editorial.composer import render_editorial_context
from plex_music_enhancer.editorial.models import EditorialContext
from plex_music_enhancer.enrichment.models import AlbumContext, ArtistContext
from plex_music_enhancer.prompts.budget import PromptBudgetManager
from plex_music_enhancer.prompts.registry import PromptRegistry
from plex_music_enhancer.prompts.renderer import PromptRenderer, RenderedPrompt
from plex_music_enhancer.prompts.targets import (
    ARTIST_BIOGRAPHY_MAX_WORDS,
    ARTIST_BIOGRAPHY_MIN_WORDS,
)
from plex_music_enhancer.verification.models import VerifiedFact

ARTIST_WIKIPEDIA_EXTRACT_MAX_CHARS = 1_800
ARTIST_CURRENT_SUMMARY_MAX_CHARS = 1_500
ARTIST_CURRENT_SUMMARY_EXCERPT_MIN_CHARS = 500
ARTIST_CURRENT_SUMMARY_EXCERPT_MAX_CHARS = 900
ARTIST_WIKIPEDIA_KEEP_KEYWORDS = (
    "achievement",
    "award",
    "breakthrough",
    "career",
    "formed",
    "formation",
    "founded",
    "genre",
    "historical",
    "influence",
    "legacy",
    "milestone",
    "musical",
    "significance",
    "style",
    "auszeichnung",
    "bedeutung",
    "durchbruch",
    "einfluss",
    "erfolg",
    "gegründet",
    "gründung",
    "historisch",
    "karriere",
    "meilenstein",
    "musikalisch",
    "stil",
)
ARTIST_CURRENT_SUMMARY_KEEP_KEYWORDS = (
    "achievement",
    "breakthrough",
    "career-defining",
    "cultural impact",
    "historically important",
    "influence",
    "international",
    "legacy",
    "recognized",
    "significance",
    "wirkung",
    "bedeutung",
    "durchbruch",
    "einfluss",
    "erfolg",
    "international",
    "kulturell",
    "prägend",
    "werk",
)
ARTIST_CURRENT_SUMMARY_DROP_KEYWORDS = (
    "band member",
    "discography",
    "line-up",
    "personnel",
    "song-by-song",
    "tour",
    "track-by-track",
    "besetzung",
    "diskografie",
    "mitglieder",
    "titel für titel",
    "tournee",
)
ARTIST_WIKIPEDIA_DROP_KEYWORDS = (
    "concert",
    "detailed chronology",
    "discography",
    "divorce",
    "personal life",
    "relationship",
    "song-by-song",
    "tour",
    "track-by-track",
    "konzert",
    "privatleben",
    "titel für titel",
    "tournee",
)
LOGGER = getLogger(__name__)
LOW_NARRATIVE_VERIFIED_CATEGORIES = {
    "aliases",
    "birth_name",
    "genres",
    "styles",
}


class PromptBuilder:
    """Build rendered prompts from normalized context models."""

    def __init__(
        self,
        *,
        registry: PromptRegistry | None = None,
        renderer: PromptRenderer | None = None,
        editorial_composer: EditorialComposer | None = None,
        artist_editorial_composer: ArtistEditorialComposer | None = None,
        budget_manager: PromptBudgetManager | None = None,
    ) -> None:
        """Create a prompt builder."""
        self._registry = registry or PromptRegistry()
        self._renderer = renderer or PromptRenderer()
        self._editorial_composer = editorial_composer or EditorialComposer()
        self._artist_editorial_composer = artist_editorial_composer or ArtistEditorialComposer()
        self._budget_manager = budget_manager or PromptBudgetManager(
            Settings().ai.max_prompt_characters
        )

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
        return self._budget_manager.fit(
            self._renderer.render(
                name=template.name,
                version=template.version,
                template=template.template,
                variables=variables,
            )
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
            "wikipedia_extract": _artist_wikipedia_extract(context.wikipedia.extract)
            or "No reference extract available.",
            "current_summary": _artist_current_summary(context.plex.summary)
            or "No current summary.",
            "language": context.wikipedia.language or "de",
            "minimum_words": ARTIST_BIOGRAPHY_MIN_WORDS,
            "maximum_words": ARTIST_BIOGRAPHY_MAX_WORDS,
            "additional_metadata": _artist_additional_metadata(
                context,
                composer=self._artist_editorial_composer,
            ),
        }
        rendered = self._renderer.render(
            name=template.name,
            version=template.version,
            template=template.template,
            variables=variables,
        )
        prompt = self._budget_manager.fit(rendered)
        _log_artist_prompt_diagnostics(prompt)
        return prompt


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
    """Return structured artist facts for prompt context."""
    selected_composer = composer or ArtistEditorialComposer()
    return _render_artist_structured_context(context, selected_composer.compose_artist(context))


def _log_artist_prompt_diagnostics(prompt: RenderedPrompt) -> None:
    """Log artist prompt diagnostics when debug logging is enabled."""
    if not LOGGER.isEnabledFor(DEBUG):
        return

    section_sizes = _prompt_section_sizes(prompt)
    largest_contributors = sorted(
        section_sizes.items(),
        key=lambda item: (-item[1], item[0]),
    )[:5]
    duplicate_content = _duplicate_prompt_content(prompt)
    LOGGER.debug(
        "Artist prompt diagnostics: total_characters=%s estimated_tokens=%s "
        "section_sizes=%s largest_contributors=%s duplicate_content=%s",
        len(prompt.rendered_text),
        _estimated_tokens(prompt.rendered_text),
        section_sizes,
        largest_contributors,
        duplicate_content,
    )


def _prompt_section_sizes(prompt: RenderedPrompt) -> dict[str, int]:
    """Return character sizes for rendered prompt sections and variables."""
    sections: dict[str, int] = {
        f"variable:{name}": len(value) for name, value in sorted(prompt.variables.items())
    }
    sections.update(_rendered_section_sizes(prompt.rendered_text))
    return sections


def _rendered_section_sizes(text: str) -> dict[str, int]:
    """Return approximate section sizes from the rendered Markdown prompt."""
    sections: dict[str, list[str]] = {}
    current = "section:preamble"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            current = f"section:{stripped.removeprefix('# ').strip()}"
        elif stripped.endswith(":") and not stripped.startswith(
            ("-", "1.", "2.", "3.", "4.", "5.", "6.")
        ):
            current = f"section:{stripped.rstrip(':')}"
        sections.setdefault(current, []).append(line)
    return {name: len("\n".join(lines)) for name, lines in sections.items()}


def _duplicate_prompt_content(prompt: RenderedPrompt) -> list[str]:
    """Return normalized duplicate lines detected in prompt variables."""
    counts: dict[str, tuple[str, int]] = {}
    for value in prompt.variables.values():
        for line in value.splitlines():
            text = line.strip()
            if len(text) < 12:
                continue
            key = sub(r"\s+", " ", text.casefold())
            original, count = counts.get(key, (text, 0))
            counts[key] = (original, count + 1)
    return [original for original, count in counts.values() if count > 1]


def _estimated_tokens(text: str) -> int:
    """Return a deterministic rough token estimate."""
    return max(1, round(len(text) / 4))


def _render_artist_structured_context(
    context: ArtistContext,
    editorial: EditorialContext,
) -> str:
    """Render artist context as compact factual sections."""
    lines: list[str] = []
    _append_structured_value(lines, "Artist", context.full_name or context.plex.artist)
    _append_structured_list(
        lines,
        "Genres",
        _dedupe_list(_first_list(context.genres, context.musicbrainz.genres, context.plex.genres)),
    )
    _append_structured_value(
        lines, "Active years", context.active_years or context.discogs.active_years
    )
    _append_structured_list(
        lines, "Members", _dedupe_list(context.members or context.discogs.members)
    )
    _append_structured_value(
        lines,
        "Origin",
        context.origin
        or context.plex.country
        or context.nationality
        or context.musicbrainz.country,
    )
    _append_structured_list(
        lines,
        "Career highlights",
        _dedupe_list(
            [
                *context.milestones,
                *_fact_values(
                    editorial.career_context, skipped_topics={"active_years", "identity"}
                ),
            ]
        ),
    )
    _append_structured_list(lines, "Most notable works", _dedupe_list(context.notable_albums))
    _append_structured_list(lines, "Awards", _dedupe_list(context.awards))
    _append_structured_list(
        lines,
        "Historical significance",
        _dedupe_list(
            [
                *context.influenced_artists,
                *_fact_values(editorial.historical_context),
                *_fact_values(editorial.legacy_context),
            ]
        ),
    )
    _append_structured_verified(lines, "Verified facts", editorial.verified_facts)
    _append_structured_list(
        lines,
        "Avoid topics",
        ["unsupported claims not present anywhere in the supplied context"],
    )
    return "\n".join(lines) if lines else "No structured artist facts available."


def _fact_values(facts: object, *, skipped_topics: set[str] | None = None) -> list[str]:
    """Return compact fact texts from editorial facts."""
    if not isinstance(facts, list):
        return []
    skipped = {"aliases", "genres", *(skipped_topics or set())}
    return [
        fact.text
        for fact in facts
        if hasattr(fact, "text")
        and hasattr(fact, "topic")
        and fact.topic not in skipped
        and isinstance(fact.text, str)
        and len(fact.text) <= 240
    ]


def _append_structured_value(lines: list[str], label: str, value: str | None) -> None:
    """Append one compact scalar section."""
    if value:
        lines.append(f"{label}: {value}")


def _append_structured_list(lines: list[str], label: str, values: list[str] | None) -> None:
    """Append one compact list section."""
    if values:
        lines.append(f"{label}: {', '.join(values)}")


def _append_structured_verified(
    lines: list[str],
    label: str,
    facts: list[VerifiedFact] | None,
) -> None:
    """Append verified facts in compact deterministic form."""
    if not facts:
        return
    selected = [fact for fact in facts if fact.category not in LOW_NARRATIVE_VERIFIED_CATEGORIES]
    if not selected:
        return
    rendered = [
        (
            f"{fact.category}={fact.value} "
            f"({fact.confidence_score:.2f}; {', '.join(fact.supporting_sources) or 'none'})"
        )
        for fact in selected
    ]
    lines.append(f"{label}: {'; '.join(rendered)}")


def _dedupe_list(values: list[str]) -> list[str]:
    """Return deterministic case-insensitive unique values."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _artist_wikipedia_extract(extract: str | None) -> str | None:
    """Return a focused Wikipedia excerpt for artist biography prompts."""
    if not extract:
        return None

    sentences = _reference_sentences(extract)
    selected = [sentence for sentence in sentences if _keep_artist_reference_sentence(sentence)]
    if not selected:
        selected = [
            sentence for sentence in sentences if not _drop_artist_reference_sentence(sentence)
        ]
    if not selected:
        return None

    return _join_to_budget(selected, ARTIST_WIKIPEDIA_EXTRACT_MAX_CHARS)


def _artist_current_summary(summary: str | None) -> str | None:
    """Return a compact excerpt from the existing artist summary."""
    if not summary:
        return None
    if len(summary) <= ARTIST_CURRENT_SUMMARY_MAX_CHARS:
        return summary

    paragraphs = _reference_paragraphs(summary)
    selected = [
        paragraph for paragraph in paragraphs if _keep_artist_current_summary_paragraph(paragraph)
    ]
    has_informative_selection = bool(selected)
    if not selected:
        selected = _fallback_current_summary_paragraphs(paragraphs)
    if has_informative_selection:
        selected = _extend_current_summary_selection(selected, paragraphs)
    return _join_to_budget(selected, ARTIST_CURRENT_SUMMARY_EXCERPT_MAX_CHARS)


def _reference_paragraphs(text: str) -> list[str]:
    """Split prose into deterministic paragraph-like chunks."""
    return [
        sub(r"\s+", " ", paragraph).strip()
        for paragraph in split(r"\n\s*\n", text)
        if paragraph.strip()
    ]


def _keep_artist_current_summary_paragraph(paragraph: str) -> bool:
    """Return whether a Plex biography paragraph has narrative value."""
    normalized = paragraph.casefold()
    has_keep_signal = any(keyword in normalized for keyword in ARTIST_CURRENT_SUMMARY_KEEP_KEYWORDS)
    has_drop_signal = any(keyword in normalized for keyword in ARTIST_CURRENT_SUMMARY_DROP_KEYWORDS)
    return has_keep_signal and not has_drop_signal


def _drop_artist_current_summary_paragraph(paragraph: str) -> bool:
    """Return whether a Plex biography paragraph should be avoided in excerpts."""
    normalized = paragraph.casefold()
    return any(keyword in normalized for keyword in ARTIST_CURRENT_SUMMARY_DROP_KEYWORDS)


def _fallback_current_summary_paragraphs(paragraphs: list[str]) -> list[str]:
    """Prefer the beginning and conclusion when no better narrative signal exists."""
    if not paragraphs:
        return []
    if len(paragraphs) == 1:
        return paragraphs
    return [paragraphs[0], paragraphs[-1]]


def _extend_current_summary_selection(
    selected: list[str],
    paragraphs: list[str],
) -> list[str]:
    """Extend a short excerpt deterministically without repeating paragraphs."""
    result = _dedupe_list(selected)
    if len(" ".join(result)) >= ARTIST_CURRENT_SUMMARY_EXCERPT_MIN_CHARS:
        return result

    candidates = [
        paragraph
        for paragraph in [*paragraphs[:4], *paragraphs[-4:]]
        if not _drop_artist_current_summary_paragraph(paragraph)
    ]
    for paragraph in candidates:
        result = _dedupe_list([*result, paragraph])
        if len(_join_to_budget(result, ARTIST_CURRENT_SUMMARY_EXCERPT_MAX_CHARS)) >= (
            ARTIST_CURRENT_SUMMARY_EXCERPT_MIN_CHARS
        ):
            break
    return result


def _reference_sentences(text: str) -> list[str]:
    """Split prose into deterministic sentence-like chunks."""
    normalized = sub(r"\s+", " ", text).strip()
    return [
        sentence.strip() for sentence in split(r"(?<=[.!?])\s+", normalized) if sentence.strip()
    ]


def _keep_artist_reference_sentence(sentence: str) -> bool:
    """Return whether a Wikipedia sentence is useful artist summary context."""
    normalized = sentence.casefold()
    has_keep_signal = any(keyword in normalized for keyword in ARTIST_WIKIPEDIA_KEEP_KEYWORDS)
    return has_keep_signal and not _drop_artist_reference_sentence(sentence)


def _drop_artist_reference_sentence(sentence: str) -> bool:
    """Return whether a Wikipedia sentence is too detailed for prompt context."""
    normalized = sentence.casefold()
    return any(keyword in normalized for keyword in ARTIST_WIKIPEDIA_DROP_KEYWORDS)


def _join_to_budget(sentences: list[str], max_characters: int) -> str:
    """Join sentences without cutting in the middle of a sentence."""
    result: list[str] = []
    size = 0
    for sentence in sentences:
        next_size = size + len(sentence) + (1 if result else 0)
        if next_size > max_characters:
            break
        result.append(sentence)
        size = next_size
    return " ".join(result) if result else sentences[0][:max_characters].rstrip()


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
