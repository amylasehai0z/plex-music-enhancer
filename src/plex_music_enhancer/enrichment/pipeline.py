"""Read-only pipeline for collecting normalized album context."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, SecretStr

from plex_music_enhancer.cache import CacheKind, KnowledgeCacheService
from plex_music_enhancer.config import get_settings
from plex_music_enhancer.enrichment.models import (
    AlbumContext,
    ArtistContext,
    DiscogsAlbumContext,
    DiscogsArtistContext,
    LastFMAlbumContext,
    LastFMArtistContext,
    MusicBrainzAlbumContext,
    MusicBrainzArtistContext,
    PlexAlbumContext,
    PlexArtistContext,
    WikipediaAlbumContext,
    WikipediaArtistContext,
)
from plex_music_enhancer.enrichment.validators import (
    validate_album_context,
    validate_artist_context,
)
from plex_music_enhancer.knowledge.builder import build_album_knowledge_graph
from plex_music_enhancer.performance import ProviderScheduler, ProviderTask
from plex_music_enhancer.providers import (
    DiscogsProvider,
    LastFMProvider,
    ProviderManager,
    WikipediaProvider,
)
from plex_music_enhancer.providers.base import AlbumMetadata
from plex_music_enhancer.providers.musicbrainz import (
    MusicBrainzAlbumMetadata,
    MusicBrainzArtistMetadata,
    MusicBrainzArtistSearchResult,
    MusicBrainzProvider,
)
from plex_music_enhancer.providers.wikipedia import WikipediaSummary
from plex_music_enhancer.services.musicbrainz_matcher import MatchResult, MusicBrainzMatcher
from plex_music_enhancer.verification import FactVerifier


class EnrichmentPipelineError(Exception):
    """Raised when album context cannot be collected."""


@dataclass(frozen=True)
class _PlexAlbumLookup:
    """Selected Plex album plus local artist discography context."""

    album: Any
    artist: Any
    artist_albums: list[Any]


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the context pipeline."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the context pipeline."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class _Matcher(Protocol):
    """MusicBrainz matcher interface used by the context pipeline."""

    def match_album(
        self,
        *,
        artist_name: str,
        album_title: str,
        release_year: int | None = None,
    ) -> MatchResult:
        """Match one album to MusicBrainz."""


class _MusicBrainzProvider(Protocol):
    """MusicBrainz metadata provider interface used by the context pipeline."""

    def get_album_metadata(self, mbid: str) -> MusicBrainzAlbumMetadata:
        """Return release-group metadata."""

    def search_artist(self, name: str, *, limit: int = 5) -> list[MusicBrainzArtistSearchResult]:
        """Search artists by name."""

    def get_artist_metadata(self, mbid: str) -> MusicBrainzArtistMetadata:
        """Return artist metadata."""


class _WikipediaLookupProvider(Protocol):
    """Wikipedia lookup provider interface used for detailed page fields."""

    name: str

    def lookup_album(self, artist: str, album: str) -> WikipediaSummary | None:
        """Return detailed Wikipedia summary data."""

    def lookup_artist(self, artist: str) -> WikipediaSummary | None:
        """Return detailed Wikipedia artist summary data."""


class _DiscogsLookupProvider(Protocol):
    """Discogs lookup provider interface used for optional enrichment."""

    @property
    def configured(self) -> bool:
        """Return whether Discogs credentials are available."""

    def lookup_album(self, artist: str, album: str) -> DiscogsAlbumContext:
        """Return Discogs album context."""

    def lookup_artist(self, artist: str) -> DiscogsArtistContext:
        """Return Discogs artist context."""


class _LastFMLookupProvider(Protocol):
    """Last.fm lookup provider interface used for optional enrichment."""

    @property
    def configured(self) -> bool:
        """Return whether Last.fm credentials are available."""

    def lookup_album(self, artist: str, album: str) -> LastFMAlbumContext:
        """Return Last.fm album context."""

    def lookup_artist(self, artist: str) -> LastFMArtistContext:
        """Return Last.fm artist context."""


class EnrichmentPipeline:
    """Collect normalized read-only context for one Plex album."""

    def __init__(
        self,
        base_url: AnyHttpUrl | str,
        token: SecretStr,
        *,
        matcher: _Matcher | None = None,
        musicbrainz_provider: _MusicBrainzProvider | None = None,
        provider_manager: ProviderManager | None = None,
        wikipedia_provider: _WikipediaLookupProvider | None = None,
        discogs_provider: _DiscogsLookupProvider | None = None,
        lastfm_provider: _LastFMLookupProvider | None = None,
        knowledge_cache: KnowledgeCacheService | None = None,
        provider_scheduler: ProviderScheduler | None = None,
        plex_server_factory: Callable[[str, str], Any] = PlexServer,
    ) -> None:
        """Create an enrichment pipeline."""
        self._base_url = str(base_url).rstrip("/")
        self._token = token
        self._plex_server_factory = plex_server_factory
        use_default_cache = (
            matcher is None
            and musicbrainz_provider is None
            and provider_manager is None
            and wikipedia_provider is None
            and discogs_provider is None
            and lastfm_provider is None
        )
        if knowledge_cache is not None:
            self._knowledge_cache = knowledge_cache
        elif use_default_cache:
            self._knowledge_cache = KnowledgeCacheService()
        else:
            self._knowledge_cache = None
        provider = musicbrainz_provider or MusicBrainzProvider()
        self._musicbrainz_provider = provider
        self._matcher = matcher or MusicBrainzMatcher(provider=provider)
        self._wikipedia_provider = wikipedia_provider or WikipediaProvider()
        self._provider_manager = provider_manager or ProviderManager([self._wikipedia_provider])
        self._discogs_provider = discogs_provider or _default_discogs_provider()
        self._lastfm_provider = lastfm_provider or _default_lastfm_provider()
        self._provider_scheduler = provider_scheduler or ProviderScheduler(
            max_workers=get_settings().performance.max_workers
        )

    def collect_album_context(self, *, artist: str, album: str) -> AlbumContext:
        """Collect all available metadata for one Plex album without modifying Plex."""
        album_lookup = self._read_plex_album(artist=artist, album=album)
        plex_album = album_lookup.album
        plex_context = _plex_context(plex_album, requested_artist=artist)
        warnings: list[str] = []
        collected_sources = ["plex"]

        match = self._match_musicbrainz(plex_context, warnings)
        musicbrainz_album = self._musicbrainz_album(match, warnings)
        musicbrainz_context = _musicbrainz_context(match, musicbrainz_album)
        if musicbrainz_context.release_group_mbid is not None:
            collected_sources.append("musicbrainz")

        provider_results = self._provider_scheduler.run(
            [
                ProviderTask(
                    name="wikipedia",
                    operation=lambda: self._wikipedia_context(plex_context, warnings),
                    priority=10,
                ),
                ProviderTask(
                    name="discogs",
                    operation=lambda: self._discogs_context(plex_context, warnings),
                    should_run=lambda: self._discogs_provider.configured,
                    priority=20,
                ),
                ProviderTask(
                    name="lastfm_album",
                    operation=lambda: self._lastfm_context(plex_context, warnings),
                    should_run=lambda: self._lastfm_provider.configured,
                    priority=30,
                ),
                ProviderTask(
                    name="lastfm_artist",
                    operation=lambda: self._lastfm_album_artist_context(plex_context, warnings),
                    should_run=lambda: self._lastfm_provider.configured,
                    priority=31,
                ),
            ]
        )
        wikipedia_context = _scheduled_value(
            provider_results.get("wikipedia"),
            WikipediaAlbumContext,
            warnings=warnings,
        )
        if wikipedia_context.extract is not None:
            collected_sources.append("wikipedia")

        discogs_context = _scheduled_value(
            provider_results.get("discogs"),
            DiscogsAlbumContext,
            warnings=warnings,
        )
        if _discogs_album_has_data(discogs_context):
            collected_sources.append("discogs")

        lastfm_context = _scheduled_value(
            provider_results.get("lastfm_album"),
            LastFMAlbumContext,
            warnings=warnings,
        )
        lastfm_artist_context = _scheduled_value(
            provider_results.get("lastfm_artist"),
            LastFMArtistContext,
            warnings=warnings,
        )
        if _lastfm_album_has_data(lastfm_context) or _lastfm_artist_has_data(lastfm_artist_context):
            collected_sources.append("lastfm")

        pipeline_context = validate_album_context(
            plex=plex_context,
            musicbrainz=musicbrainz_context,
            wikipedia=wikipedia_context,
            collected_sources=collected_sources,
            warnings=warnings,
        )

        context = AlbumContext(
            plex=plex_context,
            musicbrainz=musicbrainz_context,
            wikipedia=wikipedia_context,
            discogs=discogs_context,
            lastfm=lastfm_context,
            lastfm_artist=lastfm_artist_context,
            pipeline=pipeline_context,
            **_merge_discogs_album_fields(
                _rich_album_fields(
                    plex_album=plex_album,
                    plex_artist=album_lookup.artist,
                    artist_albums=album_lookup.artist_albums,
                    plex=plex_context,
                    musicbrainz=musicbrainz_context,
                    album_metadata=musicbrainz_album,
                ),
                discogs_context,
            ),
        )
        with_graph = context.model_copy(
            update={"knowledge_graph": build_album_knowledge_graph(context)}
        )
        return with_graph.model_copy(
            update={"fact_collection": FactVerifier().verify_album(with_graph)}
        )

    def collect_artist_context(self, *, artist: str) -> ArtistContext:
        """Collect all available metadata for one Plex artist without modifying Plex."""
        plex_artist = self._read_plex_artist(artist=artist)
        plex_context = _plex_artist_context(plex_artist, requested_artist=artist)
        warnings: list[str] = []
        collected_sources = ["plex"]

        artist_match = self._match_artist(plex_context, warnings)
        artist_metadata = self._musicbrainz_artist(artist_match, warnings)
        musicbrainz_context = _musicbrainz_artist_context(artist_match, artist_metadata)
        if musicbrainz_context.artist_mbid is not None:
            collected_sources.append("musicbrainz")

        provider_results = self._provider_scheduler.run(
            [
                ProviderTask(
                    name="wikipedia",
                    operation=lambda: self._wikipedia_artist_context(plex_context, warnings),
                    priority=10,
                ),
                ProviderTask(
                    name="discogs",
                    operation=lambda: self._discogs_artist_context(plex_context, warnings),
                    should_run=lambda: self._discogs_provider.configured,
                    priority=20,
                ),
                ProviderTask(
                    name="lastfm",
                    operation=lambda: self._lastfm_artist_context(plex_context, warnings),
                    should_run=lambda: self._lastfm_provider.configured,
                    priority=30,
                ),
            ]
        )
        wikipedia_context = _scheduled_value(
            provider_results.get("wikipedia"),
            WikipediaArtistContext,
            warnings=warnings,
        )
        if wikipedia_context.extract is not None:
            collected_sources.append("wikipedia")

        discogs_context = _scheduled_value(
            provider_results.get("discogs"),
            DiscogsArtistContext,
            warnings=warnings,
        )
        if _discogs_artist_has_data(discogs_context):
            collected_sources.append("discogs")

        lastfm_context = _scheduled_value(
            provider_results.get("lastfm"),
            LastFMArtistContext,
            warnings=warnings,
        )
        if _lastfm_artist_has_data(lastfm_context):
            collected_sources.append("lastfm")

        pipeline_context = validate_artist_context(
            plex=plex_context,
            musicbrainz=musicbrainz_context,
            wikipedia=wikipedia_context,
            collected_sources=collected_sources,
            warnings=warnings,
        )
        context = ArtistContext(
            plex=plex_context,
            musicbrainz=musicbrainz_context,
            wikipedia=wikipedia_context,
            discogs=discogs_context,
            lastfm=lastfm_context,
            pipeline=pipeline_context,
            **_rich_artist_fields(
                plex_artist=plex_artist,
                plex=plex_context,
                musicbrainz=musicbrainz_context,
                wikipedia=wikipedia_context,
                discogs=discogs_context,
                lastfm=lastfm_context,
            ),
        )
        return context.model_copy(update={"fact_collection": FactVerifier().verify_artist(context)})

    def _read_plex_album(self, *, artist: str, album: str) -> _PlexAlbumLookup:
        """Read exactly one album from Plex."""
        try:
            server = cast(
                _PlexServer,
                self._plex_server_factory(self._base_url, self._token.get_secret_value()),
            )
            return _find_album(server, artist=artist, album=album)
        except EnrichmentPipelineError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to read album from Plex."
            raise EnrichmentPipelineError(msg) from exc

    def _read_plex_artist(self, *, artist: str) -> Any:
        """Read exactly one artist from Plex."""
        try:
            server = cast(
                _PlexServer,
                self._plex_server_factory(self._base_url, self._token.get_secret_value()),
            )
            return _find_artist(server, artist=artist)
        except EnrichmentPipelineError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to read artist from Plex."
            raise EnrichmentPipelineError(msg) from exc

    def _match_musicbrainz(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> MatchResult:
        """Resolve the Plex album against MusicBrainz."""
        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ALBUMS,
                source="musicbrainz-match",
                key=f"{plex.artist}|{plex.album}|{plex.year or ''}",
                model_type=MatchResult,
            )
            if cached is not None:
                warnings.extend(cached.warnings)
                return cached

            match = self._match_musicbrainz_uncached(plex, warnings)
            self._knowledge_cache.set_model(
                kind=CacheKind.ALBUMS,
                source="musicbrainz-match",
                key=f"{plex.artist}|{plex.album}|{plex.year or ''}",
                value=match,
            )
            return match

        return self._match_musicbrainz_uncached(plex, warnings)

    def _match_musicbrainz_uncached(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> MatchResult:
        """Resolve the Plex album against MusicBrainz without the knowledge cache."""
        try:
            match = self._matcher.match_album(
                artist_name=plex.artist,
                album_title=plex.album,
                release_year=plex.year,
            )
        except Exception as exc:
            warnings.append(f"MusicBrainz matching failed: {exc}")
            return MatchResult(matched=False, confidence=0, warnings=[str(exc)])

        warnings.extend(match.warnings)
        return match

    def _musicbrainz_album(
        self,
        match: MatchResult,
        warnings: list[str],
    ) -> MusicBrainzAlbumMetadata | None:
        """Retrieve MusicBrainz release-group metadata for a match."""
        if not match.matched or match.release_group_mbid is None:
            return None

        if self._knowledge_cache is not None:
            return self._knowledge_cache.get_or_refresh(
                kind=CacheKind.ALBUMS,
                source="musicbrainz-album",
                key=match.release_group_mbid,
                model_type=MusicBrainzAlbumMetadata,
                refresh=lambda: self._musicbrainz_album_uncached(match, warnings),
            )

        return self._musicbrainz_album_uncached(match, warnings)

    def _musicbrainz_album_uncached(
        self,
        match: MatchResult,
        warnings: list[str],
    ) -> MusicBrainzAlbumMetadata | None:
        """Retrieve MusicBrainz release-group metadata without the knowledge cache."""
        try:
            return self._musicbrainz_provider.get_album_metadata(match.release_group_mbid)
        except Exception as exc:
            warnings.append(f"MusicBrainz metadata lookup failed: {exc}")
            return None

    def _match_artist(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> MusicBrainzArtistSearchResult | None:
        """Resolve the Plex artist against MusicBrainz."""
        if self._knowledge_cache is not None:
            return self._knowledge_cache.get_or_refresh(
                kind=CacheKind.ARTISTS,
                source="musicbrainz-artist-match",
                key=plex.artist,
                model_type=MusicBrainzArtistSearchResult,
                refresh=lambda: self._match_artist_uncached(plex, warnings),
            )

        return self._match_artist_uncached(plex, warnings)

    def _match_artist_uncached(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> MusicBrainzArtistSearchResult | None:
        """Resolve the Plex artist against MusicBrainz without the knowledge cache."""
        try:
            candidates = self._musicbrainz_provider.search_artist(plex.artist, limit=5)
        except Exception as exc:
            warnings.append(f"MusicBrainz artist search failed: {exc}")
            return None

        if not candidates:
            warnings.append("MusicBrainz artist match was not available.")
            return None

        exact = [
            candidate
            for candidate in candidates
            if _normalize(candidate.name) == _normalize(plex.artist)
            or any(_normalize(alias.name) == _normalize(plex.artist) for alias in candidate.aliases)
        ]
        return max(exact or candidates, key=lambda candidate: candidate.score or 0)

    def _musicbrainz_artist(
        self,
        match: MusicBrainzArtistSearchResult | None,
        warnings: list[str],
    ) -> MusicBrainzArtistMetadata | None:
        """Retrieve MusicBrainz artist metadata for a match."""
        if match is None:
            return None

        if self._knowledge_cache is not None:
            return self._knowledge_cache.get_or_refresh(
                kind=CacheKind.ARTISTS,
                source="musicbrainz-artist",
                key=match.mbid,
                model_type=MusicBrainzArtistMetadata,
                refresh=lambda: self._musicbrainz_artist_uncached(match, warnings),
            )

        return self._musicbrainz_artist_uncached(match, warnings)

    def _musicbrainz_artist_uncached(
        self,
        match: MusicBrainzArtistSearchResult,
        warnings: list[str],
    ) -> MusicBrainzArtistMetadata | None:
        """Retrieve MusicBrainz artist metadata without the knowledge cache."""
        try:
            return self._musicbrainz_provider.get_artist_metadata(match.mbid)
        except Exception as exc:
            warnings.append(f"MusicBrainz artist metadata lookup failed: {exc}")
            return None

    def _wikipedia_context(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> WikipediaAlbumContext:
        """Resolve Wikipedia summary data through the configured provider manager."""
        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ALBUMS,
                source="wikipedia-album",
                key=f"{plex.artist}|{plex.album}",
                model_type=WikipediaAlbumContext,
            )
            if cached is not None:
                return cached

            context = self._wikipedia_context_uncached(plex, warnings)
            if context.extract is not None:
                self._knowledge_cache.set_model(
                    kind=CacheKind.ALBUMS,
                    source="wikipedia-album",
                    key=f"{plex.artist}|{plex.album}",
                    value=context,
                )
            return context

        return self._wikipedia_context_uncached(plex, warnings)

    def _wikipedia_context_uncached(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> WikipediaAlbumContext:
        """Resolve Wikipedia summary data without the knowledge cache."""
        try:
            summary = self._wikipedia_provider.lookup_album(plex.artist, plex.album)
        except Exception as exc:
            warnings.append(f"Wikipedia album lookup failed: {exc}")
            summary = None

        if summary is not None:
            return WikipediaAlbumContext(
                language=summary.language,
                title=summary.title,
                extract=summary.extract,
                page_url=summary.url,
                thumbnail_url=summary.thumbnail,
            )

        metadata = self._provider_manager_album_metadata(plex, warnings)
        if metadata is not None:
            return WikipediaAlbumContext(
                language=metadata.language,
                title=metadata.title,
                extract=metadata.summary,
            )

        warnings.append("Wikipedia metadata was not available.")
        return WikipediaAlbumContext()

    def _wikipedia_artist_context(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> WikipediaArtistContext:
        """Resolve Wikipedia biography data."""
        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ARTISTS,
                source="wikipedia-artist",
                key=plex.artist,
                model_type=WikipediaArtistContext,
            )
            if cached is not None:
                return cached

            context = self._wikipedia_artist_context_uncached(plex, warnings)
            if context.extract is not None:
                self._knowledge_cache.set_model(
                    kind=CacheKind.ARTISTS,
                    source="wikipedia-artist",
                    key=plex.artist,
                    value=context,
                )
            return context

        return self._wikipedia_artist_context_uncached(plex, warnings)

    def _wikipedia_artist_context_uncached(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> WikipediaArtistContext:
        """Resolve Wikipedia biography data without the knowledge cache."""
        try:
            summary = self._wikipedia_provider.lookup_artist(plex.artist)
        except Exception as exc:
            warnings.append(f"Wikipedia artist lookup failed: {exc}")
            summary = None

        if summary is None:
            warnings.append("Wikipedia artist metadata was not available.")
            return WikipediaArtistContext()

        return WikipediaArtistContext(
            language=summary.language,
            title=summary.title,
            extract=summary.extract,
            page_url=summary.url,
            thumbnail_url=summary.thumbnail,
        )

    def _discogs_context(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> DiscogsAlbumContext:
        """Resolve optional Discogs album metadata."""
        if not self._discogs_provider.configured:
            return DiscogsAlbumContext()

        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ALBUMS,
                source="discogs-album",
                key=f"{plex.artist}|{plex.album}",
                model_type=DiscogsAlbumContext,
            )
            if cached is not None:
                return cached

            context = self._discogs_context_uncached(plex, warnings)
            if _discogs_album_has_data(context):
                self._knowledge_cache.set_model(
                    kind=CacheKind.ALBUMS,
                    source="discogs-album",
                    key=f"{plex.artist}|{plex.album}",
                    value=context,
                )
            return context

        return self._discogs_context_uncached(plex, warnings)

    def _discogs_context_uncached(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> DiscogsAlbumContext:
        """Resolve Discogs album metadata without the knowledge cache."""
        try:
            return self._discogs_provider.lookup_album(plex.artist, plex.album)
        except Exception as exc:
            warnings.append(f"Discogs album lookup failed: {exc}")
            return DiscogsAlbumContext()

    def _discogs_artist_context(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> DiscogsArtistContext:
        """Resolve optional Discogs artist metadata."""
        if not self._discogs_provider.configured:
            return DiscogsArtistContext()

        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ARTISTS,
                source="discogs-artist",
                key=plex.artist,
                model_type=DiscogsArtistContext,
            )
            if cached is not None:
                return cached

            context = self._discogs_artist_context_uncached(plex, warnings)
            if _discogs_artist_has_data(context):
                self._knowledge_cache.set_model(
                    kind=CacheKind.ARTISTS,
                    source="discogs-artist",
                    key=plex.artist,
                    value=context,
                )
            return context

        return self._discogs_artist_context_uncached(plex, warnings)

    def _discogs_artist_context_uncached(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> DiscogsArtistContext:
        """Resolve Discogs artist metadata without the knowledge cache."""
        try:
            return self._discogs_provider.lookup_artist(plex.artist)
        except Exception as exc:
            warnings.append(f"Discogs artist lookup failed: {exc}")
            return DiscogsArtistContext()

    def _lastfm_context(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> LastFMAlbumContext:
        """Resolve optional Last.fm album metadata."""
        if not self._lastfm_provider.configured:
            return LastFMAlbumContext()

        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ALBUMS,
                source="lastfm-album",
                key=f"{plex.artist}|{plex.album}",
                model_type=LastFMAlbumContext,
            )
            if cached is not None:
                return cached

            context = self._lastfm_context_uncached(plex, warnings)
            if _lastfm_album_has_data(context):
                self._knowledge_cache.set_model(
                    kind=CacheKind.ALBUMS,
                    source="lastfm-album",
                    key=f"{plex.artist}|{plex.album}",
                    value=context,
                )
            return context

        return self._lastfm_context_uncached(plex, warnings)

    def _lastfm_context_uncached(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> LastFMAlbumContext:
        """Resolve Last.fm album metadata without the knowledge cache."""
        try:
            return self._lastfm_provider.lookup_album(plex.artist, plex.album)
        except Exception as exc:
            warnings.append(f"Last.fm album lookup failed: {exc}")
            return LastFMAlbumContext()

    def _lastfm_artist_context(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> LastFMArtistContext:
        """Resolve optional Last.fm artist metadata."""
        if not self._lastfm_provider.configured:
            return LastFMArtistContext()

        if self._knowledge_cache is not None:
            cached = self._knowledge_cache.get_model(
                kind=CacheKind.ARTISTS,
                source="lastfm-artist",
                key=plex.artist,
                model_type=LastFMArtistContext,
            )
            if cached is not None:
                return cached

            context = self._lastfm_artist_context_uncached(plex, warnings)
            if _lastfm_artist_has_data(context):
                self._knowledge_cache.set_model(
                    kind=CacheKind.ARTISTS,
                    source="lastfm-artist",
                    key=plex.artist,
                    value=context,
                )
            return context

        return self._lastfm_artist_context_uncached(plex, warnings)

    def _lastfm_album_artist_context(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> LastFMArtistContext:
        """Resolve optional Last.fm artist metadata for an album context."""
        artist_context = PlexArtistContext(rating_key="", artist=plex.artist)
        return self._lastfm_artist_context(artist_context, warnings)

    def _lastfm_artist_context_uncached(
        self,
        plex: PlexArtistContext,
        warnings: list[str],
    ) -> LastFMArtistContext:
        """Resolve Last.fm artist metadata without the knowledge cache."""
        try:
            return self._lastfm_provider.lookup_artist(plex.artist)
        except Exception as exc:
            warnings.append(f"Last.fm artist lookup failed: {exc}")
            return LastFMArtistContext()

    def _provider_manager_album_metadata(
        self,
        plex: PlexAlbumContext,
        warnings: list[str],
    ) -> AlbumMetadata | None:
        """Retrieve normalized album metadata through ProviderManager."""
        try:
            return self._provider_manager.get_album_metadata(plex.artist, plex.album)
        except Exception as exc:
            warnings.append(f"Provider metadata lookup failed: {exc}")
            return None


def _find_album(server: _PlexServer, *, artist: str, album: str) -> _PlexAlbumLookup:
    """Find exactly one Plex album by artist and album title."""
    matches: list[_PlexAlbumLookup] = []
    artist_query = _normalize(artist)
    album_query = _normalize(album)

    for section in _music_sections(server.library.sections()):
        for plex_artist in _safe_items(getattr(section, "all", None)):
            if _normalize(getattr(plex_artist, "title", None)) != artist_query:
                continue

            artist_albums = _safe_items(getattr(plex_artist, "albums", None))
            for plex_album in artist_albums:
                if _normalize(getattr(plex_album, "title", None)) == album_query:
                    matches.append(
                        _PlexAlbumLookup(
                            album=plex_album,
                            artist=plex_artist,
                            artist_albums=artist_albums,
                        )
                    )

    if not matches:
        raise EnrichmentPipelineError(
            f'No Plex album named "{album}" was found for artist "{artist}".'
        )

    if len(matches) > 1:
        raise EnrichmentPipelineError(
            f'Found {len(matches)} Plex albums named "{album}" for artist "{artist}".'
        )

    return matches[0]


def _scheduled_value(result: Any, model_type: type[Any], *, warnings: list[str]) -> Any:
    """Return a scheduled provider value or an empty context model."""
    if result is None:
        return model_type()
    if result.error:
        warnings.append(f"{result.name} provider task failed: {result.error}")
    if result.value is None:
        return model_type()
    if isinstance(result.value, model_type):
        return result.value
    return model_type()


def _find_artist(server: _PlexServer, *, artist: str) -> Any:
    """Find exactly one Plex artist by title."""
    matches: list[Any] = []
    artist_query = _normalize(artist)

    for section in _music_sections(server.library.sections()):
        for plex_artist in _safe_items(getattr(section, "all", None)):
            if _normalize(getattr(plex_artist, "title", None)) == artist_query:
                matches.append(plex_artist)

    if not matches:
        raise EnrichmentPipelineError(f'No Plex artist named "{artist}" was found.')

    if len(matches) > 1:
        raise EnrichmentPipelineError(f'Found {len(matches)} Plex artists named "{artist}".')

    return matches[0]


def _plex_context(album: Any, *, requested_artist: str) -> PlexAlbumContext:
    """Convert a Plex album object to normalized context."""
    return PlexAlbumContext(
        rating_key=_string(getattr(album, "ratingKey", None)) or "",
        artist=_string(getattr(album, "parentTitle", None)) or requested_artist,
        album=_string(getattr(album, "title", None)) or "Untitled",
        year=_int(getattr(album, "year", None)),
        summary=_string(getattr(album, "summary", None)),
        genres=_tag_names(getattr(album, "genres", [])),
        styles=_tag_names(getattr(album, "styles", [])),
        moods=_tag_names(getattr(album, "moods", [])),
    )


def _plex_artist_context(artist: Any, *, requested_artist: str) -> PlexArtistContext:
    """Convert a Plex artist object to normalized context."""
    return PlexArtistContext(
        rating_key=_string(getattr(artist, "ratingKey", None)) or "",
        artist=_string(getattr(artist, "title", None)) or requested_artist,
        summary=_string(getattr(artist, "summary", None)),
        genres=_tag_names(getattr(artist, "genres", [])),
        country=_string(getattr(artist, "country", None)),
    )


def _musicbrainz_context(
    match: MatchResult,
    album: MusicBrainzAlbumMetadata | None,
) -> MusicBrainzAlbumContext:
    """Build MusicBrainz album context from match and metadata results."""
    return MusicBrainzAlbumContext(
        artist_mbid=match.artist_mbid,
        release_group_mbid=match.release_group_mbid if match.matched else None,
        release_mbid=match.release_mbid if match.matched else None,
        release_date=match.first_release_date,
        genres=album.genres if album is not None else [],
        tags=album.tags if album is not None else [],
        confidence=match.confidence,
    )


def _rich_album_fields(
    *,
    plex_album: Any,
    plex_artist: Any,
    artist_albums: list[Any],
    plex: PlexAlbumContext,
    musicbrainz: MusicBrainzAlbumContext,
    album_metadata: MusicBrainzAlbumMetadata | None,
) -> dict[str, object]:
    """Return optional rich album metadata fields from existing sources."""
    producers = _merged_list(
        _list_from_attrs(plex_album, "producers", "producer"),
        album_metadata.producers if album_metadata is not None else [],
    )
    composers = _merged_list(
        _list_from_attrs(plex_album, "composers", "composer"),
        album_metadata.composers if album_metadata is not None else [],
    )
    lyricists = _merged_list(
        _list_from_attrs(plex_album, "lyricists", "lyricist"),
        album_metadata.lyricists if album_metadata is not None else [],
    )
    labels = _merged_list(
        _list_from_attrs(plex_album, "labels", "label", "studio"),
        album_metadata.labels if album_metadata is not None else [],
    )
    studios = _merged_list(
        _list_from_attrs(plex_album, "studios", "studio"),
        album_metadata.studios if album_metadata is not None else [],
    )
    recording_locations = _merged_list(
        _list_from_attrs(plex_album, "recording_locations", "recordingLocation"),
        album_metadata.recording_locations if album_metadata is not None else [],
    )
    genres = _merged_list(musicbrainz.genres, plex.genres)
    executive_producers = _album_metadata_list(album_metadata, "executive_producers")
    arrangers = _album_metadata_list(album_metadata, "arrangers")
    orchestrators = _album_metadata_list(album_metadata, "orchestrators")
    conductors = _album_metadata_list(album_metadata, "conductors")
    mixing_engineers = _album_metadata_list(album_metadata, "mixing_engineers")
    mastering_engineers = _album_metadata_list(album_metadata, "mastering_engineers")
    sound_engineers = _album_metadata_list(album_metadata, "sound_engineers")
    featured_artists = _album_metadata_list(album_metadata, "featured_artists")
    orchestras = _album_metadata_list(album_metadata, "orchestras")
    choirs = _album_metadata_list(album_metadata, "choirs")
    publishers = _album_metadata_list(album_metadata, "publishers")

    release_type = album_metadata.release_type if album_metadata is not None else None
    return {
        "producer": _first(producers),
        "producers": producers,
        "executive_producers": executive_producers,
        "composer": _first(composers),
        "composers": composers,
        "lyricist": _first(lyricists),
        "lyricists": lyricists,
        "label": _first(labels),
        "labels": labels,
        "catalog_number": _string_from_attrs(plex_album, "catalog_number", "catalogNumber")
        or (album_metadata.catalog_number if album_metadata is not None else None),
        "barcode": _string_from_attrs(plex_album, "barcode")
        or (album_metadata.barcode if album_metadata is not None else None),
        "release_country": _string_from_attrs(plex_album, "release_country", "releaseCountry")
        or (album_metadata.release_country if album_metadata is not None else None),
        "first_release_date": (
            album_metadata.first_release_date
            if album_metadata is not None
            else musicbrainz.release_date
        ),
        "recording_period": _string_from_attrs(
            plex_album,
            "recording_period",
            "recordingPeriod",
            "recorded",
        ),
        "recording_location": _first(recording_locations),
        "studio": _first(studios),
        "studios": studios,
        "genres": genres,
        "secondary_genres": _album_metadata_list(album_metadata, "secondary_genres"),
        "tags": musicbrainz.tags,
        "release_date": musicbrainz.release_date
        or _string_from_attrs(plex_album, "originallyAvailableAt", "releaseDate"),
        "chart_positions": _list_from_attrs(
            plex_album,
            "chart_positions",
            "chartPositions",
        )
        or _album_metadata_list(album_metadata, "chart_positions"),
        "certifications": _merged_list(
            _list_from_attrs(plex_album, "certifications"),
            _album_metadata_list(album_metadata, "certifications"),
        ),
        "notable_singles": _list_from_attrs(
            plex_album,
            "notable_singles",
            "notableSingles",
            "singles",
        ),
        "guest_musicians": _list_from_attrs(
            plex_album,
            "guest_musicians",
            "guestMusicians",
            "guestArtists",
        )
        or _album_metadata_list(album_metadata, "guest_musicians"),
        "arrangers": arrangers,
        "orchestrators": orchestrators,
        "conductors": conductors,
        "mixing_engineers": mixing_engineers,
        "mastering_engineers": mastering_engineers,
        "sound_engineers": sound_engineers,
        "featured_artists": featured_artists,
        "orchestra": _first(orchestras),
        "orchestras": orchestras,
        "choir": _first(choirs),
        "choirs": choirs,
        "publisher": _first(publishers),
        "publishers": publishers,
        **_career_album_fields(
            plex_album=plex_album,
            plex_artist=plex_artist,
            artist_albums=artist_albums,
            release_type=release_type,
        ),
        **_track_editorial_fields(plex_album),
    }


def _merge_discogs_album_fields(
    fields: dict[str, object],
    discogs: DiscogsAlbumContext,
) -> dict[str, object]:
    """Merge optional Discogs album metadata without overwriting authoritative values."""
    merged = dict(fields)
    _merge_list_field(merged, "producers", discogs.producer)
    _merge_list_field(merged, "sound_engineers", discogs.engineer)
    _merge_list_field(merged, "mastering_engineers", discogs.mastering)
    _merge_list_field(merged, "mixing_engineers", discogs.mixed_by)
    _merge_list_field(merged, "labels", discogs.labels)
    _merge_list_field(merged, "guest_musicians", discogs.guest_musicians)
    _merge_list_field(merged, "featured_artists", discogs.personnel)
    _merge_list_field(merged, "studios", discogs.recording_locations)
    _merge_list_field(merged, "tags", discogs.formats)

    _fill_scalar_field(merged, "producer", _first(_object_list(merged.get("producers"))))
    _fill_scalar_field(merged, "label", discogs.label)
    _fill_scalar_field(merged, "catalog_number", discogs.catalog_number)
    _fill_scalar_field(merged, "release_country", discogs.country)
    _fill_scalar_field(merged, "recording_location", discogs.recording_location)
    _fill_scalar_field(merged, "recording_period", discogs.recording_dates)
    _fill_scalar_field(merged, "studio", _first(_object_list(merged.get("studios"))))
    return merged


def _rich_artist_fields(
    *,
    plex_artist: Any,
    plex: PlexArtistContext,
    musicbrainz: MusicBrainzArtistContext,
    wikipedia: WikipediaArtistContext,
    discogs: DiscogsArtistContext,
    lastfm: LastFMArtistContext,
) -> dict[str, object]:
    """Return optional rich artist metadata fields from existing sources."""
    aliases = _merged_list(
        musicbrainz.aliases,
        discogs.aliases,
        discogs.name_variations,
        _list_from_attrs(plex_artist, "aliases", "alias"),
    )
    genres = _merged_list(musicbrainz.genres, plex.genres, discogs.genres, lastfm.tags)
    styles = _merged_list(discogs.styles, _list_from_attrs(plex_artist, "styles"))
    members = _merged_list(discogs.members, _list_from_attrs(plex_artist, "members"))
    active_years = _string_from_attrs(plex_artist, "active_years", "yearsActive") or (
        discogs.active_years
    )
    biography = wikipedia.extract or lastfm.biography or discogs.profile or plex.summary
    return {
        "full_name": _string_from_attrs(plex_artist, "full_name", "fullName")
        or musicbrainz.artist_name,
        "aliases": aliases,
        "birth_name": _string_from_attrs(plex_artist, "birth_name", "birthName"),
        "birth_date": _string_from_attrs(plex_artist, "birth_date", "birthDate")
        or musicbrainz.begin_date,
        "death_date": _string_from_attrs(plex_artist, "death_date", "deathDate")
        or musicbrainz.end_date,
        "origin": _string_from_attrs(plex_artist, "origin", "country") or plex.country,
        "nationality": _string_from_attrs(plex_artist, "nationality") or musicbrainz.country,
        "active_years": active_years,
        "genres": genres,
        "styles": styles,
        "occupations": _list_from_attrs(plex_artist, "occupations", "occupation"),
        "members": members,
        "former_members": _list_from_attrs(plex_artist, "former_members", "formerMembers"),
        "associated_acts": _list_from_attrs(plex_artist, "associated_acts", "associatedActs"),
        "labels": _list_from_attrs(plex_artist, "labels", "label"),
        "official_website": _string_from_attrs(
            plex_artist,
            "official_website",
            "officialWebsite",
        ),
        "biography": biography,
        "career_summary": lastfm.short_biography or wikipedia.extract,
        "historical_context": wikipedia.extract,
        "influences": _list_from_attrs(plex_artist, "influences"),
        "influenced_artists": _list_from_attrs(
            plex_artist,
            "influenced_artists",
            "influencedArtists",
        ),
        "notable_albums": _list_from_attrs(plex_artist, "notable_albums", "notableAlbums"),
        "awards": _list_from_attrs(plex_artist, "awards"),
        "milestones": _list_from_attrs(plex_artist, "milestones"),
    }


def _date_range(begin: str | None, end: str | None) -> str | None:
    """Return a compact date range when at least one bound exists."""
    if begin and end:
        return f"{begin}-{end}"
    return begin or end


def _merge_list_field(fields: dict[str, object], key: str, values: list[str]) -> None:
    """Append values to an existing list field."""
    existing = _object_list(fields.get(key))
    fields[key] = _merged_list(existing, values)


def _fill_scalar_field(fields: dict[str, object], key: str, value: str | None) -> None:
    """Fill a scalar field only when it is currently empty."""
    if fields.get(key) is None and value is not None:
        fields[key] = value


def _object_list(value: object) -> list[str]:
    """Return a string list from an object known to be a list field."""
    return value if isinstance(value, list) and all(isinstance(item, str) for item in value) else []


def _discogs_album_has_data(context: DiscogsAlbumContext) -> bool:
    """Return whether Discogs album context contains useful data."""
    return any(
        (
            context.label,
            context.labels,
            context.catalog_number,
            context.catalog_numbers,
            context.country,
            context.formats,
            context.producer,
            context.engineer,
            context.mastering,
            context.mixed_by,
            context.recording_location,
            context.recording_dates,
            context.personnel,
            context.guest_musicians,
            context.credits,
            context.notes,
        )
    )


def _discogs_artist_has_data(context: DiscogsArtistContext) -> bool:
    """Return whether Discogs artist context contains useful data."""
    return any(
        (
            context.profile,
            context.members,
            context.aliases,
            context.name_variations,
            context.genres,
            context.styles,
            context.active_years,
        )
    )


def _lastfm_album_has_data(context: LastFMAlbumContext) -> bool:
    """Return whether Last.fm album context contains useful data."""
    return any(
        (
            context.summary,
            context.wiki,
            context.tags,
            context.listeners,
            context.playcount,
            context.url,
        )
    )


def _lastfm_artist_has_data(context: LastFMArtistContext) -> bool:
    """Return whether Last.fm artist context contains useful data."""
    return any(
        (
            context.biography,
            context.short_biography,
            context.tags,
            context.similar_artists,
            context.listeners,
            context.playcount,
            context.url,
        )
    )


def _default_discogs_provider() -> DiscogsProvider:
    """Create the default optional Discogs provider from settings."""
    settings = get_settings()
    return DiscogsProvider(
        token=settings.discogs.token,
        timeout_seconds=settings.discogs.timeout_seconds,
        rate_limit_seconds=settings.discogs.rate_limit_seconds,
        retries=settings.discogs.max_retries,
    )


def _default_lastfm_provider() -> LastFMProvider:
    """Create the default optional Last.fm provider from settings."""
    settings = get_settings()
    return LastFMProvider(
        api_key=settings.lastfm.api_key,
        timeout_seconds=settings.lastfm.timeout_seconds,
        rate_limit_seconds=settings.lastfm.rate_limit_seconds,
        retries=settings.lastfm.max_retries,
    )


def _career_album_fields(
    *,
    plex_album: Any,
    plex_artist: Any,
    artist_albums: list[Any],
    release_type: str | None,
) -> dict[str, object]:
    """Return optional artist career and discography context from existing data."""
    ordered_albums = _ordered_albums(artist_albums)
    position = _album_position(ordered_albums, plex_album)
    previous_album = ordered_albums[position - 1] if position is not None and position > 0 else None
    next_album = (
        ordered_albums[position + 1]
        if position is not None and position + 1 < len(ordered_albums)
        else None
    )
    sequence_number = position + 1 if position is not None else None
    is_live_album = _release_type_contains(release_type, "live") or _bool_from_attrs(
        plex_album, "is_live_album", "isLiveAlbum"
    )
    is_compilation = _release_type_contains(release_type, "compilation") or _bool_from_attrs(
        plex_album, "is_compilation", "isCompilation"
    )
    is_soundtrack = _release_type_contains(release_type, "soundtrack") or _bool_from_attrs(
        plex_album, "is_soundtrack", "isSoundtrack"
    )
    is_debut_album = _bool_from_attrs(plex_album, "is_debut_album", "isDebutAlbum") or (
        sequence_number == 1 and not is_live_album and not is_compilation and not is_soundtrack
    )
    is_final_album = _bool_from_attrs(plex_album, "is_final_album", "isFinalAlbum") or (
        sequence_number is not None
        and sequence_number == len(ordered_albums)
        and len(ordered_albums) > 1
    )
    career_phase = _string_from_sources(
        (plex_album, ("career_phase", "careerPhase")),
        (plex_artist, ("career_phase", "careerPhase")),
    )
    if career_phase is None:
        if is_debut_album:
            career_phase = "early career"
        elif is_final_album:
            career_phase = "late career"

    return {
        "artist_history": _string_from_sources(
            (plex_album, ("artist_history", "artistHistory")),
            (plex_artist, ("artist_history", "artistHistory", "history")),
        ),
        "career_phase": career_phase,
        "discography_position": _discography_position(
            sequence_number=sequence_number,
            is_live_album=is_live_album,
            is_compilation=is_compilation,
            is_soundtrack=is_soundtrack,
        ),
        "album_sequence_number": sequence_number,
        "previous_album": _album_title(previous_album),
        "previous_album_year": _album_year(previous_album),
        "next_album": _album_title(next_album),
        "next_album_year": _album_year(next_album),
        "years_active": _string_from_sources(
            (plex_album, ("years_active", "yearsActive")),
            (plex_artist, ("years_active", "yearsActive")),
        ),
        "current_lineup": _list_from_sources(
            (plex_album, ("current_lineup", "currentLineup", "lineup")),
            (plex_artist, ("current_lineup", "currentLineup", "lineup")),
        ),
        "lineup_changes": _string_from_sources(
            (plex_album, ("lineup_changes", "lineupChanges")),
            (plex_artist, ("lineup_changes", "lineupChanges")),
        ),
        "commercial_peak": _string_from_sources(
            (plex_album, ("commercial_peak", "commercialPeak")),
            (plex_artist, ("commercial_peak", "commercialPeak")),
        ),
        "genre_evolution": _string_from_sources(
            (plex_album, ("genre_evolution", "genreEvolution")),
            (plex_artist, ("genre_evolution", "genreEvolution")),
        ),
        "major_influences": _list_from_sources(
            (plex_album, ("major_influences", "majorInfluences", "influences")),
            (plex_artist, ("major_influences", "majorInfluences", "influences")),
        ),
        "historical_context": _string_from_sources(
            (plex_album, ("historical_context", "historicalContext")),
            (plex_artist, ("historical_context", "historicalContext")),
        ),
        "is_debut_album": is_debut_album,
        "is_comeback_album": _bool_from_attrs(plex_album, "is_comeback_album", "isComebackAlbum"),
        "is_final_album": is_final_album,
        "is_live_album": is_live_album,
        "is_compilation": is_compilation,
        "is_soundtrack": is_soundtrack,
    }


def _track_editorial_fields(plex_album: Any) -> dict[str, object]:
    """Return optional track-level and editorial context from existing metadata."""
    tracks = _ordered_tracks(_safe_items(getattr(plex_album, "tracks", None)))
    track_durations = [
        (track, duration) for track in tracks if (duration := _track_duration(track)) is not None
    ]
    total_duration = _duration_from_attrs(plex_album, "total_duration", "totalDuration")
    if total_duration is None and track_durations:
        total_duration = _format_duration(sum(duration for _, duration in track_durations))

    return {
        "track_count": _int_from_attrs(plex_album, "track_count", "trackCount", "leafCount")
        or (len(tracks) if tracks else None),
        "total_duration": total_duration,
        "opening_track": _track_title(tracks[0]) if tracks else None,
        "closing_track": _track_title(tracks[-1]) if tracks else None,
        "longest_track": (
            _track_title(max(track_durations, key=lambda item: item[1])[0])
            if track_durations
            else None
        ),
        "shortest_track": (
            _track_title(min(track_durations, key=lambda item: item[1])[0])
            if track_durations
            else None
        ),
        "instrumental_tracks": _list_from_attrs(
            plex_album,
            "instrumental_tracks",
            "instrumentalTracks",
        )
        or _tracks_matching_flag(tracks, "instrumental", "isInstrumental"),
        "cover_versions": _list_from_attrs(plex_album, "cover_versions", "coverVersions"),
        "notable_tracks": _list_from_attrs(plex_album, "notable_tracks", "notableTracks"),
        "singles": _list_from_attrs(plex_album, "singles"),
        "hit_singles": _list_from_attrs(plex_album, "hit_singles", "hitSingles"),
        "promotional_singles": _list_from_attrs(
            plex_album,
            "promotional_singles",
            "promotionalSingles",
        ),
        "concept_album": _bool_from_attrs(plex_album, "concept_album", "conceptAlbum"),
        "continuous_mix": _bool_from_attrs(plex_album, "continuous_mix", "continuousMix"),
        "album_highlights": _list_from_attrs(plex_album, "album_highlights", "albumHighlights"),
        "signature_song": _string_from_attrs(plex_album, "signature_song", "signatureSong"),
        "best_known_song": _string_from_attrs(plex_album, "best_known_song", "bestKnownSong"),
        "stylistic_highlights": _list_from_attrs(
            plex_album,
            "stylistic_highlights",
            "stylisticHighlights",
        ),
        "experimental_elements": _list_from_attrs(
            plex_album,
            "experimental_elements",
            "experimentalElements",
        ),
        "recurring_themes": _list_from_attrs(
            plex_album,
            "recurring_themes",
            "recurringThemes",
        ),
        "critical_consensus": _string_from_attrs(
            plex_album,
            "critical_consensus",
            "criticalConsensus",
        ),
        "commercial_summary": _string_from_attrs(
            plex_album,
            "commercial_summary",
            "commercialSummary",
        ),
        "legacy_summary": _string_from_attrs(plex_album, "legacy_summary", "legacySummary"),
    }


def _musicbrainz_artist_context(
    match: MusicBrainzArtistSearchResult | None,
    artist: MusicBrainzArtistMetadata | None,
) -> MusicBrainzArtistContext:
    """Build MusicBrainz artist context from search and metadata results."""
    artist_name = artist.name if artist is not None else match.name if match is not None else None
    country = artist.country if artist is not None else match.country if match is not None else None
    return MusicBrainzArtistContext(
        artist_mbid=match.mbid if match is not None else None,
        artist_name=artist_name,
        country=country,
        genres=artist.genres if artist is not None else match.tags if match is not None else [],
        begin_date=artist.begin_date if artist is not None else None,
        end_date=artist.end_date if artist is not None else None,
        aliases=[alias.name for alias in artist.aliases] if artist is not None else [],
        confidence=match.score if match is not None and match.score is not None else 0,
    )


def _music_sections(sections: Iterable[Any]) -> list[Any]:
    """Return music library sections."""
    return [
        section
        for section in sections
        if (getattr(section, "type", None) or getattr(section, "TYPE", None)) == "artist"
    ]


def _safe_items(method: Any) -> list[Any]:
    """Call a Plex method and return a list."""
    if not callable(method):
        return []

    result = method()
    return list(result) if result is not None else []


def _tag_names(tags: object) -> list[str]:
    """Return names from Plex tag objects."""
    if not isinstance(tags, Iterable) or isinstance(tags, str):
        return []

    names: list[str] = []
    for tag in tags:
        name = _string(tag) if isinstance(tag, str) else None
        if name is None:
            name = _string(getattr(tag, "tag", None) or getattr(tag, "title", None))
        if name is not None:
            names.append(name)

    return names


def _string_from_attrs(source: Any, *names: str) -> str | None:
    """Return the first populated string attribute."""
    for name in names:
        value = _string(getattr(source, name, None))
        if value is not None:
            return value
    return None


def _list_from_attrs(source: Any, *names: str) -> list[str]:
    """Return deduplicated strings from the first populated attributes."""
    values: list[str] = []
    for name in names:
        value = getattr(source, name, None)
        if value is None:
            continue
        if isinstance(value, str):
            values.extend(_split_structured_string(value))
            continue
        if isinstance(value, Iterable):
            values.extend(_tag_names(value))
            continue

        text = _string(value)
        if text is not None:
            values.append(text)

    return _dedupe(values)


def _split_structured_string(value: str) -> list[str]:
    """Split a simple delimited metadata string without splitting names aggressively."""
    separators = [";", "|"]
    values = [value]
    for separator in separators:
        values = [part for item in values for part in item.split(separator)]
    return [part.strip() for part in values if part.strip()]


def _merged_list(*lists: list[str]) -> list[str]:
    """Return deduplicated values across lists."""
    values: list[str] = []
    for items in lists:
        values.extend(items)
    return _dedupe(values)


def _dedupe(values: Iterable[str]) -> list[str]:
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


def _first(values: list[str]) -> str | None:
    """Return the first list item."""
    return values[0] if values else None


def _album_metadata_list(
    album_metadata: MusicBrainzAlbumMetadata | None,
    field_name: str,
) -> list[str]:
    """Return a list field from MusicBrainz album metadata."""
    if album_metadata is None:
        return []

    value = getattr(album_metadata, field_name, [])
    return value if isinstance(value, list) else []


def _ordered_albums(albums: list[Any]) -> list[Any]:
    """Return albums ordered by available year and title."""
    populated = [album for album in albums if _album_title(album) is not None]
    return sorted(
        populated,
        key=lambda album: (
            _album_year(album) is None,
            _album_year(album) or 0,
            _album_title(album),
        ),
    )


def _ordered_tracks(tracks: list[Any]) -> list[Any]:
    """Return tracks ordered by available track index."""
    populated = [track for track in tracks if _track_title(track) is not None]
    return sorted(
        populated,
        key=lambda track: (
            _int_from_attrs(track, "index", "trackNumber", "parentIndex") is None,
            _int_from_attrs(track, "index", "trackNumber", "parentIndex") or 0,
            _track_title(track),
        ),
    )


def _album_position(albums: list[Any], selected_album: Any) -> int | None:
    """Return the selected album index within a local discography."""
    selected_key = (
        _normalize(getattr(selected_album, "ratingKey", None)),
        _normalize(getattr(selected_album, "title", None)),
    )
    for index, album in enumerate(albums):
        album_key = (
            _normalize(getattr(album, "ratingKey", None)),
            _normalize(getattr(album, "title", None)),
        )
        if album is selected_album or album_key == selected_key:
            return index
    return None


def _album_title(album: Any | None) -> str | None:
    """Return an album title."""
    return None if album is None else _string(getattr(album, "title", None))


def _track_title(track: Any | None) -> str | None:
    """Return a track title."""
    return None if track is None else _string(getattr(track, "title", None))


def _track_duration(track: Any) -> int | None:
    """Return track duration in milliseconds."""
    return _int_from_attrs(track, "duration")


def _duration_from_attrs(source: Any, *names: str) -> str | None:
    """Return a human-readable duration from explicit metadata attributes."""
    for name in names:
        value = getattr(source, name, None)
        if value is None:
            continue
        if isinstance(value, int):
            return _format_duration(value)
        text = _string(value)
        if text is not None:
            return text
    return None


def _tracks_matching_flag(tracks: list[Any], *names: str) -> list[str]:
    """Return track titles for tracks with a true boolean marker."""
    return _dedupe(
        title
        for track in tracks
        if _bool_from_attrs(track, *names) and (title := _track_title(track)) is not None
    )


def _album_year(album: Any | None) -> int | None:
    """Return the most useful album year."""
    if album is None:
        return None
    for name in ("year", "originallyAvailableAt", "releaseDate"):
        value = getattr(album, name, None)
        year = _year_from_value(value)
        if year is not None:
            return year
    return None


def _year_from_value(value: object) -> int | None:
    """Return a four-digit year from an int, date, or date-like string."""
    if value is None:
        return None
    if hasattr(value, "year"):
        return _int(getattr(value, "year", None))
    text = _string(value)
    if text is None:
        return None
    return _int(text[:4]) if len(text) >= 4 else _int(text)


def _release_type_contains(release_type: str | None, needle: str) -> bool:
    """Return whether a release type contains a marker such as live or compilation."""
    return needle.casefold() in (release_type or "").casefold()


def _bool_from_attrs(source: Any, *names: str) -> bool:
    """Return a boolean from optional object attributes."""
    for name in names:
        value = getattr(source, name, None)
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().casefold() in {"1", "true", "yes"}:
            return True
    return False


def _int_from_attrs(source: Any, *names: str) -> int | None:
    """Return the first integer-like attribute."""
    for name in names:
        value = _int(getattr(source, name, None))
        if value is not None:
            return value
    return None


def _format_duration(duration_ms: int) -> str:
    """Format a millisecond duration as H:MM:SS or M:SS."""
    total_seconds = round(duration_ms / 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _discography_position(
    *,
    sequence_number: int | None,
    is_live_album: bool,
    is_compilation: bool,
    is_soundtrack: bool,
) -> str | None:
    """Return a compact discography position label."""
    if sequence_number is None:
        if is_live_album:
            return "live album"
        if is_compilation:
            return "compilation"
        if is_soundtrack:
            return "soundtrack"
        return None

    if is_live_album:
        return f"{sequence_number}. album in available discography; live album"
    if is_compilation:
        return f"{sequence_number}. album in available discography; compilation"
    if is_soundtrack:
        return f"{sequence_number}. album in available discography; soundtrack"
    return f"{sequence_number}. studio album in available discography"


def _string_from_sources(*sources: tuple[Any, tuple[str, ...]]) -> str | None:
    """Return the first populated string from multiple objects."""
    for source, names in sources:
        value = _string_from_attrs(source, *names)
        if value is not None:
            return value
    return None


def _list_from_sources(*sources: tuple[Any, tuple[str, ...]]) -> list[str]:
    """Return the first populated string list from multiple objects."""
    for source, names in sources:
        values = _list_from_attrs(source, *names)
        if values:
            return values
    return []


def _normalize(value: object) -> str:
    """Normalize a Plex title for exact matching."""
    return str(value or "").strip().casefold()


def _string(value: object) -> str | None:
    """Return a populated string."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _int(value: object) -> int | None:
    """Return an int if possible."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
