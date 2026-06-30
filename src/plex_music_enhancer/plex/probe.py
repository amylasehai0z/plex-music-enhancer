"""Plex write capability probes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from traceback import format_exception
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

SUMMARY_FIELD = "summary"
TEST_SUMMARY_PREFIX = "PLEX_MUSIC_ENHANCER_TEST"
TARGET_TYPES = ("artist", "album")
_MISSING = object()


class SummaryWriteCapability(BaseModel):
    """Summary write capability for a sampled Plex metadata object."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    object_type: str = Field(serialization_alias="objectType")
    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    title: str | None = None
    supported_edit_methods: list[str] = Field(serialization_alias="supportedEditMethods")
    writable_fields: list[str] = Field(serialization_alias="writableFields")
    read_only_fields: list[str] = Field(serialization_alias="readOnlyFields")
    lower_level_http_required: bool = Field(serialization_alias="lowerLevelHttpRequired")
    explanation: str


class WriteCapabilityReport(BaseModel):
    """Read-only report describing Plex summary write support."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    plex_version: str | None = Field(default=None, serialization_alias="plexVersion")
    plexapi_version: str | None = Field(default=None, serialization_alias="plexapiVersion")
    capabilities: list[SummaryWriteCapability]


class AlbumWriteVerificationReport(BaseModel):
    """Result of a targeted album summary write verification."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    status: str
    executed: bool
    library: str | None = None
    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    title: str | None = None
    artist: str
    album: str
    current_summary: str | None = Field(default=None, serialization_alias="currentSummary")
    available_edit_methods: list[str] = Field(serialization_alias="availableEditMethods")
    edit_summary_exists: bool = Field(serialization_alias="editSummaryExists")
    original_summary_length: int = Field(serialization_alias="originalSummaryLength")
    temporary_summary: str | None = Field(default=None, serialization_alias="temporarySummary")
    summary_after_reload: str | None = Field(default=None, serialization_alias="summaryAfterReload")
    restore_status: str | None = Field(default=None, serialization_alias="restoreStatus")
    final_verification: bool | None = Field(default=None, serialization_alias="finalVerification")
    temporary_summary_verified: bool | None = Field(
        default=None,
        serialization_alias="temporarySummaryVerified",
    )
    original_summary_restored: bool | None = Field(
        default=None,
        serialization_alias="originalSummaryRestored",
    )
    exception: str | None = None
    explanation: str


class PlexProbeError(Exception):
    """Raised when a write capability probe cannot be prepared."""


@dataclass(frozen=True)
class _AlbumLookup:
    """Located Plex album and its source library."""

    album: Any
    library_title: str | None


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the probe."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the probe."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class PlexWriteProbe:
    """Plex write capability probe."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex write probe.

        Args:
            base_url: Base URL of the Plex server.
            token: Plex authentication token.

        """
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def analyze_summary_writes(self) -> WriteCapabilityReport:
        """Analyze whether Artist.summary and Album.summary appear writable."""
        try:
            server = cast(_PlexServer, PlexServer(self._base_url, self._token.get_secret_value()))
            music_sections = _music_sections(server.library.sections())
            samples = {
                "artist": _first_from_sections(music_sections, "all"),
                "album": _first_from_sections(music_sections, "albums"),
            }
            return WriteCapabilityReport(
                plex_version=_optional_string(getattr(server, "version", None)),
                plexapi_version=_plexapi_version(),
                capabilities=[
                    _analyze_summary_capability(object_type, plex_object)
                    for object_type, plex_object in samples.items()
                    if plex_object is not None
                ],
            )
        except Exception as exc:
            msg = str(exc) or "Unable to analyze Plex write capabilities."
            raise PlexProbeError(msg) from exc

    def verify_album_summary(
        self,
        *,
        artist_name: str,
        album_title: str,
        execute: bool,
    ) -> AlbumWriteVerificationReport:
        """Verify whether a selected album summary can be edited.

        The default mode only locates the album and reports available methods. When
        execute is true, the method writes a temporary summary through
        ``album.editSummary()``, saves, reloads, compares, and restores the original
        summary before returning.

        Args:
            artist_name: Exact artist title to locate.
            album_title: Exact album title to locate under the artist.
            execute: Whether to perform the reversible write verification.

        Returns:
            A typed verification report.

        Raises:
            PlexProbeError: If Plex cannot be reached or the album lookup is
                ambiguous or unsuccessful.

        """
        try:
            server = PlexServer(self._base_url, self._token.get_secret_value())
            lookup = _locate_album(server, artist_name=artist_name, album_title=album_title)
        except PlexProbeError:
            raise
        except Exception as exc:
            msg = str(exc) or "Unable to prepare Plex write verification."
            raise PlexProbeError(msg) from exc

        album = lookup.album
        methods = _album_edit_methods(album)
        current_summary = _optional_string(getattr(album, SUMMARY_FIELD, None))
        edit_summary_exists = "editSummary" in methods

        if not execute:
            return AlbumWriteVerificationReport(
                status="DRY_RUN",
                executed=False,
                library=lookup.library_title,
                rating_key=_optional_string(getattr(album, "ratingKey", None)),
                title=_optional_string(getattr(album, "title", None)),
                artist=artist_name,
                album=album_title,
                current_summary=current_summary,
                available_edit_methods=methods,
                edit_summary_exists=edit_summary_exists,
                original_summary_length=len(current_summary or ""),
                explanation="Dry run only. Plex was not modified.",
            )

        return _execute_album_summary_probe(
            server=server,
            album=album,
            library_title=lookup.library_title,
            artist_name=artist_name,
            album_title=album_title,
            current_summary=current_summary,
            available_edit_methods=methods,
            edit_summary_exists=edit_summary_exists,
        )


