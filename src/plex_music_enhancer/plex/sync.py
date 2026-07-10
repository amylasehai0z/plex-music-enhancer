"""Persistent Plex library synchronization."""

from __future__ import annotations

from datetime import UTC, datetime
from os import environ
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.api.models import PlexSyncStatusResponse
from plex_music_enhancer.cache.store import DEFAULT_CACHE_ROOT
from plex_music_enhancer.config import Settings
from plex_music_enhancer.plex.scanner import _is_music_section
from plex_music_enhancer.utils.files import write_text_atomic


class PlexSyncError(Exception):
    """Raised when Plex library synchronization cannot be completed."""


class SyncedLibrary(BaseModel):
    """Persisted Plex music library metadata."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    library_id: str = Field(serialization_alias="libraryId")
    title: str
    uuid: str | None = None
    scanner: str | None = None
    agent: str | None = None


class SyncedArtist(BaseModel):
    """Persisted Plex artist metadata."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    guid: str | None = None
    summary_present: bool = Field(default=False, serialization_alias="summaryPresent")
    library_id: str = Field(serialization_alias="libraryId")
    library_title: str = Field(serialization_alias="libraryTitle")


class SyncedAlbum(BaseModel):
    """Persisted Plex album metadata."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    parent_artist: str | None = Field(default=None, serialization_alias="parentArtist")
    guid: str | None = None
    year: int | None = None
    library_id: str = Field(serialization_alias="libraryId")
    library_title: str = Field(serialization_alias="libraryTitle")


class SyncedTrack(BaseModel):
    """Persisted Plex track metadata."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    parent_artist: str | None = Field(default=None, serialization_alias="parentArtist")
    parent_album: str | None = Field(default=None, serialization_alias="parentAlbum")
    guid: str | None = None
    duration: int | None = None
    index: int | None = None
    library_id: str = Field(serialization_alias="libraryId")
    library_title: str = Field(serialization_alias="libraryTitle")


class PlexSyncSnapshot(BaseModel):
    """Persisted Plex sync snapshot."""

    model_config = ConfigDict(frozen=True)

    synced_at: datetime = Field(serialization_alias="syncedAt")
    libraries: list[SyncedLibrary] = Field(default_factory=list)
    artists: list[SyncedArtist] = Field(default_factory=list)
    albums: list[SyncedAlbum] = Field(default_factory=list)
    tracks: list[SyncedTrack] = Field(default_factory=list)

    def status(self, *, running: bool = False, progress: int = 100) -> PlexSyncStatusResponse:
        """Return the public status represented by this snapshot."""
        return PlexSyncStatusResponse(
            running=running,
            progress=progress,
            libraries=len(self.libraries),
            artists=len(self.artists),
            albums=len(self.albums),
            tracks=len(self.tracks),
            last_sync=self.synced_at,
        )


