# Metadata Enrichment

The first metadata enrichment pipeline is implemented in
`src/plex_music_enhancer/services/enrichment.py`.

## Scope

The pipeline is read-only. It does not modify Plex, does not use AI, and does
not call Wikipedia.

## Workflow

Given a Plex album identity:

- artist
- album
- optional year

the pipeline:

1. Runs MusicBrainz release-group matching.
2. Fetches MusicBrainz release-group metadata when a confident match exists.
3. Produces one normalized album metadata document.

## Output Model

The output document has three sections:

- `plex`
  The input album metadata supplied by Plex or the caller.
- `musicbrainz`
  Match status, confidence, MBIDs, release date, release type, genres, tags, and
  warnings.
- `metadata`
  Normalized album metadata containing artist, album, year, genres, summary,
  sources, and confidence.

The normalized summary is currently `None`; summary generation is reserved for a
future non-AI or AI enrichment step.

## CLI

Render a Rich report:

```bash
plex-enhancer metadata album --artist "Nina Simone" --album "Pastel Blues"
```

Print JSON:

```bash
plex-enhancer metadata album --artist "Nina Simone" --album "Pastel Blues" --json
```

Save JSON:

```bash
plex-enhancer metadata album --artist "Nina Simone" --album "Pastel Blues" --save
```

Saved files are written under:

`exports/metadata/<artist>-<album>.json`
