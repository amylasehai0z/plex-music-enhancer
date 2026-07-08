# Enrichment Preview

The preview command performs a read-only readiness check for album enrichment.

```bash
plex-enhancer preview --artist "Nina Simone" --album "Pastel Blues"
```

## Workflow

1. Reads the selected album from Plex.
2. Displays the current Plex metadata:
   - title
   - artist
   - current summary
   - year
   - genres
3. Queries configured metadata providers.
4. Displays provider readiness checks:
   - provider reachable
   - match found
   - metadata available
5. Shows MusicBrainz identifiers and metadata fields.

The first configured provider is MusicBrainz. The command reuses the existing
MusicBrainz matching and enrichment pipeline.

## Boundaries

The preview command does not generate text, does not call AI, and does not
modify Plex. It is intended to show whether an album has enough provider
metadata for a later enrichment workflow.
