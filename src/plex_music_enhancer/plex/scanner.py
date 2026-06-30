"""Read-only Plex library scanner."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sized
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr


class MusicLibraryStats(BaseModel):
    """Statistics collected for a Plex music library."""

    model_config = ConfigDict(frozen=True)

    library_id: str = Field(description="Plex library identifier.")
    library_title: str = Field(description="Plex library title.")
    library_uuid: str | None = Field(default=None, description="Plex library UUID.")
    scanner: str | None = Field(
        default=None,
        description="Plex scanner configured for the library.",
    )
    agent: str | None = Field(
        default=None,
        description="Plex metadata agent configured for the library.",
    )
    artist_count: int = Field(ge=0, description="Number of artists in the library.")
    album_count: int = Field(ge=0, description="Number of albums in the library.")
    track_count: int = Field(ge=0, description="Number of tracks in the library.")


class MusicLibraryScanExport(BaseModel):
    """JSON export payload for a music library scan."""

    model_config = ConfigDict(frozen=True)

    libraries: list[MusicLibraryStats]


class ArtistScanItem(BaseModel):
    """Exported Plex artist data."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    guid: str | None = None
    summary: str | None = None
    genres: list[str] = Field(default_factory=list)
    country: str | None = None
    artwork_url: str | None = Field(default=None, serialization_alias="artworkUrl")
    thumb_url: str | None = Field(default=None, serialization_alias="thumbUrl")
    album_count: int = Field(ge=0, serialization_alias="albumCount")


class ArtistScanExport(BaseModel):
    """JSON export payload for an artist scan."""

    model_config = ConfigDict(frozen=True)

    artists: list[ArtistScanItem]