class _PlexLibrary(Protocol):
    """Minimal Plex library API required by synchronization."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API required by synchronization."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class PlexSyncStore:
    """JSON store for persistent Plex sync snapshots."""

    def __init__(self, path: Path) -> None:
        """Create a sync store."""
        self.path = path

    @classmethod
    def default(cls) -> PlexSyncStore:
        """Return the sync store inside the configured cache volume."""
        return cls(_default_sync_path())

    def load(self) -> PlexSyncSnapshot | None:
        """Return the persisted snapshot when available and valid."""
        if not self.path.exists():
            return None
        try:
            return PlexSyncSnapshot.model_validate_json(self.path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def save(self, snapshot: PlexSyncSnapshot) -> None:
        """Persist a sync snapshot atomically."""
        write_text_atomic(
            self.path,
            snapshot.model_dump_json(indent=2),
        )


class PlexLibrarySyncService:
    """Synchronize Plex music library metadata into the local cache."""

    def __init__(
        self, *, settings: Settings | None = None, store: PlexSyncStore | None = None
    ) -> None:
        """Create a Plex sync service."""
        self._settings = settings
        self._store = store or PlexSyncStore.default()
        self._lock = Lock()
        self._status = self._stored_status()

    def status(self) -> PlexSyncStatusResponse:
        """Return the current synchronization status."""
        with self._lock:
            return self._status

    def snapshot(self) -> PlexSyncSnapshot | None:
        """Return the persisted sync snapshot when available."""
        return self._store.load()

    def start(self) -> PlexSyncStatusResponse:
        """Start a background synchronization job and return current status."""
        self._require_configured_settings()
        with self._lock:
            if self._status.running:
                return self._status
            self._status = self._status.model_copy(
                update={"running": True, "progress": 0, "error": None}
            )

        thread = Thread(target=self._run_background, name="plex-library-sync", daemon=True)
        thread.start()
        return self.status()

    def sync_now(self) -> PlexSyncStatusResponse:
        """Run synchronization synchronously for tests and CLI-adjacent services."""
        self._require_configured_settings()
        with self._lock:
            self._status = self._status.model_copy(
                update={"running": True, "progress": 0, "error": None}
            )

        try:
            snapshot = self._collect_snapshot()
        except Exception as exc:
            message = str(exc) or "Plex synchronization failed."
            with self._lock:
                self._status = self._status.model_copy(
                    update={"running": False, "progress": 0, "error": message}
                )
                return self._status

        self._store.save(snapshot)
        with self._lock:
            self._status = snapshot.status()
            return self._status

    def _run_background(self) -> None:
        """Execute a background synchronization job."""
        self.sync_now()

    def _collect_snapshot(self) -> PlexSyncSnapshot:
        """Collect a full Plex music library snapshot."""
        settings = self._require_configured_settings()

        server = cast(
            _PlexServer,
            PlexServer(str(settings.plex_url).rstrip("/"), settings.plex_token.get_secret_value()),
        )
        sections = [section for section in server.library.sections() if _is_music_section(section)]
        total_steps = max(len(sections) * 3, 1)
        completed_steps = 0

        libraries: list[SyncedLibrary] = []
        artists: list[SyncedArtist] = []
        albums: list[SyncedAlbum] = []
        tracks: list[SyncedTrack] = []

        for section in sections:
            library_id = _string(getattr(section, "key", ""))
            library_title = _string(getattr(section, "title", "Untitled"))
            libraries.append(
                SyncedLibrary(
                    library_id=library_id,
                    title=library_title,
                    uuid=_optional_string(getattr(section, "uuid", None)),
                    scanner=_optional_string(getattr(section, "scanner", None)),
                    agent=_optional_string(getattr(section, "agent", None)),
                )
            )

            artists.extend(
                _artist_item(artist, library_id=library_id, library_title=library_title)
                for artist in section.all()
            )
            completed_steps += 1
            self._update_progress(completed_steps, total_steps, artists, albums, tracks, libraries)

            albums.extend(
                _album_item(album, library_id=library_id, library_title=library_title)
                for album in section.albums()
            )
            completed_steps += 1
            self._update_progress(completed_steps, total_steps, artists, albums, tracks, libraries)

            tracks.extend(
                _track_item(track, library_id=library_id, library_title=library_title)
                for track in section.searchTracks()
            )
            completed_steps += 1
            self._update_progress(completed_steps, total_steps, artists, albums, tracks, libraries)

        return PlexSyncSnapshot(
            synced_at=datetime.now(UTC),
            libraries=libraries,
            artists=artists,
            albums=albums,
            tracks=tracks,
        )

    def _require_configured_settings(self) -> Settings:
        """Return settings when Plex connection details are present."""
        settings = self._settings or Settings()
        if settings.plex_url is None or settings.plex_token is None:
            msg = "Plex URL and token are required before synchronization."
            raise PlexSyncError(msg)
        return settings

    def _update_progress(
        self,
        completed_steps: int,
        total_steps: int,
        artists: list[SyncedArtist],
        albums: list[SyncedAlbum],
        tracks: list[SyncedTrack],
        libraries: list[SyncedLibrary],
    ) -> None:
        """Update public progress without exposing Plex credentials."""
        progress = min(99, int((completed_steps / total_steps) * 100))
        with self._lock:
            self._status = self._status.model_copy(
                update={
                    "running": True,
                    "progress": progress,
                    "libraries": len(libraries),
                    "artists": len(artists),
                    "albums": len(albums),
                    "tracks": len(tracks),
                    "error": None,
                }
            )

    def _stored_status(self) -> PlexSyncStatusResponse:
        """Return status from persisted sync data."""
        snapshot = self._store.load()
        if snapshot is None:
            return PlexSyncStatusResponse()
        return snapshot.status()


def _artist_item(artist: Any, *, library_id: str, library_title: str) -> SyncedArtist:
    """Return a persisted artist item."""
    return SyncedArtist(
        rating_key=_string(getattr(artist, "ratingKey", "")),
        title=_string(getattr(artist, "title", "Untitled")),
        guid=_optional_string(getattr(artist, "guid", None)),
        summary_present=bool(_optional_string(getattr(artist, "summary", None))),
        library_id=library_id,
        library_title=library_title,
    )


def _album_item(album: Any, *, library_id: str, library_title: str) -> SyncedAlbum:
    """Return a persisted album item."""
    return SyncedAlbum(
        rating_key=_string(getattr(album, "ratingKey", "")),
        title=_string(getattr(album, "title", "Untitled")),
        parent_artist=_optional_string(getattr(album, "parentTitle", None)),
        guid=_optional_string(getattr(album, "guid", None)),
        year=_optional_int(getattr(album, "year", None)),
        library_id=library_id,
        library_title=library_title,
    )


def _track_item(track: Any, *, library_id: str, library_title: str) -> SyncedTrack:
    """Return a persisted track item."""
    return SyncedTrack(
        rating_key=_string(getattr(track, "ratingKey", "")),
        title=_string(getattr(track, "title", "Untitled")),
        parent_artist=_optional_string(getattr(track, "grandparentTitle", None)),
        parent_album=_optional_string(getattr(track, "parentTitle", None)),
        guid=_optional_string(getattr(track, "guid", None)),
        duration=_optional_int(getattr(track, "duration", None)),
        index=_optional_int(getattr(track, "index", None)),
        library_id=library_id,
        library_title=library_title,
    )


def _default_sync_path() -> Path:
    """Return the persistent sync path inside the configured cache root."""
    raw_path = environ.get("PLEX_ENHANCER_CACHE")
    root = Path(raw_path).expanduser() if raw_path else DEFAULT_CACHE_ROOT
    return root / "plex" / "sync.json"


def _string(value: object) -> str:
    """Return a non-empty string representation."""
    text = str(value) if value is not None else ""
    return text or "Untitled"


def _optional_string(value: object) -> str | None:
    """Return a string when Plex exposes a populated value."""
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_int(value: object) -> int | None:
    """Return an integer when Plex exposes one."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "PlexLibrarySyncService",
    "PlexSyncError",
    "PlexSyncSnapshot",
    "PlexSyncStatusResponse",
    "PlexSyncStore",
    "SyncedAlbum",
    "SyncedArtist",
    "SyncedLibrary",
    "SyncedTrack",
]
