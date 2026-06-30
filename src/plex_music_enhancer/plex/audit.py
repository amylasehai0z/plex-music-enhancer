"""Read-only Plex metadata audit subsystem."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from enum import StrEnum
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr


class SummaryPresence(StrEnum):
    """Summary presence classification."""

    PRESENT = "present"
    MISSING = "missing"
    UNKNOWN = "unknown"


class SummaryLanguage(StrEnum):
    """Supported summary language classifications."""

    GERMAN = "german"
    ENGLISH = "english"
    OTHER = "other"
    UNKNOWN = "unknown"


class ArtistAuditFinding(BaseModel):
    """Audit finding for one Plex artist."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    title: str
    biography: SummaryPresence
    language: SummaryLanguage


class AlbumAuditFinding(BaseModel):
    """Audit finding for one Plex album."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    title: str
    parent_artist: str | None = Field(default=None, serialization_alias="parentArtist")
    summary: SummaryPresence
    language: SummaryLanguage


class AuditStatistics(BaseModel):
    """Aggregated audit statistics."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    artist_total: int = Field(ge=0, serialization_alias="artistTotal")
    artist_biography_present: int = Field(ge=0, serialization_alias="artistBiographyPresent")
    artist_biography_missing: int = Field(ge=0, serialization_alias="artistBiographyMissing")
    artist_biography_unknown: int = Field(ge=0, serialization_alias="artistBiographyUnknown")
    album_total: int = Field(ge=0, serialization_alias="albumTotal")
    album_summary_present: int = Field(ge=0, serialization_alias="albumSummaryPresent")
    album_summary_missing: int = Field(ge=0, serialization_alias="albumSummaryMissing")
    album_summary_unknown: int = Field(ge=0, serialization_alias="albumSummaryUnknown")
    languages: dict[str, int]


class LibraryAuditResult(BaseModel):
    """Audit results for one Plex music library."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    library_id: str = Field(serialization_alias="libraryId")
    library_title: str = Field(serialization_alias="libraryTitle")
    statistics: AuditStatistics
    artists: list[ArtistAuditFinding]
    albums: list[AlbumAuditFinding]


class MetadataAuditReport(BaseModel):
    """Complete metadata audit report."""

    model_config = ConfigDict(frozen=True)

    statistics: AuditStatistics
    libraries: list[LibraryAuditResult]
    artists: list[ArtistAuditFinding]
    albums: list[AlbumAuditFinding]


class PlexAuditError(Exception):
    """Raised when metadata audit cannot complete."""


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the audit."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the audit."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class PlexMetadataAuditor:
    """Read-only Plex metadata auditor."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex metadata auditor.

        Args:
            base_url: Base URL of the Plex server.
            token: Plex authentication token.

        """
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def audit(self) -> MetadataAuditReport:
        """Audit every configured Plex music library."""
        try:
            server = cast(_PlexServer, PlexServer(self._base_url, self._token.get_secret_value()))
            library_results = [_audit_library(section) for section in _music_sections(server)]
        except Exception as exc:
            msg = str(exc) or "Unable to audit Plex metadata."
            raise PlexAuditError(msg) from exc

        artists = [artist for library in library_results for artist in library.artists]
        albums = [album for library in library_results for album in library.albums]
        return MetadataAuditReport(
            statistics=_statistics(artists, albums),
            libraries=library_results,
            artists=artists,
            albums=albums,
        )


def _audit_library(section: Any) -> LibraryAuditResult:
    """Audit one Plex music library."""
    artists = [_artist_finding(artist) for artist in section.all()]
    albums = [_album_finding(album) for album in section.albums()]
    return LibraryAuditResult(
        library_id=str(getattr(section, "key", "")),
        library_title=str(getattr(section, "title", "Untitled")),
        statistics=_statistics(artists, albums),
        artists=artists,
        albums=albums,
    )


def _artist_finding(artist: Any) -> ArtistAuditFinding:
    """Return an audit finding for one artist."""
    summary = _optional_string(getattr(artist, "summary", None))
    presence = _presence(summary)
    return ArtistAuditFinding(
        rating_key=_optional_string(getattr(artist, "ratingKey", None)),
        title=str(getattr(artist, "title", "Untitled")),
        biography=presence,
        language=_language(summary, presence),
    )


def _album_finding(album: Any) -> AlbumAuditFinding:
    """Return an audit finding for one album."""
    summary = _optional_string(getattr(album, "summary", None))
    presence = _presence(summary)
    return AlbumAuditFinding(
        rating_key=_optional_string(getattr(album, "ratingKey", None)),
        title=str(getattr(album, "title", "Untitled")),
        parent_artist=_optional_string(getattr(album, "parentTitle", None)),
        summary=presence,
        language=_language(summary, presence),
    )


def _statistics(
    artists: list[ArtistAuditFinding],
    albums: list[AlbumAuditFinding],
) -> AuditStatistics:
    """Build aggregate statistics from findings."""
    artist_counts = Counter(artist.biography for artist in artists)
    album_counts = Counter(album.summary for album in albums)
    language_counts: Counter[SummaryLanguage] = Counter(
        album.language for album in albums if album.language is not SummaryLanguage.UNKNOWN
    )
    return AuditStatistics(
        artist_total=len(artists),
        artist_biography_present=artist_counts[SummaryPresence.PRESENT],
        artist_biography_missing=artist_counts[SummaryPresence.MISSING],
        artist_biography_unknown=artist_counts[SummaryPresence.UNKNOWN],
        album_total=len(albums),
        album_summary_present=album_counts[SummaryPresence.PRESENT],
        album_summary_missing=album_counts[SummaryPresence.MISSING],
        album_summary_unknown=album_counts[SummaryPresence.UNKNOWN],
        languages={
            SummaryLanguage.GERMAN.value: language_counts[SummaryLanguage.GERMAN],
            SummaryLanguage.ENGLISH.value: language_counts[SummaryLanguage.ENGLISH],
            SummaryLanguage.OTHER.value: language_counts[SummaryLanguage.OTHER],
        },
    )


def _music_sections(server: _PlexServer) -> list[Any]:
    """Return music library sections."""
    return [
        section
        for section in server.library.sections()
        if (getattr(section, "type", None) or getattr(section, "TYPE", None)) == "artist"
    ]


def _presence(summary: str | None) -> SummaryPresence:
    """Return summary presence classification."""
    if summary is None:
        return SummaryPresence.MISSING

    return SummaryPresence.PRESENT if summary.strip() else SummaryPresence.MISSING


def _language(summary: str | None, presence: SummaryPresence) -> SummaryLanguage:
    """Estimate summary language using deterministic keyword heuristics."""
    if presence is not SummaryPresence.PRESENT or summary is None:
        return SummaryLanguage.UNKNOWN

    text = f" {summary.casefold()} "
    german_score = _keyword_score(
        text,
        (" der ", " die ", " das ", " und ", " ist ", " mit ", " ein ", " eine ", " wurde "),
    )
    english_score = _keyword_score(
        text,
        (" the ", " and ", " is ", " with ", " a ", " an ", " was ", " were ", " from "),
    )

    if german_score == 0 and english_score == 0:
        return SummaryLanguage.OTHER
    if german_score > english_score:
        return SummaryLanguage.GERMAN
    if english_score > german_score:
        return SummaryLanguage.ENGLISH
    return SummaryLanguage.UNKNOWN


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    """Count keyword hits in text."""
    return sum(text.count(keyword) for keyword in keywords)


def _optional_string(value: object) -> str | None:
    """Return a populated string value."""
    if value is None:
        return None

    text = str(value)
    return text or None
