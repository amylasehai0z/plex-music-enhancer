"""Typed models for normalized album enrichment context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.knowledge.models import KnowledgeGraph
from plex_music_enhancer.verification.models import FactCollection


class PlexAlbumContext(BaseModel):
    """Metadata read directly from one Plex album."""

    model_config = ConfigDict(frozen=True)

    rating_key: str
    artist: str
    album: str
    year: int | None = None
    summary: str | None = None
    genres: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)


class PlexArtistContext(BaseModel):
    """Metadata read directly from one Plex artist."""

    model_config = ConfigDict(frozen=True)

    rating_key: str
    artist: str
    summary: str | None = None
    genres: list[str] = Field(default_factory=list)
    country: str | None = None


class MusicBrainzAlbumContext(BaseModel):
    """MusicBrainz identity and metadata for one album."""

    model_config = ConfigDict(frozen=True)

    artist_mbid: str | None = None
    release_group_mbid: str | None = None
    release_mbid: str | None = None
    release_date: str | None = None
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)


class MusicBrainzArtistContext(BaseModel):
    """MusicBrainz identity and metadata for one artist."""

    model_config = ConfigDict(frozen=True)

    artist_mbid: str | None = None
    artist_name: str | None = None
    country: str | None = None
    genres: list[str] = Field(default_factory=list)
    begin_date: str | None = None
    end_date: str | None = None
    aliases: list[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)


class WikipediaAlbumContext(BaseModel):
    """Wikipedia summary metadata for one album."""

    model_config = ConfigDict(frozen=True)

    language: str | None = None
    title: str | None = None
    extract: str | None = None
    page_url: str | None = None
    thumbnail_url: str | None = None


class WikipediaArtistContext(BaseModel):
    """Wikipedia biography metadata for one artist."""

    model_config = ConfigDict(frozen=True)

    language: str | None = None
    title: str | None = None
    extract: str | None = None
    page_url: str | None = None
    thumbnail_url: str | None = None


class DiscogsArtistContext(BaseModel):
    """Discogs artist metadata used as optional enrichment context."""

    model_config = ConfigDict(frozen=True)

    profile: str | None = None
    members: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    name_variations: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    active_years: str | None = None


class DiscogsAlbumContext(BaseModel):
    """Discogs album metadata used as optional enrichment context."""

    model_config = ConfigDict(frozen=True)

    label: str | None = None
    labels: list[str] = Field(default_factory=list)
    catalog_number: str | None = None
    catalog_numbers: list[str] = Field(default_factory=list)
    country: str | None = None
    formats: list[str] = Field(default_factory=list)
    producer: list[str] = Field(default_factory=list)
    engineer: list[str] = Field(default_factory=list)
    mastering: list[str] = Field(default_factory=list)
    mixed_by: list[str] = Field(default_factory=list)
    photography: list[str] = Field(default_factory=list)
    artwork: list[str] = Field(default_factory=list)
    design: list[str] = Field(default_factory=list)
    recording_location: str | None = None
    recording_locations: list[str] = Field(default_factory=list)
    recording_dates: str | None = None
    personnel: list[str] = Field(default_factory=list)
    guest_musicians: list[str] = Field(default_factory=list)
    credits: list[str] = Field(default_factory=list)
    notes: str | None = None


class LastFMArtistContext(BaseModel):
    """Last.fm artist metadata used as optional community enrichment context."""

    model_config = ConfigDict(frozen=True)

    biography: str | None = None
    short_biography: str | None = None
    tags: list[str] = Field(default_factory=list)
    similar_artists: list[str] = Field(default_factory=list)
    listeners: int | None = None
    playcount: int | None = None
    url: str | None = None


class LastFMAlbumContext(BaseModel):
    """Last.fm album metadata used as optional community enrichment context."""

    model_config = ConfigDict(frozen=True)

    summary: str | None = None
    wiki: str | None = None
    tags: list[str] = Field(default_factory=list)
    listeners: int | None = None
    playcount: int | None = None
    url: str | None = None


class PipelineContext(BaseModel):
    """Pipeline status after collecting and validating album context."""

    model_config = ConfigDict(frozen=True)

    collected_sources: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ready_for_generation: bool = False


class AlbumContext(BaseModel):
    """Normalized context document for preview, AI generation, apply, and rollback."""

    model_config = ConfigDict(frozen=True)

    plex: PlexAlbumContext
    musicbrainz: MusicBrainzAlbumContext
    wikipedia: WikipediaAlbumContext
    discogs: DiscogsAlbumContext = Field(default_factory=DiscogsAlbumContext)
    lastfm: LastFMAlbumContext = Field(default_factory=LastFMAlbumContext)
    lastfm_artist: LastFMArtistContext = Field(default_factory=LastFMArtistContext)
    pipeline: PipelineContext
    producer: str | None = None
    producers: list[str] = Field(default_factory=list)
    composer: str | None = None
    composers: list[str] = Field(default_factory=list)
    lyricist: str | None = None
    lyricists: list[str] = Field(default_factory=list)
    label: str | None = None
    labels: list[str] = Field(default_factory=list)
    catalog_number: str | None = None
    barcode: str | None = None
    release_country: str | None = None
    first_release_date: str | None = None
    recording_period: str | None = None
    recording_location: str | None = None
    studio: str | None = None
    studios: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    secondary_genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    release_date: str | None = None
    chart_positions: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    notable_singles: list[str] = Field(default_factory=list)
    guest_musicians: list[str] = Field(default_factory=list)
    executive_producers: list[str] = Field(default_factory=list)
    arrangers: list[str] = Field(default_factory=list)
    orchestrators: list[str] = Field(default_factory=list)
    conductors: list[str] = Field(default_factory=list)
    mixing_engineers: list[str] = Field(default_factory=list)
    mastering_engineers: list[str] = Field(default_factory=list)
    sound_engineers: list[str] = Field(default_factory=list)
    featured_artists: list[str] = Field(default_factory=list)
    orchestra: str | None = None
    orchestras: list[str] = Field(default_factory=list)
    choir: str | None = None
    choirs: list[str] = Field(default_factory=list)
    publisher: str | None = None
    publishers: list[str] = Field(default_factory=list)
    artist_history: str | None = None
    career_phase: str | None = None
    discography_position: str | None = None
    album_sequence_number: int | None = None
    previous_album: str | None = None
    previous_album_year: int | None = None
    next_album: str | None = None
    next_album_year: int | None = None
    years_active: str | None = None
    current_lineup: list[str] = Field(default_factory=list)
    lineup_changes: str | None = None
    commercial_peak: str | None = None
    genre_evolution: str | None = None
    major_influences: list[str] = Field(default_factory=list)
    historical_context: str | None = None
    is_debut_album: bool = False
    is_comeback_album: bool = False
    is_final_album: bool = False
    is_live_album: bool = False
    is_compilation: bool = False
    is_soundtrack: bool = False
    track_count: int | None = None
    total_duration: str | None = None
    opening_track: str | None = None
    closing_track: str | None = None
    longest_track: str | None = None
    shortest_track: str | None = None
    instrumental_tracks: list[str] = Field(default_factory=list)
    cover_versions: list[str] = Field(default_factory=list)
    notable_tracks: list[str] = Field(default_factory=list)
    singles: list[str] = Field(default_factory=list)
    hit_singles: list[str] = Field(default_factory=list)
    promotional_singles: list[str] = Field(default_factory=list)
    concept_album: bool = False
    continuous_mix: bool = False
    album_highlights: list[str] = Field(default_factory=list)
    signature_song: str | None = None
    best_known_song: str | None = None
    stylistic_highlights: list[str] = Field(default_factory=list)
    experimental_elements: list[str] = Field(default_factory=list)
    recurring_themes: list[str] = Field(default_factory=list)
    critical_consensus: str | None = None
    commercial_summary: str | None = None
    legacy_summary: str | None = None
    knowledge_graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)
    fact_collection: FactCollection = Field(default_factory=FactCollection)


class ArtistContext(BaseModel):
    """Normalized artist context document for preview, review, and apply."""

    model_config = ConfigDict(frozen=True)

    plex: PlexArtistContext
    musicbrainz: MusicBrainzArtistContext
    wikipedia: WikipediaArtistContext
    discogs: DiscogsArtistContext = Field(default_factory=DiscogsArtistContext)
    lastfm: LastFMArtistContext = Field(default_factory=LastFMArtistContext)
    pipeline: PipelineContext
    full_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    birth_name: str | None = None
    birth_date: str | None = None
    death_date: str | None = None
    origin: str | None = None
    nationality: str | None = None
    active_years: str | None = None
    genres: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    occupations: list[str] = Field(default_factory=list)
    members: list[str] = Field(default_factory=list)
    former_members: list[str] = Field(default_factory=list)
    associated_acts: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    official_website: str | None = None
    biography: str | None = None
    career_summary: str | None = None
    historical_context: str | None = None
    influences: list[str] = Field(default_factory=list)
    influenced_artists: list[str] = Field(default_factory=list)
    notable_albums: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    fact_collection: FactCollection = Field(default_factory=FactCollection)
