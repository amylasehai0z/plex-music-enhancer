"""Prompt engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from plex_music_enhancer.enrichment import (
    AlbumContext,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
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
    assert "Language: de" in prompt.rendered_text


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
    assert "Current Plex summary" in translated.rendered_text
    assert "Current Plex summary" in translated.variables["current_summary"]
    assert improved.name == "album_improve"
    assert "Improve the existing German Plex album summary" in improved.rendered_text
    assert "Avoid repetition" in improved.rendered_text


def test_default_album_prompt_contains_production_safety_requirements() -> None:
    """Default album prompt should constrain production AI generation."""
    builder = PromptBuilder()

    prompt = builder.build_album_summary_prompt(_album_context())

    assert "professionally crafted encyclopedic album description" in prompt.rendered_text
    assert "approximately 80-120 words" in prompt.rendered_text
    assert "one fluent paragraph" in prompt.rendered_text
    assert "Introduce the album and artist" in prompt.rendered_text
    assert "musical style, sound, or production" in prompt.rendered_text
    assert "notable characteristics without long enumerations" in prompt.rendered_text
    assert "closing sentence" in prompt.rendered_text
    assert "varied sentence openings" in prompt.rendered_text
    assert 'Do not write phrases like "ist den Genres ... zuzuordnen"' in prompt.rendered_text
    assert "Use only the supplied metadata" in prompt.rendered_text
    assert "Never invent facts" in prompt.rendered_text
    assert "If the supplied information is sparse" in prompt.rendered_text
    assert "Return only the finished German album description" in prompt.rendered_text


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
