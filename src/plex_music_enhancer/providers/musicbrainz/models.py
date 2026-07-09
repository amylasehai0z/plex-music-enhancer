"""Typed MusicBrainz provider models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MusicBrainzLifeSpan(BaseModel):
    """MusicBrainz artist life-span dates."""

    model_config = ConfigDict(frozen=True)

    begin: str | None = None
    end: str | None = None
    ended: bool | None = None


class MusicBrainzAlias(BaseModel):
    """MusicBrainz alias entry."""

    model_config = ConfigDict(frozen=True)

    name: str
    sort_name: str | None = None
    locale: str | None = None
    primary: bool | None = None
    type: str | None = None


class MusicBrainzArtistSearchResult(BaseModel):
    """Artist search result from MusicBrainz."""

    model_config = ConfigDict(frozen=True)

    mbid: str
    name: str
    sort_name: str | None = None
    country: str | None = None
    disambiguation: str | None = None
    tags: list[str] = Field(default_factory=list)
    aliases: list[MusicBrainzAlias] = Field(default_factory=list)
    life_span: MusicBrainzLifeSpan | None = None
    score: int | None = None


class MusicBrainzAlbumSearchResult(BaseModel):
    """Album search result from MusicBrainz."""

    model_config = ConfigDict(frozen=True)

    release_group_mbid: str
    release_mbid: str | None = None
    title: str
    artist_name: str | None = None
    first_release_date: str | None = None
    primary_type: str | None = None
    secondary_types: list[str] = Field(default_factory=list)
    score: int | None = None


class MusicBrainzArtistMetadata(BaseModel):
    """Detailed artist metadata from MusicBrainz."""

    model_config = ConfigDict(frozen=True)

    mbid: str
    name: str
    biography: str | None = None
    country: str | None = None
    genres: list[str] = Field(default_factory=list)
    begin_date: str | None = None
    end_date: str | None = None
    aliases: list[MusicBrainzAlias] = Field(default_factory=list)


class MusicBrainzAlbumMetadata(BaseModel):
    """Detailed album metadata from MusicBrainz."""

    model_config = ConfigDict(frozen=True)

    mbid: str
    title: str
    artist: str | None = None
    year: int | None = None
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    release_type: str | None = None
    catalog_number: str | None = None
    barcode: str | None = None
    release_country: str | None = None
    first_release_date: str | None = None
    producers: list[str] = Field(default_factory=list)
    executive_producers: list[str] = Field(default_factory=list)
    composers: list[str] = Field(default_factory=list)
    lyricists: list[str] = Field(default_factory=list)
    arrangers: list[str] = Field(default_factory=list)
    orchestrators: list[str] = Field(default_factory=list)
    conductors: list[str] = Field(default_factory=list)
    mixing_engineers: list[str] = Field(default_factory=list)
    mastering_engineers: list[str] = Field(default_factory=list)
    sound_engineers: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    recording_locations: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    guest_musicians: list[str] = Field(default_factory=list)
    featured_artists: list[str] = Field(default_factory=list)
    orchestra: str | None = None
    orchestras: list[str] = Field(default_factory=list)
    choir: str | None = None
    choirs: list[str] = Field(default_factory=list)
    publisher: str | None = None
    publishers: list[str] = Field(default_factory=list)
    secondary_genres: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    chart_positions: list[str] = Field(default_factory=list)