def _analyze_summary_capability(
    object_type: str,
    plex_object: Any,
) -> SummaryWriteCapability:
    """Analyze summary write capability for one Plex object."""
    available_fields = _available_fields(plex_object)
    supported_methods = _supported_edit_methods(plex_object)
    summary_supported = bool(supported_methods) and SUMMARY_FIELD in available_fields
    read_only_fields = [
        field for field in available_fields if not (field == SUMMARY_FIELD and summary_supported)
    ]

    return SummaryWriteCapability(
        object_type=object_type,
        rating_key=_optional_string(getattr(plex_object, "ratingKey", None)),
        title=_optional_string(getattr(plex_object, "title", None)),
        supported_edit_methods=supported_methods,
        writable_fields=[SUMMARY_FIELD] if summary_supported else [],
        read_only_fields=read_only_fields,
        lower_level_http_required=not summary_supported,
        explanation=(
            f"{object_type.title()}.summary appears writable through plexapi "
            f"method(s): {', '.join(supported_methods)}."
            if summary_supported
            else f"{object_type.title()}.summary does not appear writable through plexapi. "
            "A lower-level HTTP implementation would be required to test or perform this write."
        ),
    )


def _music_sections(sections: Iterable[Any]) -> list[Any]:
    """Return music library sections."""
    return [
        section
        for section in sections
        if (getattr(section, "type", None) or getattr(section, "TYPE", None)) == "artist"
    ]


def _first_from_sections(sections: list[Any], method_name: str) -> Any | None:
    """Return the first item from a Plex section method."""
    for section in sections:
        method = getattr(section, method_name, None)
        if not callable(method):
            continue

        items = _safe_call_iterable(method)
        if items:
            return items[0]

    return None


def _available_fields(plex_object: Any) -> list[str]:
    """Return readable public non-callable fields."""
    fields: list[str] = []
    for name in sorted(dir(plex_object)):
        if name.startswith("_"):
            continue

        value = _safe_getattr(plex_object, name)
        if value is _MISSING:
            continue

        if not callable(value):
            fields.append(name)

    return fields


def _supported_edit_methods(plex_object: Any) -> list[str]:
    """Return plexapi edit methods exposed by an object."""
    return [
        method_name
        for method_name in ("edit", "editField")
        if callable(getattr(plex_object, method_name, None))
    ]


