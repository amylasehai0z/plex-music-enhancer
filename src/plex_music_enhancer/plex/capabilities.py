"""Read-only Plex metadata capability analyzer."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

_MISSING = object()
_MUTATING_METHOD_PREFIXES = ("add", "edit", "remove", "save", "update", "upload")
_KNOWN_EDITABLE_ATTRIBUTES = {
    "contentRating",
    "originallyAvailableAt",
    "rating",
    "sortTitle",
    "summary",
    "title",
    "titleSort",
    "userRating",
}


class LibraryCapability(BaseModel):
    """Plex music library capability context."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    library_id: str = Field(serialization_alias="libraryId")
    library_title: str = Field(serialization_alias="libraryTitle")
    agent: str | None = None
    scanner: str | None = None


class ObjectCapabilityAnalysis(BaseModel):
    """Metadata capability analysis for one sampled Plex object type."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    object_type: str = Field(serialization_alias="objectType")
    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    title: str | None = None
    available_attributes: list[str] = Field(serialization_alias="availableAttributes")
    writable_attributes: list[str] = Field(serialization_alias="writableAttributes")
    read_only_attributes: list[str] = Field(serialization_alias="readOnlyAttributes")
    api_capabilities: list[str] = Field(serialization_alias="apiCapabilities")


class PlexCapabilityAnalysis(BaseModel):
    """Complete Plex metadata capability analysis export."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    plex_server_version: str | None = Field(
        default=None,
        serialization_alias="plexServerVersion",
    )
    platform: str | None = None
    libraries: list[LibraryCapability]
    api_capabilities: list[str] = Field(serialization_alias="apiCapabilities")
    samples: list[ObjectCapabilityAnalysis]


class PlexCapabilityError(Exception):
    """Raised when Plex capability analysis cannot complete."""


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the analyzer."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the analyzer."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""


class PlexCapabilityAnalyzer:
    """Read-only analyzer for Plex metadata capabilities."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex capability analyzer.

        Args:
            base_url: Base URL of the Plex server.
            token: Plex authentication token.

        """
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def analyze(self) -> PlexCapabilityAnalysis:
        """Analyze Plex metadata capabilities without modifying Plex."""
        try:
            server = cast(_PlexServer, PlexServer(self._base_url, self._token.get_secret_value()))
            music_sections = _music_sections(server.library.sections())
            samples = _sample_objects(music_sections)
            return PlexCapabilityAnalysis(
                plex_server_version=_optional_string(getattr(server, "version", None)),
                platform=_optional_string(getattr(server, "platform", None)),
                libraries=[_library_capability(section) for section in music_sections],
                api_capabilities=_api_capabilities(server),
                samples=[
                    _analyze_object(object_type, plex_object)
                    for object_type, plex_object in samples
                    if plex_object is not None
                ],
            )
        except Exception as exc:
            msg = str(exc) or "Unable to analyze Plex metadata capabilities."
            raise PlexCapabilityError(msg) from exc


def _music_sections(sections: Iterable[Any]) -> list[Any]:
    """Return music library sections."""
    return [
        section
        for section in sections
        if (getattr(section, "type", None) or getattr(section, "TYPE", None)) == "artist"
    ]


def _sample_objects(sections: list[Any]) -> list[tuple[str, Any | None]]:
    """Return one artist, album, and track sample from music libraries."""
    return [
        ("artist", _first_from_sections(sections, "all")),
        ("album", _first_from_sections(sections, "albums")),
        ("track", _first_from_sections(sections, "searchTracks")),
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


def _library_capability(section: Any) -> LibraryCapability:
    """Return library capability context."""
    return LibraryCapability(
        library_id=str(getattr(section, "key", "")),
        library_title=str(getattr(section, "title", "Untitled")),
        agent=_optional_string(getattr(section, "agent", None)),
        scanner=_optional_string(getattr(section, "scanner", None)),
    )


def _analyze_object(object_type: str, plex_object: Any) -> ObjectCapabilityAnalysis:
    """Analyze available and writable metadata attributes for one Plex object."""
    available_attributes = _available_attributes(plex_object)
    writable_attributes = [
        attribute
        for attribute in available_attributes
        if _is_writable_attribute(plex_object, attribute)
    ]
    writable_set = set(writable_attributes)

    return ObjectCapabilityAnalysis(
        object_type=object_type,
        rating_key=_optional_string(getattr(plex_object, "ratingKey", None)),
        title=_optional_string(getattr(plex_object, "title", None)),
        available_attributes=available_attributes,
        writable_attributes=writable_attributes,
        read_only_attributes=[
            attribute for attribute in available_attributes if attribute not in writable_set
        ],
        api_capabilities=_api_capabilities(plex_object),
    )


def _available_attributes(plex_object: Any) -> list[str]:
    """Return readable public attributes for a Plex object."""
    attributes: list[str] = []
    for name in sorted(dir(plex_object)):
        if name.startswith("_"):
            continue

        value = _safe_getattr(plex_object, name)
        if value is _MISSING or callable(value):
            continue

        attributes.append(name)

    return attributes


def _is_writable_attribute(plex_object: Any, attribute: str) -> bool:
    """Return whether an attribute appears writable through plexapi."""
    descriptor = inspect_descriptor(type(plex_object), attribute)
    if isinstance(descriptor, property) and descriptor.fset is not None:
        return True

    return attribute in _KNOWN_EDITABLE_ATTRIBUTES and callable(getattr(plex_object, "edit", None))


def inspect_descriptor(object_type: type[object], attribute: str) -> object | None:
    """Return a class descriptor without invoking instance attribute access."""
    for class_item in object_type.__mro__:
        if attribute in class_item.__dict__:
            return class_item.__dict__[attribute]

    return None


def _api_capabilities(plex_object: Any) -> list[str]:
    """Return available plexapi methods that indicate API capabilities."""
    capabilities: list[str] = []
    for name in sorted(dir(plex_object)):
        if name.startswith("_") or not name.startswith(_MUTATING_METHOD_PREFIXES):
            continue

        value = _safe_getattr(plex_object, name)
        if callable(value):
            capabilities.append(name)

    return capabilities


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


def _optional_string(value: object) -> str | None:
    """Return a populated string value."""
    if value is None:
        return None

    text = str(value)
    return text or None
