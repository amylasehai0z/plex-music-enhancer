"""AI generation subsystem tests."""

from __future__ import annotations

from datetime import UTC, datetime
from json import loads
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr, ValidationError

from plex_music_enhancer.ai import (
    AIManager,
    AIProviderConfigurationError,
    AIProviderNotFoundError,
    AIProviderNotImplementedError,
    AIProviderRequestError,
    DummyProvider,
    GeneratedSummary,
    OpenAIProvider,
    create_default_registry,
)
from plex_music_enhancer.ai.dummy import DUMMY_SUMMARY_TEXT
from plex_music_enhancer.config import AISettings
from plex_music_enhancer.enrichment import (
    AlbumContext,
    ArtistContext,
    LastFMArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PipelineContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.verification import FactVerifier


def test_generated_summary_model_validates_confidence() -> None:
    """GeneratedSummary should enforce confidence bounds."""
    created_at = datetime(2026, 1, 1, tzinfo=UTC)

    summary = GeneratedSummary(
        language="en",
        text="Summary",
        provider="dummy",
        model="dummy-v1",
        prompt_name="dummy_album_summary",
        prompt_version="1.0",
        created_at=created_at,
        confidence=1.0,
        source_count=3,
        metadata={"artist": "Nina Simone"},
    )

    assert summary.created_at == created_at
    assert summary.source_count == 3

    with pytest.raises(ValidationError):
        GeneratedSummary(
            language="en",
            text="Summary",
            provider="dummy",
            model="dummy-v1",
            prompt_name="dummy_album_summary",
            prompt_version="1.0",
            created_at=created_at,
            confidence=1.1,
            source_count=3,
        )


def test_registry_loads_dummy_provider() -> None:
    """Default registry should load DummyProvider."""
    registry = create_default_registry()

    provider = registry.create("dummy")

    assert isinstance(provider, DummyProvider)
    assert registry.provider_names() == ["dummy", "openai", "ollama"]
    assert registry.implemented_provider_names() == ["dummy", "openai"]


def test_registry_rejects_unknown_provider() -> None:
    """Registry should reject unsupported provider names."""
    registry = create_default_registry()

    with pytest.raises(AIProviderNotFoundError):
        registry.create("unknown")


def test_registry_reports_known_unimplemented_provider() -> None:
    """Registry should distinguish known future providers from invalid names."""
    registry = create_default_registry()

    with pytest.raises(AIProviderNotImplementedError):
        registry.create("ollama")


def test_dummy_provider_generates_deterministic_album_summary() -> None:
    """DummyProvider should produce deterministic placeholder text."""
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    provider = DummyProvider(clock=lambda: created_at)

    prompt = _rendered_prompt(name="album_summary")

    summary = provider.generate_album_summary(prompt)

    assert summary.language == "de"
    assert summary.text == DUMMY_SUMMARY_TEXT
    assert summary.provider == "dummy"
    assert summary.model == "dummy-v1"
    assert summary.prompt_name == "album_summary"
    assert summary.prompt_version == "1.0"
    assert summary.created_at == created_at
    assert summary.confidence == 1.0
    assert summary.source_count == 4
    assert summary.metadata == {
        "artist": "Nina Simone",
        "album": "Pastel Blues",
        "prompt_length": len(prompt.rendered_text),
    }


def test_dummy_provider_generates_deterministic_artist_summary() -> None:
    """DummyProvider should support artist summaries without networking."""
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    provider = DummyProvider(clock=lambda: created_at)

    prompt = _rendered_prompt(
        name="artist_summary",
        variables={
            "artist": "Jennifer Rush",
            "genres": "Pop",
            "current_summary": "Current artist summary",
            "wikipedia_extract": "Reference extract",
            "language": "en",
        },
    )

    summary = provider.generate_artist_summary(prompt)

    assert summary.language == "en"
    assert summary.text == DUMMY_SUMMARY_TEXT
    assert summary.prompt_name == "artist_summary"
    assert summary.created_at == created_at
    assert summary.source_count == 3
    assert summary.metadata == {
        "artist": "Jennifer Rush",
        "prompt_length": len(prompt.rendered_text),
    }


def test_ai_manager_dispatches_to_configured_provider() -> None:
    """AIManager should load the configured provider and dispatch generation."""
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    manager = AIManager(
        settings=AISettings(provider="dummy"),
        provider=DummyProvider(clock=lambda: created_at),
    )

    summary = manager.generate_album_summary(_album_context())
    capabilities = manager.capabilities()
    metadata = manager.provider_metadata()

    assert summary.text == DUMMY_SUMMARY_TEXT
    assert capabilities.album_summary is True
    assert capabilities.artist_summary is True
    assert capabilities.network_required is False
    assert metadata.provider == "dummy"
    assert metadata.configured is True


def test_ai_manager_rejects_invalid_provider() -> None:
    """AIManager should fail clearly for invalid provider configuration."""
    with pytest.raises(AIProviderNotFoundError):
        AIManager(settings=AISettings(provider="unknown"))


def test_openai_provider_generates_summary_from_rendered_prompt() -> None:
    """OpenAIProvider should call the SDK and normalize response metadata."""
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    client = FakeOpenAIClient(
        [
            SimpleNamespace(
                output_text="Generated album summary.",
                usage=SimpleNamespace(input_tokens=100, output_tokens=25),
                status="completed",
            )
        ]
    )
    provider = OpenAIProvider(
        settings=_openai_settings(),
        client=client,
        clock=lambda: created_at,
    )

    summary = provider.generate_album_summary(_rendered_prompt(name="album_summary"))

    assert client.responses.requests == [{"model": "gpt-5.5", "input": "Rendered prompt text"}]
    assert summary.text == "Generated album summary."
    assert summary.provider == "openai"
    assert summary.model == "gpt-5.5"
    assert summary.prompt_name == "album_summary"
    assert summary.prompt_version == "1.0"
    assert summary.created_at == created_at
    assert summary.metadata == {
        "prompt_tokens": 100,
        "completion_tokens": 25,
        "finish_reason": "completed",
    }


def test_openai_provider_dumps_exact_prompt_for_debugging() -> None:
    """OpenAIProvider should write the exact request prompt to the temporary debug file."""
    dump_path = Path("/tmp/openai_prompt.txt")  # noqa: S108 - required debug dump path.
    metadata_path = Path("/tmp/openai_prompt_meta.json")  # noqa: S108 - debug metadata path.
    dump_path.write_text("old prompt", encoding="utf-8")
    metadata_path.write_text("{}", encoding="utf-8")
    client = FakeOpenAIClient(
        [
            SimpleNamespace(
                output_text="Generated album summary.",
                usage=SimpleNamespace(input_tokens=100, output_tokens=25),
                status="completed",
            )
        ]
    )
    provider = OpenAIProvider(settings=_openai_settings(), client=client)
    prompt = _rendered_prompt(
        name="album_summary",
        rendered_text="Rendered prompt text\nmit Umlauten äöü.",
    )

    provider.generate_album_summary(prompt)

    assert client.responses.requests[0]["input"] == prompt.rendered_text
    assert dump_path.read_text(encoding="utf-8") == client.responses.requests[0]["input"]
    metadata = loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["provider"] == "openai"
    assert metadata["model"] == "gpt-5.5"
    assert metadata["target"] == "album_summary"
    assert metadata["prompt_characters"] == len(prompt.rendered_text)
    assert metadata["estimated_prompt_tokens"] > 0


def test_openai_provider_retries_transient_failures() -> None:
    """OpenAIProvider should retry transient SDK failures."""
    transient = FakeSDKError("rate limited", status_code=429)
    client = FakeOpenAIClient(
        [
            transient,
            SimpleNamespace(
                output_text="Generated artist summary.",
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                choices=[SimpleNamespace(finish_reason="stop")],
            ),
        ]
    )
    provider = OpenAIProvider(settings=_openai_settings(max_retries=1), client=client)

    summary = provider.generate_artist_summary(_rendered_prompt(name="artist_summary"))

    assert summary.text == "Generated artist summary."
    assert summary.metadata["prompt_tokens"] == 10
    assert summary.metadata["completion_tokens"] == 5
    assert summary.metadata["finish_reason"] == "stop"
    assert len(client.responses.requests) == 2


@pytest.mark.parametrize("artist_name", ["ABBA", "Queen", "The Beatles"])
def test_ai_manager_budgets_large_artist_prompt_before_openai_generation(
    artist_name: str,
) -> None:
    """Large artist contexts should be trimmed automatically before OpenAI validation."""
    client = FakeOpenAIClient(
        [
            SimpleNamespace(
                output_text="Generierte ABBA-Biografie.",
                usage=SimpleNamespace(input_tokens=300, output_tokens=80),
                status="completed",
            )
        ]
    )
    provider = OpenAIProvider(
        settings=_openai_settings(max_prompt_characters=20_000),
        client=client,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    manager = AIManager(
        settings=_openai_settings(max_prompt_characters=20_000),
        provider=provider,
    )

    summary = manager.generate_artist_summary(_large_artist_context(artist_name))

    sent_prompt = client.responses.requests[0]["input"]
    assert summary.text == "Generierte ABBA-Biografie."
    assert len(sent_prompt) <= 20_000
    assert artist_name in sent_prompt
    assert "Verified facts" in sent_prompt
    assert f"Existing Plex biography paragraph 0 about {artist_name}" in sent_prompt
    assert f"Existing Plex biography paragraph 179 about {artist_name}" in sent_prompt
    assert "omitted because it exceeds" not in sent_prompt


def test_openai_provider_requires_api_key(monkeypatch) -> None:
    """OpenAIProvider should validate API key configuration."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(settings=AISettings(provider="openai"))

    with pytest.raises(AIProviderConfigurationError, match="OPENAI_API_KEY"):
        provider.validate_configuration()


def test_openai_provider_reads_openai_api_key(monkeypatch) -> None:
    """OpenAIProvider should read OPENAI_API_KEY when settings omit an API key."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    provider = OpenAIProvider(settings=AISettings(provider="openai"))

    provider.validate_configuration()

    assert provider.provider_metadata().configured is True


def test_openai_provider_rejects_empty_and_oversized_prompts() -> None:
    """OpenAIProvider should refuse unsafe prompt payloads before networking."""
    provider = OpenAIProvider(
        settings=_openai_settings(max_prompt_characters=5),
        client=FakeOpenAIClient([]),
    )

    with pytest.raises(AIProviderConfigurationError, match="empty prompt"):
        provider.generate_album_summary(_rendered_prompt(name="album_summary", rendered_text="  "))

    with pytest.raises(AIProviderConfigurationError, match="longer than 5"):
        provider.generate_album_summary(
            _rendered_prompt(name="album_summary", rendered_text="too long")
        )


def test_openai_provider_maps_sdk_errors() -> None:
    """OpenAIProvider should map SDK errors to project exceptions."""
    client = FakeOpenAIClient([FakeSDKError("bad request", status_code=400)])
    provider = OpenAIProvider(settings=_openai_settings(), client=client)

    with pytest.raises(AIProviderRequestError, match="HTTP 400"):
        provider.generate_album_summary(_rendered_prompt(name="album_summary"))


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


def _large_artist_context(artist_name: str) -> ArtistContext:
    """Return an oversized artist context resembling a large public artist."""
    long_wikipedia = "\n\n".join(
        f"{artist_name} Wikipedia paragraph {index}. "
        "The artist had extensive international context."
        for index in range(180)
    )
    long_lastfm = "\n\n".join(
        f"Last.fm community biography paragraph {index} about {artist_name}."
        for index in range(160)
    )
    long_plex = "\n\n".join(
        f"Existing Plex biography paragraph {index} about {artist_name}." for index in range(180)
    )
    context = ArtistContext(
        plex=PlexArtistContext(
            rating_key=artist_name.casefold().replace(" ", "-"),
            artist=artist_name,
            summary=long_plex,
            genres=["Pop"],
            country="SE",
        ),
        musicbrainz=MusicBrainzArtistContext(
            artist_mbid=f"{artist_name.casefold()}-mbid",
            artist_name=artist_name,
            country="SE",
            genres=["pop", "europop"],
            begin_date="1972",
            aliases=["Björn & Benny, Agnetha & Anni-Frid"],
            confidence=100,
        ),
        wikipedia=WikipediaArtistContext(
            language="de",
            title=artist_name,
            extract=long_wikipedia,
            page_url=f"https://de.wikipedia.org/wiki/{artist_name.replace(' ', '_')}",
        ),
        lastfm=LastFMArtistContext(
            biography=long_lastfm,
            short_biography="ABBA war eine schwedische Popgruppe.",
            tags=["pop", "swedish pop"],
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia", "lastfm"],
            ready_for_generation=True,
        ),
        full_name=artist_name,
        active_years="1972–1982",
        genres=["pop", "europop"],
        notable_albums=["Arrival", "The Album", "Voulez-Vous"],
        milestones=["Eurovision Song Contest 1974"],
        historical_context=long_wikipedia,
        career_summary="ABBA war eine international erfolgreiche schwedische Popgruppe.",
        biography=long_wikipedia,
    )
    return context.model_copy(update={"fact_collection": FactVerifier().verify_artist(context)})


def _rendered_prompt(
    *,
    name: str,
    variables: dict[str, str] | None = None,
    rendered_text: str = "Rendered prompt text",
) -> RenderedPrompt:
    """Return a rendered prompt fixture."""
    prompt_variables = variables or {
        "artist": "Nina Simone",
        "album": "Pastel Blues",
        "genres": "jazz",
        "release_date": "1965-10",
        "wikipedia_extract": "Wikipedia summary",
        "current_summary": "Current Plex summary",
        "language": "de",
    }
    return RenderedPrompt(
        name=name,
        version="1.0",
        rendered_text=rendered_text,
        variables=prompt_variables,
        template="Template text",
    )


def _openai_settings(
    *,
    max_retries: int = 0,
    max_prompt_characters: int = 20000,
) -> AISettings:
    """Return OpenAI settings for tests."""
    return AISettings(
        provider="openai",
        model="gpt-5.5",
        api_key=SecretStr("sk-test"),
        max_retries=max_retries,
        max_prompt_characters=max_prompt_characters,
    )


class FakeOpenAIClient:
    """Fake OpenAI SDK client."""

    def __init__(self, responses: list[object]) -> None:
        """Create a fake client."""
        self.responses = FakeResponses(responses)


class FakeResponses:
    """Fake OpenAI responses API."""

    def __init__(self, responses: list[object]) -> None:
        """Create fake responses API."""
        self._responses = responses
        self.requests: list[dict[str, str]] = []

    def create(self, *, model: str, input: str) -> object:  # noqa: A002
        """Return or raise the next fake response."""
        self.requests.append({"model": model, "input": input})
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response

        return response


class FakeSDKError(Exception):
    """Fake OpenAI SDK error."""

    def __init__(self, message: str, *, status_code: int) -> None:
        """Create a fake SDK error."""
        super().__init__(message)
        self.status_code = status_code
