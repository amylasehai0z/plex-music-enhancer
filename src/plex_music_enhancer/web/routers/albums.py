"""Album REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from plex_music_enhancer.album_reviews import AlbumReviewService
from plex_music_enhancer.api.models import LibraryAlbum, LibraryAlbumDetail, StoredAlbumReview
from plex_music_enhancer.plex.sync import (
    PlexLibrarySyncService,
    PlexSyncSnapshot,
    SyncedAlbum,
    SyncedArtist,
    SyncedTrack,
)
from plex_music_enhancer.web.dependencies import get_album_review_service, get_plex_sync_service

router = APIRouter()


@router.get("", response_model=list[LibraryAlbum])
async def list_albums(
    sync_service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
    review_service: Annotated[AlbumReviewService, Depends(get_album_review_service)],
) -> list[LibraryAlbum]:
    """Return synchronized Plex album entries for library views."""
    snapshot = sync_service.snapshot()
    if snapshot is None:
        return []
    reviews = review_service.reviews()
    return [
        _album_entry(snapshot, album, reviews.get(album.rating_key)) for album in snapshot.albums
    ]


@router.get("/{album_id}", response_model=LibraryAlbumDetail)
async def get_album(
    album_id: str,
    sync_service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
    review_service: Annotated[AlbumReviewService, Depends(get_album_review_service)],
) -> LibraryAlbumDetail:
    """Return one synchronized Plex album with tracks and stored review."""
    snapshot = sync_service.snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No Plex sync snapshot available.")
    album = next((item for item in snapshot.albums if item.rating_key == album_id), None)
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found in synchronized library.")

    review = review_service.reviews().get(album.rating_key)
    entry = _album_entry(snapshot, album, review)
    return LibraryAlbumDetail(
        **entry.model_dump(),
        tracks=[_track_label(track) for track in _tracks_for_album(snapshot, album)],
        review=review,
    )


def _album_entry(
    snapshot: PlexSyncSnapshot,
    album: SyncedAlbum,
    review: StoredAlbumReview | None,
) -> LibraryAlbum:
    """Return a public album row with aggregate counts and review status."""
    tracks = _tracks_for_album(snapshot, album)
    artist = _artist_for_album(snapshot, album)
    return LibraryAlbum(
        rating_key=album.rating_key,
        title=album.title,
        artist=album.parent_artist or "Unbekannter Interpret",
        artist_id=artist.rating_key if artist is not None else None,
        library=album.library_title,
        year=album.year,
        track_count=len(tracks),
        genres=review.content.genres if review is not None else [],
        review_status="present" if review is not None else "missing",
        summary_present=review is not None,
    )


def _tracks_for_album(snapshot: PlexSyncSnapshot, album: SyncedAlbum) -> list[SyncedTrack]:
    """Return tracks belonging to an album from the sync snapshot."""
    return sorted(
        [
            track
            for track in snapshot.tracks
            if _same(track.parent_album, album.title)
            and _same(track.parent_artist, album.parent_artist)
            and track.library_id == album.library_id
        ],
        key=lambda track: (track.index is None, track.index or 0, track.title.casefold()),
    )


def _artist_for_album(snapshot: PlexSyncSnapshot, album: SyncedAlbum) -> SyncedArtist | None:
    """Return the synchronized artist for an album when present."""
    return next(
        (
            artist
            for artist in snapshot.artists
            if _same(artist.title, album.parent_artist) and artist.library_id == album.library_id
        ),
        None,
    )


def _track_label(track: SyncedTrack) -> str:
    """Return a stable track label for UI display."""
    return f"{track.index}. {track.title}" if track.index is not None else track.title


def _same(left: str | None, right: str | None) -> bool:
    """Return whether two optional Plex strings describe the same value."""
    return (left or "").strip().casefold() == (right or "").strip().casefold()
