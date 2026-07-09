"""Artist enrichment workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from plex_music_enhancer.ai import GeneratedSummary
from plex_music_enhancer.apply import ApplyService, AuditStore, BackupStore
from plex_music_enhancer.editorial import ArtistEditorialComposer
from plex_music_enhancer.editorial.composer import render_editorial_context
from plex_music_enhancer.enrichment import (
    DiscogsArtistContext,
    EnrichmentPipeline,
    LastFMArtistContext,
)
from plex_music_enhancer.prompts import RenderedPrompt
from plex_music_enhancer.providers.musicbrainz import (
    MusicBrainzAlias,
    MusicBrainzArtistMetadata,
    MusicBrainzArtistSearchResult,
)
from plex_music_enhancer.providers.wikipedia import WikipediaSummary
from plex_music_enhancer.review import ReviewService
from plex_music_enhancer.services import EnrichmentPreviewService


def test_enrichment_pipeline_collects_artist_context() -> None:
    """Artist context should merge Plex, MusicBrainz, and Wikipedia metadata."""
    pipeline = EnrichmentPipeline(
        "http://localhost:32400",
        SecretStr("token"),
        musicbrainz_provider=FakeMusicBrainzProvider(),
        wikipedia_provider=FakeWikipediaProvider(),
        discogs_provider=FakeDiscogsProvider(),
        lastfm_provider=FakeLastFMProvider(),
        plex_server_factory=FakePlexServer,
    )

    context = pipeline.collect_artist_context(artist="Nina Simone")

    assert context.plex.rating_key == "100"
    assert context.plex.artist == "Nina Simone"
    assert context.musicbrainz.artist_mbid == "artist-mbid"
    assert context.musicbrainz.genres == ["jazz", "soul"]
    assert context.wikipedia.language == "de"
    assert context.full_name == "Nina Simone"
    assert context.aliases == ["Eunice Waymon"]
    assert context.birth_date == "1933-02-21"
    assert context.death_date == "2003-04-21"
    assert context.styles == ["Vocal Jazz"]
    assert context.biography == "Nina Simone war eine US-amerikanische Musikerin."
    assert context.fact_collection.by_category("birth_date")[0].confidence_score >= 0.9
    assert context.pipeline.ready_for_generation is True


def test_artist_editorial_composer_builds_biography_guidance() -> None:
    """Artist composer should produce reusable biography guidance."""
    context = FakeArtistPipeline().collect_artist_context(artist="Nina Simone")

    editorial = ArtistEditorialComposer().compose_artist(context)
    rendered = render_editorial_context(editorial)

    assert editorial.recommended_story_order is not None
    assert "Introduction" in editorial.recommended_story_order
    assert "Origins" in editorial.recommended_story_order
    assert "Musical style" in editorial.recommended_story_order
    assert "Verified facts:" in rendered
    assert "never resolve conflicting facts by guessing" in rendered


def test_preview_and_review_generate_artist_biography() -> None:
    """Preview and review should support artist biographies."""
    preview_service = EnrichmentPreviewService(
        "http://localhost:32400",
        SecretStr("token"),
        pipeline=FakeArtistPipeline(),
        ai_manager=FakeAIManager(),
    )
    review_service = ReviewService(preview_service=preview_service)

    preview = preview_service.preview_artist(artist="Nina Simone")
    review = review_service.create_artist_review(artist="Nina Simone")

    assert preview.context.plex.artist == "Nina Simone"
    assert preview.context.fact_collection.facts
    assert preview.generated_summary.text == _german_summary()
    assert review.current_summary == "Aktuelle Biografie."
    assert review.proposed_summary == _german_summary()
    assert review.quality.status == "PASS"
    assert review.style.overall_style


def test_apply_service_writes_artist_biography(tmp_path: Path) -> None:
    """ApplyService should back up, write, verify, and audit artist summaries."""
    artist_object = FakeMutablePlexObject(summary="Aktuelle Biografie.")
    preview_service = EnrichmentPreviewService(
        "http://localhost:32400",
        SecretStr("token"),
        pipeline=FakeArtistPipeline(),
        ai_manager=FakeAIManager(),
    )
    service = ApplyService(
        review_service=ReviewService(preview_service=preview_service),
        base_url="http://localhost:32400",
        token=SecretStr("token"),
        backup_store=BackupStore(directory=tmp_path / "exports" / "backups"),
        audit_store=AuditStore(directory=tmp_path / "exports" / "audit"),
        album_loader=lambda rating_key: artist_object,
    )

    result = service.apply_artist_summary(artist="Nina Simone")

    assert result.status == "SUCCESS"
    assert result.artist == "Nina Simone"
    assert result.album == "artist"
    assert result.backup_path is not None
    assert result.audit_path is not None
    assert Path(result.backup_path).exists()
    assert Path(result.audit_path).exists()
    assert artist_object.summary == _german_summary()


class FakePlexArtist:
    """Fake Plex artist."""

    ratingKey = "100"  # noqa: N815
    title = "Nina Simone"
    summary = "Aktuelle Biografie."
    genres = ["Jazz", "Soul"]
    country = "US"

    def albums(self) -> list[object]:
        """Return fake albums."""
        return []


class FakePlexSection:
    """Fake music section."""

    type = "artist"

    def all(self) -> list[FakePlexArtist]:
        """Return fake artists."""
        return [FakePlexArtist()]


class FakePlexLibrary:
    """Fake Plex library."""

    def sections(self) -> list[FakePlexSection]:
        """Return fake sections."""
        return [FakePlexSection()]


class FakePlexServer:
    """Fake Plex server factory."""

    def __init__(self, base_url: str, token: str) -> None:
        """Create fake server."""
        self.base_url = base_url
        self.token = token
        self.library = FakePlexLibrary()


class FakeMusicBrainzProvider:
    """Fake MusicBrainz provider."""

    def search_artist(self, name: str, *, limit: int = 5) -> list[MusicBrainzArtistSearchResult]:
        """Return fake artist candidates."""
        assert name == "Nina Simone"
        assert limit == 5
        return [
            MusicBrainzArtistSearchResult(
                mbid="artist-mbid",
                name="Nina Simone",
                country="US",
                tags=["jazz"],
                aliases=[MusicBrainzAlias(name="Eunice Waymon")],
                score=100,
            )
        ]

    def get_artist_metadata(self, mbid: str) -> MusicBrainzArtistMetadata:
        """Return fake artist metadata."""
        assert mbid == "artist-mbid"
        return MusicBrainzArtistMetadata(
            mbid=mbid,
            name="Nina Simone",
            country="US",
            genres=["jazz", "soul"],
            begin_date="1933-02-21",
            end_date="2003-04-21",
            aliases=[MusicBrainzAlias(name="Eunice Waymon")],
        )

    def get_album_metadata(self, mbid: str) -> object:
        """Unused album metadata method."""
        raise AssertionError(mbid)


class FakeWikipediaProvider:
    """Fake Wikipedia provider."""

    name = "wikipedia"

    def lookup_artist(self, artist: str) -> WikipediaSummary:
        """Return fake artist biography."""
        assert artist == "Nina Simone"
        return WikipediaSummary(
            title="Nina Simone",
            page_id=1,
            language="de",
            extract="Nina Simone war eine US-amerikanische Musikerin.",
            url="https://de.wikipedia.org/wiki/Nina_Simone",
            thumbnail="https://example.test/nina.jpg",
        )

    def lookup_album(self, artist: str, album: str) -> None:
        """Unused album lookup."""
        del artist, album
        return None


class FakeDiscogsProvider:
    """Fake optional Discogs provider."""

    configured = True

    def lookup_artist(self, artist: str) -> DiscogsArtistContext:
        """Return fake Discogs artist context."""
        assert artist == "Nina Simone"
        return DiscogsArtistContext(
            profile="Discogs profile.",
            aliases=["Eunice Waymon"],
            genres=["Jazz"],
            styles=["Vocal Jazz"],
            active_years="1954-2003",
        )

    def lookup_album(self, artist: str, album: str) -> object:
        """Unused album lookup."""
        del artist, album
        raise AssertionError("album lookup should not be used")


class FakeLastFMProvider:
    """Fake optional Last.fm provider."""

    configured = True

    def lookup_artist(self, artist: str) -> LastFMArtistContext:
        """Return fake Last.fm artist context."""
        assert artist == "Nina Simone"
        return LastFMArtistContext(
            biography="Last.fm biography.",
            short_biography="Last.fm short biography.",
            tags=["soul"],
            similar_artists=["Billie Holiday"],
        )

    def lookup_album(self, artist: str, album: str) -> object:
        """Unused album lookup."""
        del artist, album
        raise AssertionError("album lookup should not be used")


class FakeArtistPipeline:
    """Fake artist context pipeline."""

    def collect_artist_context(self, *, artist: str):
        """Return fake artist context."""
        pipeline = EnrichmentPipeline(
            "http://localhost:32400",
            SecretStr("token"),
            musicbrainz_provider=FakeMusicBrainzProvider(),
            wikipedia_provider=FakeWikipediaProvider(),
            discogs_provider=FakeDiscogsProvider(),
            lastfm_provider=FakeLastFMProvider(),
            plex_server_factory=FakePlexServer,
        )
        return pipeline.collect_artist_context(artist=artist)

    def collect_album_context(self, *, artist: str, album: str) -> object:
        """Unused album context method."""
        del artist, album
        raise AssertionError("album context should not be collected")


class FakeAIManager:
    """Fake AI manager for artist preview."""

    def render_artist_summary_prompt(self, context) -> RenderedPrompt:
        """Return fake rendered prompt."""
        return RenderedPrompt(
            name="artist_summary",
            version="1.0",
            rendered_text="Prompt",
            variables={
                "artist": context.plex.artist,
                "language": "de",
                "current_summary": context.plex.summary or "",
                "wikipedia_extract": context.wikipedia.extract or "",
            },
            template="Template",
        )

    def generate_artist_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Return fake generated biography."""
        return GeneratedSummary(
            language="de",
            text=_german_summary(),
            provider="openai",
            model="gpt-5.5",
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confidence=0.9,
            source_count=3,
            metadata={},
        )

    def render_album_summary_prompt(self, context) -> RenderedPrompt:
        """Unused album prompt method."""
        del context
        raise AssertionError("album prompt should not be rendered")

    def generate_album_summary_from_prompt(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Unused album generation method."""
        del prompt
        raise AssertionError("album summary should not be generated")


class FakeMutablePlexObject:
    """Fake writable Plex artist object."""

    def __init__(self, *, summary: str) -> None:
        """Create fake object."""
        self.summary = summary
        self._pending_summary: str | None = None

    def batchEdits(self) -> None:  # noqa: N802
        """Start fake batch edit."""

    def editSummary(self, summary: str) -> None:  # noqa: N802
        """Stage fake summary."""
        self._pending_summary = summary

    def saveEdits(self) -> None:  # noqa: N802
        """Persist fake summary."""
        self.summary = self._pending_summary or ""

    def reload(self) -> FakeMutablePlexObject:
        """Reload fake object."""
        return self


def _german_summary() -> str:
    """Return deterministic German prose."""
    return (
        "Nina Simone, geboren 1933 als Eunice Waymon und gestorben 2003, war eine "
        "US-amerikanische Musikerin, deren Werk Jazz, Soul, Blues und klassische "
        "Einflüsse miteinander verband. Zwischen 1954 und 2003 entwickelte sie einen "
        "präzisen Vocal-Jazz-Stil, der Gesang und Klavier eng aufeinander bezog. "
        "Zugleich wurde sie durch eindringliche Interpretationen und politisch bewusste "
        "Lieder bekannt, die ihre künstlerische Entwicklung mit der Bürgerrechtsbewegung "
        "verbanden. Dadurch gilt ihre Laufbahn als wichtiger Bezugspunkt für die "
        "Geschichte afroamerikanischer Populärmusik, ohne sich auf ein einzelnes Genre "
        "reduzieren zu lassen."
    )
