"""Artist REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from plex_music_enhancer.album_reviews import AlbumReviewService
from plex_music_enhancer.api.models import LibraryAlbum, LibraryArtist, LibraryArtistDetail
from plex_music_enhancer.plex.sync import PlexLibrarySyncService, PlexSyncSnapshot, SyncedArtist
from plex_music_enhancer.web.dependencies import get_album_review_service, get_plex_sync_service

router = APIRouter()


@router.get("", response_model=list[LibraryArtist])
async def list_artists(
    sync_service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
) -> list[LibraryArtist]:
    """Return synchronized Plex artist entries for library views."""
    snapshot = sync_service.snapshot()
    if snapshot is None:
        return []
    return [_artist_entry(snapshot, artist) for artist in snapshot.artists]


@router.get("/{artist_id}", response_model=LibraryArtistDetail)
async def get_artist(
    artist_id: str,
    sync_service: Annotated[PlexLibrarySyncService, Depends(get_plex_sync_service)],
    review_service: Annotated[AlbumReviewService, Depends(get_album_review_service)],
) -> LibraryArtistDetail:
    """Return one synchronized Plex artist with albums, tracks and stored reviews."""
    snapshot = sync_service.snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No Plex sync snapshot available.")
    artist = next((item for item in snapshot.artists if item.rating_key == artist_id), None)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found in synchronized library.")

    albums = [
        LibraryAlbum(
            rating_key=album.rating_key,
            title=album.title,
            artist=album.parent_artist or artist.title,
            library=album.library_title,
            year=album.year,
            summary_present=False,
        )
        for album in snapshot.albums
        if _same_artist(album.parent_artist, artist.title) and album.library_id == artist.library_id
    ]
    tracks = [
        track.title
        for track in snapshot.tracks
        if _same_artist(track.parent_artist, artist.title) and track.library_id == artist.library_id
    ]
    album_ids = {
        album.rating_key
        for album in snapshot.albums
        if _same_artist(album.parent_artist, artist.title)
    }
    reviews = [
        review
        for review in review_service.reviews().values()
        if review.album_id in album_ids or _same_artist(review.artist, artist.title)
    ]

    return LibraryArtistDetail(
        rating_key=artist.rating_key,
        title=artist.title,
        library=artist.library_title,
        album_count=len(albums),
        track_count=len(tracks),
        albums=albums,
        tracks=tracks,
        reviews=reviews,
    )


def _artist_entry(snapshot: PlexSyncSnapshot, artist: SyncedArtist) -> LibraryArtist:
    """Return a public artist row with aggregate counts."""
    albums = [
        album
        for album in snapshot.albums
        if _same_artist(album.parent_artist, artist.title) and album.library_id == artist.library_id
    ]
    tracks = [
        track
        for track in snapshot.tracks
        if _same_artist(track.parent_artist, artist.title) and track.library_id == artist.library_id
    ]
    return LibraryArtist(
        rating_key=artist.rating_key,
        title=artist.title,
        library=artist.library_title,
        album_count=len(albums),
        track_count=len(tracks),
        summary_present=False,
    )


def _same_artist(left: str | None, right: str) -> bool:
    """Return whether two artist names describe the same synced Plex artist."""
    return (left or "").strip().casefold() == right.strip().casefold()
