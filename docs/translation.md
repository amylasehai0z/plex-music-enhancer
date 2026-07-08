# Translation Engine

The translation engine translates existing English Plex album summaries into natural German.

## Command

```bash
plex-enhancer preview --artist "Artist" --album "Album" --translate
plex-enhancer review --artist "Artist" --album "Album" --translate
plex-enhancer apply --artist "Artist" --album "Album" --translate
```

Preview and review are read-only. Apply uses the existing backup, verification, and audit workflow
and stores the approved translated summary exactly as reviewed.

## Workflow

1. Load the album from Plex through the enrichment pipeline.
2. Validate that a current Plex summary exists.
3. Detect whether the source summary is English, mixed, German, or unknown.
4. Render `prompts/album_translate.md`.
5. Generate the German translation through `AIManager`.
6. Show the current summary, translated summary, and diff in review.

## Translation Rules

The translation prompt requires the model to:

- translate only
- avoid summarizing or condensing
- preserve all factual information
- avoid invented facts
- keep names, song titles, album titles, labels, and proper names in the original language
- preserve release dates and track titles exactly
- translate prose into natural German

## Planner Integration

When the planner recommends `TRANSLATE`, batch review uses the translation engine automatically by
selecting the `album_translate` prompt.

German summaries are not translated. Use improvement mode for existing German text.
