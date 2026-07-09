"""End-to-end preview service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.ai import AIManager, GeneratedSummary, OpenAIProvider
from plex_music_enhancer.ai.dummy import DUMMY_SUMMARY_TEXT
from plex_music_enhancer.config import AISettings
from plex_music_enhancer.enrichment import (
    AlbumContext,
    EnrichmentPipelineError,
    MusicBrainzAlbumContext,
    PipelineContext,
    PlexAlbumContext,
    WikipediaAlbumContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.services import EnrichmentPreviewService, PreviewError


def test_preview_service_collects_context_and_generates_summary() -> None:
    """Preview service should connect AlbumContext collection to AI generation."""
    pipeline = FakeContextPipeline()
    ai_manager = FakeAIManager()

    document = _service(pipeline=pipeline, ai_manager=ai_manager).preview_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert pipeline.received == ("Nina Simone", "Pastel Blues")
    assert ai_manager.received == _album_context()
    assert ai_manager.prompt == _rendered_prompt()
    assert document.context == _album_context()
    assert document.rendered_prompt == _rendered_prompt()
    assert document.generated_summary.text == DUMMY_SUMMARY_TEXT
    assert document.generated_summary.provider == "dummy"
    assert document.generation_time_seconds >= 0
    assert document.qa_report is not None
    assert "overall_score" in document.model_dump_json()


def test_preview_service_renders_selected_album_prompt() -> None:
    """Preview service should render specialized album prompt templates when requested."""
    ai_manager = FakeAIManager()

    document = _service(pipeline=FakeContextPipeline(), ai_manager=ai_manager).preview_album(
        artist="Nina Simone",
        album="Pastel Blues",
        prompt_name="album_translate",
    )

    assert ai_manager.prompt_name == "album_translate"
    assert document.rendered_prompt.name == "album_translate"


def test_preview_service_reports_context_failure() -> None:
    """Preview service should wrap context collection failures."""
    service = _service(pipeline=FailingContextPipeline(), ai_manager=FakeAIManager())

    try:
        service.preview_album(artist="Nina Simone", album="Pastel Blues")
    except PreviewError as exc:
        assert "No Plex album found" in str(exc)
    else:
        raise AssertionError("Expected PreviewError.")


def test_preview_service_reports_ai_failure() -> None:
    """Preview service should wrap AI generation failures."""
    service = _service(pipeline=FakeContextPipeline(), ai_manager=FailingAIManager())

    try:
        service.preview_album(artist="Nina Simone", album="Pastel Blues")
    except PreviewError as exc:
        assert "AI unavailable" in str(exc)
    else:
        raise AssertionError("Expected PreviewError.")


def test_preview_service_generates_with_openai_provider() -> None:
    """Preview service should work with OpenAIProvider through AIManager."""
    client = FakeOpenAIClient(
        SimpleNamespace(
            output_text="OpenAI generated summary.",
            usage=SimpleNamespace(input_tokens=120, output_tokens=30),
            status="completed",
        )
    )
    ai_manager = AIManager(
        settings=AISettings(
            provider="openai",
            model="gpt-5.5",
            api_key=SecretStr("sk-test"),
        ),
        provider=OpenAIProvider(
            settings=AISettings(
                provider="openai",
                model="gpt-5.5",
                api_key=SecretStr("sk-test"),
            ),
            client=client,
            clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )

    document = _service(pipeline=FakeContextPipeline(), ai_manager=ai_manager).preview_album(
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert document.generated_summary.text == "OpenAI generated summary."
    assert document.generated_summary.provider == "openai"
    assert document.generated_summary.model == "gpt-5.5"
    assert document.generated_summary.prompt_name == "album_summary"
    assert document.generated_summary.metadata == {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "finish_reason": "completed",
    }
    assert client.responses.request["model"] == "gpt-5.5"
    prompt_text = client.responses.request["input"]
    assert "Pastel Blues" in prompt_text
    assert "concise German music encyclopedia article" in prompt_text
    assert "coherent story" in prompt_text
    assert "varied sentence openings" in prompt_text
    assert "ist den Genres ... zuzuordnen" in prompt_text
    assert "Use only the supplied metadata" in prompt_text
    assert "Never invent" in prompt_text
    assert "career milestones" in prompt_text
    assert "commercial success" in prompt_text
    assert "reception" in prompt_text
    assert "chart success" in prompt_text
    assert "singles" in prompt_text
    assert "track listing" in prompt_text
    assert "If data is missing, omit that aspect silently" in prompt_text


class FakeContextPipeline:
    """Fake AlbumContext pipeline."""

    def __init__(self) -> None:
        """Create a fake pipeline."""
        self.received: tuple[str, str] | None = None

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Return one album context."""
        self.received = (artist, album)
        return _album_context()


