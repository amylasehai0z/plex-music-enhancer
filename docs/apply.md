# Apply Workflow

The apply workflow writes a generated album summary back to Plex only after the
same preview and review pipeline has produced a quality-checked summary.

## Command

```bash
plex-enhancer apply --artist "Artist Name" --album "Album Title"
```

Optional overrides:

```bash
plex-enhancer apply --artist "Artist Name" --album "Album Title" --provider openai --model gpt-5.5
plex-enhancer apply --artist "Artist Name" --album "Album Title" --json
```

## Safety Model

For one selected album, the command:

1. Builds an `AlbumContext` through the enrichment pipeline.
2. Generates a summary through the configured AI provider.
3. Runs the review quality checks.
4. Stores the current Plex summary under the persistent export path
   (`/config/exports/backups/` in Docker).
5. Writes the generated summary with PlexAPI batch edits.
6. Reloads the album from Plex and verifies the stored summary.
7. Stores an audit record under the persistent export path
   (`/config/exports/audit/` in Docker).

If quality validation fails, Plex is not modified and no backup is created. If
the write or verification fails after the backup has been created, the backup is
kept and the audit record is marked as failed.

The export root defaults to `/config/exports` in containers and can be
overridden with `PLEX_ENHANCER_EXPORTS`. It should always point to a writable,
persistent volume.

## Plex Write Workflow

Album summaries are written through the documented PlexAPI editing flow:

```python
album.batchEdits()
album.editSummary(summary)
album.saveEdits()
album.reload()
```

The command reports success only when the reloaded album summary exactly matches
the generated summary.

## Audit Records

Each completed write attempt records:

- album identity and rating key
- provider and model
- prompt name and version
- backup path
- write status
- verification status
- expected and verified summary values

No batch mode or rollback command is implemented yet.