def _locate_album(server: Any, *, artist_name: str, album_title: str) -> _AlbumLookup:
    """Locate exactly one album by artist and album title."""
    matches: list[_AlbumLookup] = []
    artist_query = _normalize_title(artist_name)
    album_query = _normalize_title(album_title)

    for section in _music_sections(server.library.sections()):
        library_title = _optional_string(getattr(section, "title", None))
        for artist in _safe_call_iterable(getattr(section, "all", None)):
            if _normalize_title(getattr(artist, "title", None)) != artist_query:
                continue

            albums_method = getattr(artist, "albums", None)
            for album in _safe_call_iterable(albums_method):
                if _normalize_title(getattr(album, "title", None)) == album_query:
                    matches.append(_AlbumLookup(album=album, library_title=library_title))

    if not matches:
        raise PlexProbeError(
            f'No album named "{album_title}" was found for artist "{artist_name}".'
        )

    if len(matches) > 1:
        raise PlexProbeError(
            f'Found {len(matches)} albums named "{album_title}" for artist '
            f'"{artist_name}". Refine the Plex metadata before running the write probe.'
        )

    return matches[0]


def _execute_album_summary_probe(
    *,
    server: Any,
    album: Any,
    library_title: str | None,
    artist_name: str,
    album_title: str,
    current_summary: str | None,
    available_edit_methods: list[str],
    edit_summary_exists: bool,
) -> AlbumWriteVerificationReport:
    """Run the reversible album summary write verification."""
    rating_key = _optional_string(getattr(album, "ratingKey", None))
    title = _optional_string(getattr(album, "title", None))
    edit_summary = getattr(album, "editSummary", None)
    batch_edits = getattr(album, "batchEdits", None)
    save_edits = getattr(album, "saveEdits", None)
    original_summary = current_summary or ""
    original_length = len(original_summary)

    if not callable(edit_summary):
        return AlbumWriteVerificationReport(
            status="READ_ONLY",
            executed=True,
            library=library_title,
            rating_key=rating_key,
            title=title,
            artist=artist_name,
            album=album_title,
            current_summary=current_summary,
            available_edit_methods=available_edit_methods,
            edit_summary_exists=edit_summary_exists,
            original_summary_length=original_length,
            temporary_summary_verified=False,
            original_summary_restored=None,
            explanation="album.editSummary() is not available on this Plex album object.",
        )

    if not callable(batch_edits):
        return AlbumWriteVerificationReport(
            status="READ_ONLY",
            executed=True,
            library=library_title,
            rating_key=rating_key,
            title=title,
            artist=artist_name,
            album=album_title,
            current_summary=current_summary,
            available_edit_methods=available_edit_methods,
            edit_summary_exists=edit_summary_exists,
            original_summary_length=original_length,
            temporary_summary_verified=False,
            original_summary_restored=None,
            explanation="album.batchEdits() is not available on this Plex album object.",
        )

    if not callable(save_edits):
        return AlbumWriteVerificationReport(
            status="READ_ONLY",
            executed=True,
            library=library_title,
            rating_key=rating_key,
            title=title,
            artist=artist_name,
            album=album_title,
            current_summary=current_summary,
            available_edit_methods=available_edit_methods,
            edit_summary_exists=edit_summary_exists,
            original_summary_length=original_length,
            temporary_summary_verified=False,
            original_summary_restored=None,
            explanation="album.saveEdits() is not available on this Plex album object.",
        )

    temporary_summary = _temporary_summary()
    summary_after_reload = None
    temp_verified = False
    restored = None
    restore_status = "NOT_ATTEMPTED"
    final_verification = None
    write_touched_album = False
    exception_text = None
    explanation = ""

    try:
        try:
            _apply_summary_edit(album, temporary_summary)
            write_touched_album = True
        except Exception as exc:
            return AlbumWriteVerificationReport(
                status="READ_ONLY",
                executed=True,
                library=library_title,
                rating_key=rating_key,
                title=title,
                artist=artist_name,
                album=album_title,
                current_summary=current_summary,
                available_edit_methods=available_edit_methods,
                edit_summary_exists=edit_summary_exists,
                original_summary_length=original_length,
                temporary_summary=temporary_summary,
                temporary_summary_verified=False,
                original_summary_restored=None,
                exception=_format_exception(exc),
                explanation=(
                    "album.editSummary() raised an exception. Plex may be read-only for this "
                    "field or the server rejected the edit."
                ),
            )

        reloaded_album = _reload_album(server, album)
        summary_after_reload = _optional_string(getattr(reloaded_album, SUMMARY_FIELD, None))
        temp_verified = summary_after_reload == temporary_summary
        explanation = (
            "Temporary summary matched after reload."
            if temp_verified
            else "The temporary summary did not match after reloading the album."
        )
    except Exception as exc:
        exception_text = _format_exception(exc)
        explanation = "The write verification failed while saving or reloading the test summary."
    finally:
        if write_touched_album:
            restore_status, restored, final_verification = _restore_and_verify_album_summary(
                server,
                album,
                original_summary,
            )

    status = "SUCCESS" if temp_verified else "FAILED"
    if restored is not True:
        status = "FAILED"

    return AlbumWriteVerificationReport(
        status=status,
        executed=True,
        library=library_title,
        rating_key=rating_key,
        title=title,
        artist=artist_name,
        album=album_title,
        current_summary=current_summary,
        available_edit_methods=available_edit_methods,
        edit_summary_exists=edit_summary_exists,
        original_summary_length=original_length,
        temporary_summary=temporary_summary,
        summary_after_reload=summary_after_reload,
        restore_status=restore_status,
        final_verification=final_verification,
        temporary_summary_verified=temp_verified,
        original_summary_restored=restored,
        exception=exception_text,
        explanation=explanation,
    )


