"""Read-only Plex metadata inspector."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol, cast

from plexapi.server import PlexServer
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

_MISSING = object()


class InspectTarget(StrEnum):
    """Supported metadata inspection targets."""

    LIBRARY = "library"
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"


class InspectImage(BaseModel):
    """Image reference discovered on a Plex object."""

    model_config = ConfigDict(frozen=True)

    kind: str
    value: str


class InspectChild(BaseModel):
    """Child object reference discovered on a Plex object."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    kind: str
    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    title: str | None = None
    guid: str | None = None


class InspectedPlexObject(BaseModel):
    """Complete read-only inspection snapshot for a Plex object."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    object_type: str = Field(serialization_alias="objectType")
    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    guid: str | None = None
    title: str | None = None
    attributes: dict[str, Any]
    media: list[dict[str, Any]]
    images: list[InspectImage]
    children: list[InspectChild]


class PlexInspectError(Exception):
    """Raised when Plex metadata inspection cannot complete."""


class _PlexLibrary(Protocol):
    """Minimal Plex library API used by the inspector."""

    def sections(self) -> list[Any]:
        """Return Plex library sections."""


class _PlexServer(Protocol):
    """Minimal Plex server API used by the inspector."""

    @property
    def library(self) -> _PlexLibrary:
        """Return the Plex library accessor."""

    def fetchItem(self, key: str) -> Any:  # noqa: N802
        """Return a Plex item by rating key."""


class PlexMetadataInspector:
    """Read-only Plex metadata inspector."""

    def __init__(self, base_url: AnyHttpUrl, token: SecretStr) -> None:
        """Create a Plex metadata inspector.

        Args:
            base_url: Base URL of the Plex server.
            token: Plex authentication token.

        """
        self._base_url = str(base_url).rstrip("/")
        self._token = token

    def inspect(
        self,
        target: InspectTarget,
        *,
        rating_key: str | None,
        name: str | None,
    ) -> InspectedPlexObject:
        """Inspect a Plex object by rating key or title."""
        try:
            server = cast(_PlexServer, PlexServer(self._base_url, self._token.get_secret_value()))
            plex_object = self._find_object(server, target, rating_key=rating_key, name=name)
            return _inspect_object(target.value, plex_object)
        except PlexInspectError:
            raise
        except Exception as exc:
            msg = str(exc) or f"Unable to inspect Plex {target.value}."
            raise PlexInspectError(msg) from exc

    def _find_object(
        self,
        server: _PlexServer,
        target: InspectTarget,
        *,
        rating_key: str | None,
        name: str | None,
    ) -> Any:
        """Find a Plex object by rating key or title."""
        if target is InspectTarget.LIBRARY:
            return _find_library(server.library.sections(), rating_key=rating_key, name=name)

        if rating_key is not None:
            return server.fetchItem(rating_key)

        if name is None:
            msg = "Provide either --id or --name."
            raise PlexInspectError(msg)

        return _find_named_metadata(_music_sections(server), target, name)


def _find_library(
    sections: Iterable[Any],
    *,
    rating_key: str | None,
    name: str | None,
) -> Any:
    """Find a library section by key or title."""
    for section in sections:
        if rating_key is not None and str(getattr(section, "key", "")) == rating_key:
            return section
        if name is not None and str(getattr(section, "title", "")).casefold() == name.casefold():
            return section

    msg = "Plex library was not found."
    raise PlexInspectError(msg)


def _find_named_metadata(sections: Iterable[Any], target: InspectTarget, name: str) -> Any:
    """Find a named artist, album, or track in music libraries."""
    for section in sections:
        candidates = _metadata_candidates(section, target)
        for candidate in candidates:
            if str(getattr(candidate, "title", "")).casefold() == name.casefold():
                return candidate

    msg = f"Plex {target.value} was not found."
    raise PlexInspectError(msg)


def _metadata_candidates(section: Any, target: InspectTarget) -> Iterable[Any]:
    """Return candidate Plex objects for the requested target."""
    if target is InspectTarget.ARTIST:
        return cast(Iterable[Any], section.all())
    if target is InspectTarget.ALBUM:
        return cast(Iterable[Any], section.albums())
    if target is InspectTarget.TRACK:
        return cast(Iterable[Any], section.searchTracks())

    return []


def _music_sections(server: _PlexServer) -> list[Any]:
    """Return all Plex music library sections."""
    return [
        section
        for section in server.library.sections()
        if (getattr(section, "type", None) or getattr(section, "TYPE", None)) == "artist"
    ]


def _inspect_object(object_type: str, plex_object: Any) -> InspectedPlexObject:
    """Create a complete inspection snapshot for a Plex object."""
    return InspectedPlexObject(
        object_type=object_type,
        rating_key=_object_rating_key(plex_object),
        guid=_optional_string(getattr(plex_object, "guid", None)),
        title=_optional_string(getattr(plex_object, "title", None)),
        attributes=_attributes(plex_object),
        media=_media_objects(plex_object),
        images=_images(plex_object),
        children=_children(plex_object),
    )


def _attributes(plex_object: Any) -> dict[str, Any]:
    """Return public serializable attributes from a Plex object."""
    attributes: dict[str, Any] = {}
    for name in sorted(dir(plex_object)):
        if name.startswith("_") or name in {"media"}:
            continue

        value = _safe_getattr(plex_object, name)
        if value is _MISSING:
            continue

        if callable(value):
            continue

        serialized = _to_jsonable(value)
        if serialized is not None:
            attributes[name] = serialized

    return attributes


def _media_objects(plex_object: Any) -> list[dict[str, Any]]:
    """Return every available Plex media object."""
    media_items = getattr(plex_object, "media", []) or []
    return [
        media_attributes
        for media in cast(Iterable[Any], media_items)
        if (media_attributes := _attributes(media))
    ]


def _images(plex_object: Any) -> list[InspectImage]:
    """Return image references from common Plex image attributes."""
    images: list[InspectImage] = []
    for name in ("art", "banner", "composite", "coverPoster", "parentThumb", "thumb"):
        value = _optional_string(getattr(plex_object, name, None))
        if value is not None:
            images.append(InspectImage(kind=name, value=value))

    images_method = getattr(plex_object, "images", None)
    if callable(images_method):
        for image in _safe_call_iterable(images_method):
            image_value = _optional_string(getattr(image, "url", image))
            image_kind = _optional_string(getattr(image, "type", None)) or "image"
            if image_value is not None:
                images.append(InspectImage(kind=image_kind, value=image_value))

    return images


def _children(plex_object: Any) -> list[InspectChild]:
    """Return available child object references."""
    children: list[InspectChild] = []
    for method_name, kind in (
        ("all", "item"),
        ("albums", "album"),
        ("tracks", "track"),
        ("searchTracks", "track"),
    ):
        method = getattr(plex_object, method_name, None)
        if not callable(method):
            continue

        children.extend(_child_reference(kind, item) for item in _safe_call_iterable(method))

    return _deduplicate_children(children)


def _child_reference(kind: str, plex_object: Any) -> InspectChild:
    """Return a compact child object reference."""
    return InspectChild(
        kind=kind,
        rating_key=_object_rating_key(plex_object),
        title=_optional_string(getattr(plex_object, "title", None)),
        guid=_optional_string(getattr(plex_object, "guid", None)),
    )


def _deduplicate_children(children: list[InspectChild]) -> list[InspectChild]:
    """Deduplicate child references while preserving order."""
    seen: set[tuple[str, str | None, str | None]] = set()
    deduplicated: list[InspectChild] = []
    for child in children:
        key = (child.kind, child.rating_key, child.title)
        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(child)

    return deduplicated


def _object_rating_key(plex_object: Any) -> str | None:
    """Return a Plex rating key or library section key."""
    return _optional_string(
        getattr(plex_object, "ratingKey", None) or getattr(plex_object, "key", None)
    )


def _optional_string(value: object) -> str | None:
    """Return a string value when Plex exposes a populated attribute."""
    if value is None:
        return None

    text = str(value)
    return text or None


def _safe_getattr(plex_object: Any, name: str) -> object:
    """Return a Plex attribute or a sentinel when it cannot be read."""
    try:
        return getattr(plex_object, name)
    except Exception:
        return _MISSING


def _safe_call_iterable(method: Any) -> list[Any]:
    """Call a Plex method that should return an iterable."""
    try:
        result = method()
    except Exception:
        return []

    if result is None:
        return []

    return list(cast(Iterable[Any], result))


def _to_jsonable(value: object) -> Any:
    """Convert common Plex values to JSON-compatible data."""
    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, datetime | date):
        return value.isoformat()

    if isinstance(value, list | tuple | set):
        return [_to_jsonable(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}

    tag = getattr(value, "tag", None)
    if tag is not None:
        return _optional_string(tag)

    if hasattr(value, "__dict__"):
        public_values = {
            key: _to_jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
        return public_values or _optional_string(value)

    return _optional_string(value)
