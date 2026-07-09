"""Prompt engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from plex_music_enhancer.enrichment import (
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
from plex_music_enhancer.knowledge.models import KnowledgeGraph
from plex_music_enhancer.prompts import PromptBuilder, PromptLoader, PromptRegistry, PromptRenderer


def test_prompt_registry_discovers_loads_and_caches_templates(tmp_path: Path) -> None:
    """PromptRegistry should discover, validate, and cache Markdown templates."""
    template_path = tmp_path / "album_summary.md"
    template_path.write_text("Artist: {{artist}}\nAlbum: {{album}}\n", encoding="utf-8")
    registry = PromptRegistry(PromptLoader(tmp_path))

    first = registry.get("album_summary")
    template_path.write_text("Changed {{artist}}\n", encoding="utf-8")
    second = registry.get("album_summary")

    assert registry.discover() == ["album_summary"]
    assert first == second
    assert first.name == "album_summary"
    assert first.version == "1.1"
    assert first.placeholders == {"artist", "album"}


def test_prompt_registry_rejects_unsupported_placeholders(tmp_path: Path) -> None:
    """PromptRegistry should reject template variables the engine does not support."""
    (tmp_path / "bad.md").write_text("Unknown: {{label}}\n", encoding="utf-8")
    registry = PromptRegistry(PromptLoader(tmp_path))

    with pytest.raises(ValueError, match="unsupported placeholders"):
        registry.get("bad")


def test_prompt_renderer_substitutes_variables_and_preserves_formatting() -> None:
    """PromptRenderer should replace placeholders without changing Markdown formatting."""
    renderer = PromptRenderer()
    template = "# Title\n\nArtist: {{artist}}\nGenres:\n- {{genres}}\n"

    rendered = renderer.render(
        name="album_summary",
        version="1.0",
        template=template,
        variables={"artist": "Nina Simone", "genres": ["Jazz", "Soul"]},
    )

    assert rendered.rendered_text == "# Title\n\nArtist: Nina Simone\nGenres:\n- Jazz, Soul\n"
    assert rendered.variables == {"artist": "Nina Simone", "genres": "Jazz, Soul"}
    assert rendered.template == template


def test_prompt_renderer_fails_on_missing_required_variables() -> None:
    """PromptRenderer should fail when required template variables are absent."""
    renderer = PromptRenderer()

    with pytest.raises(ValueError, match="album"):
        renderer.render(
            name="album_summary",
            version="1.0",
            template="{{artist}} - {{album}}",
            variables={"artist": "Nina Simone"},
        )


def test_prompt_builder_renders_album_context(tmp_path: Path) -> None:
    """PromptBuilder should render album prompts from AlbumContext."""
    (tmp_path / "album_summary.md").write_text(
        "Artist: {{artist}}\n"
        "Album: {{album}}\n"
        "Genres: {{genres}}\n"
        "Date: {{release_date}}\n"
        "Wiki: {{wikipedia_extract}}\n"
        "Current: {{current_summary}}\n"
        "Additional: {{additional_metadata}}\n"
        "Language: {{language}}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(registry=PromptRegistry(PromptLoader(tmp_path)))

    prompt = builder.build_album_summary_prompt(_album_context())

    assert prompt.name == "album_summary"
    assert prompt.version == "1.1"
    assert "Artist: Nina Simone" in prompt.rendered_text
    assert "Album: Pastel Blues" in prompt.rendered_text
    assert "Genres: jazz" in prompt.rendered_text
    assert "Date: 1965-10" in prompt.rendered_text
    assert "Wiki: Wikipedia summary" in prompt.rendered_text
    assert "Current: Current Plex summary" in prompt.rendered_text
    assert "Additional: Opening focus: Pastel Blues" in prompt.rendered_text
    assert "Most important facts:" in prompt.rendered_text
    assert "Language: de" in prompt.rendered_text


def test_prompt_builder_passes_editorial_album_context_to_prompt(tmp_path: Path) -> None:
    """PromptBuilder should expose composed editorial guidance instead of raw metadata dumps."""
    (tmp_path / "album_summary.md").write_text(
        "Additional:\n{{additional_metadata}}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(registry=PromptRegistry(PromptLoader(tmp_path)))
    context = _album_context().model_copy(
        update={
            "producers": ["Hal Mooney"],
            "executive_producers": ["Executive Example"],
            "composers": ["Nina Simone"],
            "lyricists": ["Oscar Brown Jr."],
            "arrangers": ["Horace Ott"],
            "conductors": ["Conductor Example"],
            "mixing_engineers": ["Mix Engineer"],
            "mastering_engineers": ["Master Engineer"],
            "discogs": DiscogsAlbumContext(
                labels=["Philips Records"],
                catalog_numbers=["DG-001"],
                producer=["Discogs Producer"],
                engineer=["Discogs Engineer"],
                mastering=["Discogs Mastering"],
                mixed_by=["Discogs Mixer"],
                recording_location="Discogs Studio",
                recording_dates="1965",
                formats=["Vinyl, LP"],
                personnel=["Discogs Guitarist"],
                guest_musicians=["Discogs Guest"],
                credits=["Discogs Unknown (Liner Notes)"],
                notes="Discogs release notes.",
            ),
            "lastfm": LastFMAlbumContext(
                summary="Last.fm album summary.",
                wiki="Last.fm album background.",
                tags=["vocal jazz", "soul"],
                url="https://www.last.fm/music/Nina+Simone/Pastel+Blues",
            ),
            "lastfm_artist": LastFMArtistContext(
                biography="Last.fm artist biography.",
                short_biography="Last.fm short biography.",
                tags=["jazz singer", "soul"],
                similar_artists=["Billie Holiday"],
            ),
            "labels": ["Philips Records"],
            "catalog_number": "PHS 600-187",
            "barcode": "123456789012",
            "release_country": "US",
            "recording_period": "1964-1965",
            "studios": ["RCA Studio B"],
            "notable_singles": ["Sinnerman"],
            "guest_musicians": ["Guest Example"],
            "featured_artists": ["Featured Example"],
            "orchestras": ["Studio Orchestra"],
            "publishers": ["Publishing Example"],
        }
    )

    prompt = builder.build_album_summary_prompt(context)

    additional = prompt.variables["additional_metadata"]
    assert "Opening focus: Pastel Blues; by Nina Simone" in additional
    assert "Recommended story order:" in additional
    assert "Most important facts:" in additional
    assert "Verified facts:" in additional
    assert "Probable facts:" in additional
    assert "Weak facts:" in additional
    assert "Production context:" in additional
    assert "Producer: Hal Mooney" in additional
    assert "Producer: Discogs Producer" in additional
    assert "Label: Philips Records" in additional
    assert "Recording context:" in additional
    assert "Discogs Studio" in additional
    assert "Musical style:" in additional
    assert "Community style tags: jazz singer, soul, vocal jazz" in additional
    assert "Writing guidance:" in additional
    assert "avoid isolated fact lists" in additional
    assert "Avoid topics:" in additional
    assert "Discogs producers:" not in additional
    assert "Last.fm artist tags:" not in additional


def test_prompt_builder_omits_missing_rich_album_metadata_cleanly(tmp_path: Path) -> None:
    """PromptBuilder should not render empty optional fields as literal placeholders."""
    (tmp_path / "album_summary.md").write_text(
        "Additional:\n{{additional_metadata}}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(registry=PromptRegistry(PromptLoader(tmp_path)))
    context = _album_context().model_copy(
        update={
            "genres": [],
            "release_date": None,
            "musicbrainz": MusicBrainzAlbumContext(confidence=0),
            "plex": _album_context().plex.model_copy(update={"genres": [], "year": None}),
        }
    )

    prompt = builder.build_album_summary_prompt(context)

    assert "Opening focus:" in prompt.rendered_text
    assert "Producers:" not in prompt.rendered_text
    assert "Labels:" not in prompt.rendered_text
    assert "Composers:" not in prompt.rendered_text
    assert "Executive producers:" not in prompt.rendered_text
    assert "Mixing engineers:" not in prompt.rendered_text
    assert "Career phase:" not in prompt.rendered_text
    assert "Previous album:" not in prompt.rendered_text
    assert "Track count:" not in prompt.rendered_text
    assert "Opening track:" not in prompt.rendered_text
    assert "Concept album:" not in prompt.rendered_text
    assert "Do not invent missing context:" in prompt.rendered_text
    assert "None" not in prompt.rendered_text


def test_prompt_builder_passes_track_editorial_context_to_prompt(tmp_path: Path) -> None:
    """PromptBuilder should expose optional track-level and editorial context."""
    (tmp_path / "album_summary.md").write_text(
        "Additional:\n{{additional_metadata}}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(registry=PromptRegistry(PromptLoader(tmp_path)))
    context = _album_context().model_copy(
        update={
            "track_count": 10,
            "total_duration": "42:17",
            "opening_track": "Opening Song",
            "closing_track": "Finale",
            "longest_track": "Long Suite",
            "shortest_track": "Interlude",
            "instrumental_tracks": ["Interlude"],
            "cover_versions": ["Classic Standard"],
            "notable_tracks": ["Opening Song", "Long Suite"],
            "singles": ["Lead Single"],
            "hit_singles": ["Lead Single"],
            "promotional_singles": ["Promo Track"],
            "concept_album": True,
            "continuous_mix": True,
            "album_highlights": ["suite-like second side"],
            "signature_song": "Lead Single",
            "best_known_song": "Lead Single",
            "stylistic_highlights": ["orchestral synth textures"],
            "experimental_elements": ["continuous transitions"],
            "recurring_themes": ["memory", "distance"],
            "critical_consensus": "Praised for its cohesive atmosphere.",
            "commercial_summary": "The lead single became the album's best-known track.",
            "legacy_summary": "Later cited for its integrated album structure.",
        }
    )

    prompt = builder.build_album_summary_prompt(context)

    assert "Notable tracks: Opening Song, Long Suite, suite-like second side" in (
        prompt.rendered_text
    )
    assert "Musical style:" in prompt.rendered_text
    assert "orchestral synth textures" in prompt.rendered_text
    assert "Lyrical context:" in prompt.rendered_text
    assert "Recurring theme: memory" in prompt.rendered_text
    assert "Legacy context:" in prompt.rendered_text
    assert "Praised for its cohesive atmosphere." in prompt.rendered_text
    assert "The lead single became the album's best-known track." in prompt.rendered_text
    assert "Later cited for its integrated album structure." in prompt.rendered_text
    assert "Track count:" not in prompt.rendered_text


def test_prompt_builder_passes_knowledge_graph_summaries_to_prompt(tmp_path: Path) -> None:
    """PromptBuilder should expose graph summaries through existing metadata context."""
    (tmp_path / "album_summary.md").write_text(
        "Additional:\n{{additional_metadata}}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(registry=PromptRegistry(PromptLoader(tmp_path)))
    context = _album_context().model_copy(
        update={
            "knowledge_graph": KnowledgeGraph(
                summaries=[
                    "Producer relationship: Hal Mooney.",
                    "Label history: released through Philips Records.",
                ]
            )
        }
    )

    prompt = builder.build_album_summary_prompt(context)

    assert "Producer relationship: Hal Mooney." in prompt.rendered_text
    assert "Label history: released through Philips Records." in prompt.rendered_text


def test_prompt_builder_passes_career_context_to_prompt(tmp_path: Path) -> None:
    """PromptBuilder should expose optional career and discography context."""
    (tmp_path / "album_summary.md").write_text(
        "Additional:\n{{additional_metadata}}\n",
        encoding="utf-8",
    )
    builder = PromptBuilder(registry=PromptRegistry(PromptLoader(tmp_path)))
    context = _album_context().model_copy(
        update={
            "artist_history": "A long-running German synth-pop project.",
            "career_phase": "commercial peak",
            "discography_position": "3. studio album in available discography",
            "album_sequence_number": 3,
            "previous_album": "Previous Record",
            "previous_album_year": 1984,
            "next_album": "Next Record",
            "next_album_year": 1987,
            "years_active": "1979-present",
            "current_lineup": ["Artist One", "Artist Two"],
            "lineup_changes": "Recorded after a lineup change.",
            "commercial_peak": "International breakthrough period",
            "genre_evolution": "Shifted from minimal synth-pop toward orchestral pop.",
            "major_influences": ["synth-pop", "new wave"],
            "historical_context": "Released during a major wave of German pop exports.",
            "is_debut_album": False,
            "is_comeback_album": True,
            "is_final_album": False,
            "is_live_album": False,
            "is_compilation": False,
            "is_soundtrack": False,
        }
    )

    prompt = builder.build_album_summary_prompt(context)

    assert "Career context:" in prompt.rendered_text
    assert "commercial peak" in prompt.rendered_text
    assert "3. studio album in available discography" in prompt.rendered_text
    assert "Previous album: Previous Record (1984)" in prompt.rendered_text
    assert "Next album: Next Record (1987)" in prompt.rendered_text
    assert "Career placement" in prompt.rendered_text
    assert "Genre evolution: Shifted from minimal synth-pop toward orchestral pop." in (
        prompt.rendered_text
    )
    assert "Historical context: Released during a major wave of German pop exports." in (
        prompt.rendered_text
    )
    assert "Album sequence number:" not in prompt.rendered_text


def test_prompt_builder_renders_album_translate_and_improve_prompts() -> None:
    """PromptBuilder should render specialized album rewrite prompts."""
    builder = PromptBuilder()

    translated = builder.build_album_summary_prompt(
        _album_context(),
        prompt_name="album_translate",
    )
    improved = builder.build_album_summary_prompt(
        _album_context(),
        prompt_name="album_improve",
    )

    assert translated.name == "album_translate"
    assert "Translate the current Plex album summary" in translated.rendered_text
    assert "Translate meaning, not wording" in translated.rendered_text
    assert "Preserve every factual statement exactly" in translated.rendered_text
    assert "natural German" in translated.rendered_text
    assert "Preserve track information, singles" in translated.rendered_text
    assert "Current Plex summary" in translated.rendered_text
    assert "Current Plex summary" in translated.variables["current_summary"]
    assert improved.name == "album_improve"
    assert "Improve the existing German Plex album summary" in improved.rendered_text
    assert "Remove repetition" in improved.rendered_text
    assert "Improve readability, transitions, rhythm, and paragraph flow" in improved.rendered_text
    assert "Preserve every factual statement" in improved.rendered_text
    assert "Preserve track information, singles" in improved.rendered_text


def test_prompt_builder_renders_artist_biography_prompt() -> None:
    """PromptBuilder should expose artist editorial context to biography prompts."""
    builder = PromptBuilder()

    prompt = builder.build_artist_summary_prompt(_artist_context())

    assert prompt.name == "artist_biography"
    assert "German music encyclopedia biography" in prompt.rendered_text
    assert "Additional verified artist context" in prompt.rendered_text
    assert "Recommended story order:" in prompt.rendered_text
    assert "Career context:" in prompt.rendered_text
    assert "Musical style:" in prompt.rendered_text
    assert "Verified facts:" in prompt.rendered_text
    assert "Never resolve conflicting facts by guessing" in prompt.rendered_text
    assert "Never invent awards, collaborations" in prompt.rendered_text
    assert prompt.variables["artist"] == "Nina Simone"
    assert "Opening focus: Nina Simone" in prompt.variables["additional_metadata"]


def test_default_album_prompt_contains_knowledge_enrichment_sections() -> None:
    """Default album prompt should guide encyclopedia-style knowledge enrichment."""
    builder = PromptBuilder()

    prompt = builder.build_album_summary_prompt(_album_context())

    assert "concise German music encyclopedia article" in prompt.rendered_text
    assert "approximately 80-120 words" in prompt.rendered_text
    assert "coherent story" in prompt.rendered_text
    assert "Musikexpress" in prompt.rendered_text
    assert "Do not add headings, labels, or sections" in prompt.rendered_text
    assert "Introduction: release date, artist, verified historical context" in (
        prompt.rendered_text
    )
    assert "Career context: career phase, discography position" in prompt.rendered_text
    assert "previous album, next album, stylistic" in prompt.rendered_text
    assert "Musical style: genres, stylistic contrasts" in prompt.rendered_text
    assert "Production: producer, label, recording context" in prompt.rendered_text
    assert "Notable characteristics: composers, lyricists" in prompt.rendered_text
    assert "opening or closing tracks" in prompt.rendered_text
    assert "Closing classification: a concise final sentence" in prompt.rendered_text
    assert "varied sentence openings" in prompt.rendered_text
    assert "Build a coherent narrative with natural transitions" in prompt.rendered_text
    assert "concise, information-rich encyclopedia language" in prompt.rendered_text
    assert "Use Last.fm community tags only as supporting context" in prompt.rendered_text
    assert "never present community" in prompt.rendered_text
    assert "Explain connections between facts" in prompt.rendered_text
    assert "Discuss track-level context as part of the album's musical narrative" in (
        prompt.rendered_text
    )
    assert "Additional verified album context" in prompt.rendered_text
    assert "never output metadata lists" in prompt.rendered_text
    assert "Avoid repeated sentence starts" in prompt.rendered_text
    assert "Do not use bullet lists or Markdown formatting" in prompt.rendered_text
    assert "Use only the supplied metadata" in prompt.rendered_text
    assert "Emphasize highly verified information" in prompt.rendered_text
    assert "Use probable facts carefully" in prompt.rendered_text
    assert "Never resolve conflicting facts by guessing" in prompt.rendered_text
    assert "Never invent missing facts" in prompt.rendered_text
    assert "Avoid presenting uncertain information as established fact" in (prompt.rendered_text)
    assert "Never invent chart positions, certifications, awards, reviews" in (prompt.rendered_text)
    assert "Never invent career milestones" in prompt.rendered_text
    assert "Never infer commercial peak or later influence" in prompt.rendered_text
    assert "Never invent singles, hit singles" in prompt.rendered_text
    assert "Never output a track listing" in prompt.rendered_text
    assert "If data is missing, omit that aspect silently" in prompt.rendered_text
    assert "Return only the finished German album article" in prompt.rendered_text


def test_album_prompts_are_deterministic() -> None:
    """Prompt rendering should remain deterministic for identical album context."""
    builder = PromptBuilder()
    context = _album_context()

    first = builder.build_album_summary_prompt(context)
    second = builder.build_album_summary_prompt(context)

    assert first == second


def _album_context() -> AlbumContext:
    """Return a complete album context fixture."""
    return AlbumContext(
        plex=PlexAlbumContext(
            rating_key="42",
            artist="Nina Simone",
            album="Pastel Blues",
            year=1965,
            summary="Current Plex summary",
            genres=["Jazz", "Soul"],
            styles=[],
            moods=[],
        ),
        musicbrainz=MusicBrainzAlbumContext(
            artist_mbid="artist-mbid",
            release_group_mbid="release-group-mbid",
            release_mbid="release-mbid",
            release_date="1965-10",
            genres=["jazz"],
            tags=["blues"],
            confidence=96,
        ),
        wikipedia=WikipediaAlbumContext(
            language="de",
            title="Pastel Blues",
            extract="Wikipedia summary",
            page_url="https://de.wikipedia.org/wiki/Pastel_Blues",
            thumbnail_url=None,
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )


def _artist_context() -> ArtistContext:
    """Return an artist context fixture."""
    return ArtistContext(
        plex=PlexArtistContext(
            rating_key="100",
            artist="Nina Simone",
            summary="Current biography",
            genres=["Jazz"],
            country="US",
        ),
        musicbrainz=MusicBrainzArtistContext(
            artist_mbid="artist-mbid",
            artist_name="Nina Simone",
            country="US",
            genres=["jazz", "soul"],
            begin_date="1933-02-21",
            end_date="2003-04-21",
            aliases=["Eunice Waymon"],
            confidence=100,
        ),
        wikipedia=WikipediaArtistContext(
            language="de",
            title="Nina Simone",
            extract="Nina Simone war eine US-amerikanische Musikerin.",
        ),
        discogs=DiscogsArtistContext(
            profile="Discogs profile.",
            aliases=["Eunice Waymon"],
            styles=["Vocal Jazz"],
            active_years="1954-2003",
        ),
        lastfm=LastFMArtistContext(
            biography="Last.fm biography.",
            short_biography="Last.fm short biography.",
            tags=["soul"],
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia", "discogs", "lastfm"],
            ready_for_generation=True,
        ),
        full_name="Nina Simone",
        aliases=["Eunice Waymon"],
        birth_date="1933-02-21",
        death_date="2003-04-21",
        nationality="US",
        active_years="1954-2003",
        genres=["jazz", "soul"],
        styles=["Vocal Jazz"],
        biography="Nina Simone war eine US-amerikanische Musikerin.",
        career_summary="Last.fm short biography.",
    )