class FailingContextPipeline:
    """Fake failing context pipeline."""

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Raise a context collection error."""
        del artist, album
        raise EnrichmentPipelineError("No Plex album found")


class FakeAIManager:
    """Fake AI manager."""

    def __init__(self) -> None:
        """Create a fake AI manager."""
        self.received: AlbumContext | None = None
        self.prompt: RenderedPrompt | None = None
        self.prompt_name: str = "album_summary"

    def render_album_summary_prompt(
        self,
        context: AlbumContext,
        *,
        prompt_name: str = "album_summary",
    ) -> RenderedPrompt:
        """Return a rendered prompt."""
        self.received = context
        self.prompt_name = prompt_name
        return _rendered_prompt(name=prompt_name)

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Return generated summary."""
        self.prompt = prompt
        return _generated_summary()


class FailingAIManager:
    """Fake failing AI manager."""

    def render_album_summary_prompt(self, context: AlbumContext) -> RenderedPrompt:
        """Return a rendered prompt."""
        del context
        return _rendered_prompt()

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Raise an AI generation error."""
        del prompt
        raise RuntimeError("AI unavailable")


class FakeOpenAIClient:
    """Fake OpenAI SDK client."""

    def __init__(self, response: object) -> None:
        """Create a fake client."""
        self.responses = FakeOpenAIResponses(response)


class FakeOpenAIResponses:
    """Fake OpenAI responses resource."""

    def __init__(self, response: object) -> None:
        """Create fake responses."""
        self._response = response
        self.request: dict[str, str] = {}

    def create(self, *, model: str, input: str) -> object:  # noqa: A002
        """Return the fake response."""
        self.request = {"model": model, "input": input}
        return self._response


def _service(
    *,
    pipeline: object,
    ai_manager: object,
) -> EnrichmentPreviewService:
    """Create a preview service with fakes."""
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")
    return EnrichmentPreviewService(
        url,
        SecretStr("secret-token"),
        pipeline=pipeline,  # type: ignore[arg-type]
        ai_manager=ai_manager,  # type: ignore[arg-type]
    )


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
            language="en",
            title="Pastel Blues",
            extract="Wikipedia summary",
            page_url="https://en.wikipedia.org/wiki/Pastel_Blues",
            thumbnail_url=None,
        ),
        pipeline=PipelineContext(
            collected_sources=["plex", "musicbrainz", "wikipedia"],
            missing_fields=[],
            warnings=[],
            ready_for_generation=True,
        ),
    )


def _generated_summary() -> GeneratedSummary:
    """Return a generated summary fixture."""
    return GeneratedSummary(
        language="en",
        text=DUMMY_SUMMARY_TEXT,
        provider="dummy",
        model="dummy-v1",
        prompt_name="dummy_album_summary",
        prompt_version="1.0",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        confidence=1.0,
        source_count=3,
        metadata={"artist": "Nina Simone", "album": "Pastel Blues"},
    )


def _rendered_prompt(name: str = "album_summary") -> RenderedPrompt:
    """Return a rendered prompt fixture."""
    return RenderedPrompt(
        name=name,
        version="1.0",
        rendered_text="Artist: Nina Simone\nAlbum: Pastel Blues\nLanguage: de\n",
        variables={
            "artist": "Nina Simone",
            "album": "Pastel Blues",
            "language": "de",
        },
        template="Artist: {{artist}}\nAlbum: {{album}}\nLanguage: {{language}}\n",
    )
