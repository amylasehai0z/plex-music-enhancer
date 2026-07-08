# MusicBrainz Provider

The MusicBrainz provider is a read-only metadata source implemented under
`src/plex_music_enhancer/providers/musicbrainz/`.

## API Endpoints

The provider uses the official MusicBrainz Web Service API at:

`https://musicbrainz.org/ws/2`

Implemented endpoints:

- `GET /artist`
  Searches artists by name and returns MBID, name, sort name, country,
  disambiguation, tags, aliases, and life-span.
- `GET /release-group`
  Searches albums by artist and album title and returns release-group MBID,
  title, first release date, primary type, and secondary types.
- `GET /release`
  Resolves the first release MBID for a release-group search result.
- `GET /artist/{mbid}`
  Fetches detailed artist metadata by MBID.
- `GET /release-group/{mbid}`
  Fetches detailed album metadata by release-group MBID.

All requests use `fmt=json`.

## Rate Limiting

MusicBrainz asks API clients to make no more than one request per second.
`MusicBrainzClient` enforces this with a process-local lock and a minimum
interval between requests. The client is synchronous and does not issue parallel
requests to MusicBrainz.

Transient failures are retried for:

- `429`
- `500`
- `502`
- `503`
- `504`
- temporary `httpx.RequestError` failures

The client sets a project User-Agent on all requests:

`plex-music-enhancer/<version> ( https://github.com/plex-music-enhancer )`

## Caching Strategy

Detailed metadata lookups are cached transparently by MBID.

- Cache directory: `cache/musicbrainz/`
- Cache key: `<MBID>.json`
- Cache lifetime: 30 days

Search results are not cached yet. The cache is currently used for:

- `get_artist_metadata(mbid)`
- `get_album_metadata(mbid)`

Expired or unreadable cache entries are ignored and refreshed from MusicBrainz.

## Boundaries

This provider does not use AI, does not call Wikipedia, and does not write to
Plex. It only gathers MusicBrainz metadata for later enrichment workflows.