class AlbumScanItem(BaseModel):
    """Exported Plex album data."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    parent_artist: str | None = Field(default=None, serialization_alias="parentArtist")
    guid: str | None = None
    year: int | None = None
    originally_available_at: str | None = Field(
        default=None,
        serialization_alias="originallyAvailableAt",
    )
    summary: str | None = None
    genres: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    leaf_count: int = Field(ge=0, serialization_alias="leafCount")
    thumb: str | None = None
    artwork: str | None = None


class AlbumScanExport(BaseModel):
    """JSON export payload for an album scan."""

    model_config = ConfigDict(frozen=True)

    albums: list[AlbumScanItem]


class PlexScannerError(Exception):
    """Raised when the Plex scanner cannot complete."""


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the scanner."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the scanner."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class PlexMusicScanner:
    """Read-only scanner for Plex music library statistics."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex music scanner.

        Args:
            base_url: Base URL of the Plex server.
            token: Plex authentication token.

        """
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def scan_libraries(self) -> MusicLibraryScanExport:
        """Scan all Plex libraries and return music-library statistics."""
        try:
            sections = self._music_sections()
            libraries = [self._scan_music_section(section) for section in sections]
        except Exception as exc:
            msg = str(exc) or "Unable to connect to Plex."
            raise PlexScannerError(msg) from exc

        return MusicLibraryScanExport(libraries=libraries)

    def scan_artists(
        self,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ArtistScanExport:
        """Scan every artist from every music library."""
        try:
            artists = [
                self._scan_artist(artist, progress_callback)
                for section in self._music_sections()
                for artist in section.all()
            ]
        except Exception as exc:
            msg = str(exc) or "Unable to scan Plex artists."
            raise PlexScannerError(msg) from exc

        return ArtistScanExport(artists=artists)

    def scan_albums(self) -> AlbumScanExport:
        """Scan every album from every music library."""
        try:
            albums = [
                self._scan_album(album)
                for section in self._music_sections()
                for album in section.albums()
            ]
        except Exception as exc:
            msg = str(exc) or "Unable to scan Plex albums."
            raise PlexScannerError(msg) from exc

        return AlbumScanExport(albums=albums)

    def scan(self) -> MusicLibraryScanExport:
        """Scan Plex music libraries.

        This alias keeps the public scanner API compact while `scan_libraries`
        leaves room for future scanner methods such as artists, albums, and tracks.
        """
        return self.scan_libraries()

    def _music_sections(self) -> list[Any]:
        """Return all music library sections from Plex."""
        server = cast(_PlexServer, PlexServer(self._base_url, self._token.get_secret_value()))
        return [section for section in server.library.sections() if _is_music_section(section)]

    @staticmethod
    def _scan_music_section(section: Any) -> MusicLibraryStats:
        """Collect statistics for one Plex music section."""
        return MusicLibraryStats(
            library_id=str(getattr(section, "key", "")),
            library_title=str(getattr(section, "title", "Untitled")),
            library_uuid=_optional_string(getattr(section, "uuid", None)),
            scanner=_optional_string(getattr(section, "scanner", None)),
            agent=_optional_string(getattr(section, "agent", None)),
            artist_count=_count_items(section.all()),
            album_count=_count_items(section.albums()),
            track_count=_count_items(section.searchTracks()),
        )

    @staticmethod
    def _scan_artist(
        artist: Any,
        progress_callback: Callable[[str], None] | None,
    ) -> ArtistScanItem:
        """Collect export data for one Plex artist."""
        title = str(getattr(artist, "title", "Untitled"))
        if progress_callback is not None:
            progress_callback(title)

        return ArtistScanItem(
            rating_key=str(getattr(artist, "ratingKey", "")),
            title=title,
            guid=_optional_string(getattr(artist, "guid", None)),
            summary=_optional_string(getattr(artist, "summary", None)),
            genres=_tag_names(getattr(artist, "genres", [])),
            country=_artist_country(artist),
            artwork_url=_optional_string(getattr(artist, "art", None)),
            thumb_url=_optional_string(getattr(artist, "thumb", None)),
            album_count=_count_items(artist.albums()),
        )

    @staticmethod
    def _scan_album(album: Any) -> AlbumScanItem:
        """Collect export data for one Plex album."""
        return AlbumScanItem(
            rating_key=str(getattr(album, "ratingKey", "")),
            title=str(getattr(album, "title", "Untitled")),
            parent_artist=_optional_string(getattr(album, "parentTitle", None)),
            guid=_optional_string(getattr(album, "guid", None)),
            year=_optional_int(getattr(album, "year", None)),
            originally_available_at=_optional_string(getattr(album, "originallyAvailableAt", None)),
            summary=_optional_string(getattr(album, "summary", None)),
            genres=_tag_names(getattr(album, "genres", [])),
            styles=_tag_names(getattr(album, "styles", [])),
            moods=_tag_names(getattr(album, "moods", [])),
            leaf_count=_optional_int(getattr(album, "leafCount", None)) or 0,
            thumb=_optional_string(getattr(album, "thumb", None)),
            artwork=_optional_string(getattr(album, "art", None)),
        )


def _is_music_section(section: Any) -> bool:
    """Return whether a Plex library section is a music library."""
    section_type = getattr(section, "type", None) or getattr(section, "TYPE", None)
    return section_type == "artist"


def _count_items(items: Sized | Iterable[object]) -> int:
    """Return the number of items in a Plex collection response."""
    if isinstance(items, Sized):
        return len(items)

    return sum(1 for _item in items)


def _optional_string(value: object) -> str | None:
    """Return a string value when Plex exposes a populated attribute."""
    if value is None:
        return None

    text = str(value)
    return text or None


def _optional_int(value: object) -> int | None:
    """Return an integer value when Plex exposes a populated numeric attribute."""
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _tag_names(values: object) -> list[str]:
    """Return Plex tag labels as strings."""
    if values is None:
        return []

    if isinstance(values, str):
        return [values]

    return [
        text
        for value in cast(Iterable[object], values)
        if (text := _optional_string(getattr(value, "tag", value))) is not None
    ]


def _artist_country(artist: Any) -> str | None:
    """Return an artist country when Plex exposes one."""
    country = _optional_string(getattr(artist, "country", None))
    if country is not None:
        return country

    countries = _tag_names(getattr(artist, "countries", []))
    return countries[0] if countries else None
