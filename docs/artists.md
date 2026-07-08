# Artist Enrichment

Artist enrichment follows the same preview, review, and apply lifecycle as album
summaries.

## Commands

Preview a generated biography without modifying Plex:

```bash
plex-enhancer preview artist --artist "Nina Simone"
```

Review the generated biography interactively:

```bash
plex-enhancer review artist --artist "Nina Simone"
```

Apply the generated biography after quality validation:

```bash
plex-enhancer apply artist --artist "Nina Simone"
```

Each command supports the same provider overrides as albums:

```bash
plex-enhancer preview artist --artist "Nina Simone" --provider openai --model gpt-5.5
```

## Workflow

The artist workflow:

1. Loads the artist from Plex.
2. Resolves MusicBrainz artist metadata.
3. Resolves the Wikipedia biography, preferring German and falling back to English.
4. Builds an `ArtistContext`.
5. Renders the artist summary prompt.
6. Generates a German biography through `AIManager`.
7. Runs the same quality validation used for album summaries.
8. Writes through the apply workflow only when `apply artist` is used.

## Safety

Artist apply uses the same safety controls as album apply:

- current Plex summary backup under `exports/backups/`
- PlexAPI batch edit workflow
- reload verification
- audit record under `exports/audit/`

No batch artist mode or rollback command is implemented yet.
