# Enrichment Pipeline

The enrichment pipeline builds one normalized `AlbumContext` for a Plex album. This context is
the central read-only document intended for Preview, AI generation, Apply, and Rollback workflows.

## Command

```text
plex-enhancer context album --artist "Artist" --album "Album"
```

Options:

- `--json` prints the complete `AlbumContext`.
- `--save` writes `exports/context/<artist>-<album>.json`.

## Workflow

1. Read exactly one matching album from Plex.
2. Resolve the album against MusicBrainz using the existing matcher.
3. Retrieve MusicBrainz release-group metadata.
4. Resolve Wikipedia metadata through the configured provider manager.
5. Merge all metadata into one typed context document.
6. Validate completeness and set `ready_for_generation`.

## Context Sections

`plex` contains album identity and local Plex metadata:

- `rating_key`
- `artist`
- `album`
- `year`
- `summary`
- `genres`
- `styles`
- `moods`

`musicbrainz` contains external identity and classification metadata:

- `artist_mbid`
- `release_group_mbid`
- `release_mbid`
- `release_date`
- `genres`
- `tags`
- `confidence`

`wikipedia` contains encyclopedic summary metadata:

- `language`
- `title`
- `extract`
- `page_url`
- `thumbnail_url`

`pipeline` contains operational status:

- `collected_sources`
- `missing_fields`
- `warnings`
- `ready_for_generation`

## Read-Only Guarantee

The pipeline only reads from Plex and external providers. It does not write to Plex, does not call
AI services, and does not generate replacement metadata.