def _restore_and_verify_album_summary(
    server: Any,
    album: Any,
    original_summary: str,
) -> tuple[str, bool, bool]:
    """Restore the original album summary and verify it after reload."""
    try:
        reloaded_album = _reload_album(server, album)
        _apply_summary_edit(reloaded_album, original_summary)
        final_album = _reload_album(server, reloaded_album)
        final_summary = getattr(final_album, SUMMARY_FIELD, None) or ""
        verified = final_summary == original_summary
        return ("RESTORED" if verified else "FAILED", verified, verified)
    except Exception:
        return ("FAILED", False, False)


def _apply_summary_edit(album: Any, summary: str) -> None:
    """Apply a summary edit using plexapi batch editing."""
    batch_edits = getattr(album, "batchEdits", None)
    edit_summary = getattr(album, "editSummary", None)
    save_edits = getattr(album, "saveEdits", None)

    if not callable(batch_edits):
        raise PlexProbeError("album.batchEdits() is not available on this Plex album object.")
    if not callable(edit_summary):
        raise PlexProbeError("album.editSummary() is not available on this Plex album object.")
    if not callable(save_edits):
        raise PlexProbeError("album.saveEdits() is not available on this Plex album object.")

    batch_edits()
    edit_summary(summary)
    save_edits()


def _reload_album(server: Any, album: Any) -> Any:
    """Reload an album object from Plex."""
    rating_key = getattr(album, "ratingKey", None)
    fetch_item = getattr(server, "fetchItem", None)
    if callable(fetch_item) and rating_key is not None:
        return fetch_item(rating_key)

    reload_album = getattr(album, "reload", None)
    if callable(reload_album):
        result = reload_album()
        return album if result is None else result

    raise PlexProbeError("Album could not be reloaded from Plex after writing.")


def _album_edit_methods(album: Any) -> list[str]:
    """Return write-related plexapi methods exposed by an album."""
    return [
        method_name
        for method_name in (
            "batchEdits",
            "editSummary",
            "saveEdits",
            "reload",
            "edit",
            "editField",
        )
        if callable(getattr(album, method_name, None))
    ]


def _temporary_summary() -> str:
    """Return a unique temporary summary value for write verification."""
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{TEST_SUMMARY_PREFIX}_{timestamp}"


def _normalize_title(value: object) -> str:
    """Normalize a Plex title for exact case-insensitive matching."""
    return str(value or "").strip().casefold()


def _format_exception(exc: Exception) -> str:
    """Return a complete exception traceback for reporting."""
    return "".join(format_exception(type(exc), exc, exc.__traceback__)).strip()


def _safe_getattr(plex_object: Any, name: str) -> object:
    """Return an attribute or a sentinel when it cannot be read."""
    try:
        return getattr(plex_object, name)
    except Exception:
        return _MISSING


def _safe_call_iterable(method: Any) -> list[Any]:
    """Call a Plex method expected to return an iterable."""
    try:
        result = method()
    except Exception:
        return []

    if result is None:
        return []

    return list(cast(Iterable[Any], result))


def _plexapi_version() -> str | None:
    """Return the installed plexapi package version."""
    try:
        return version("plexapi")
    except PackageNotFoundError:
        return None


def _optional_string(value: object) -> str | None:
    """Return a populated string value."""
    if value is None:
        return None

    text = str(value)
    return text or None
