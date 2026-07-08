# Batch Review

Batch review processes multiple albums in one guided terminal session. It is
sequential by design: one album is scanned, reviewed, optionally edited, and
then applied or skipped before the next album is shown.

## Command

```bash
plex-enhancer batch review
```

Common options:

```bash
plex-enhancer batch review --library "Music" --missing-only --limit 25
plex-enhancer batch review --library "Music" --resume
plex-enhancer batch review --provider openai --model gpt-5.5
plex-enhancer batch review --json
```

`--missing-only` is enabled by default. Use `--all` to include albums that
already have summaries.

## Workflow

For each selected album, the command:

1. Scans the selected Plex music library.
2. Filters albums according to the requested options.
3. Builds the same `AlbumContext` used by preview and review.
4. Generates a summary through the configured AI provider.
5. Runs quality validation.
6. Displays the album, current summary, and generated summary.
7. Prompts for a decision:

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

Choosing Apply reuses the existing apply workflow, including backup creation,
Plex write, reload verification, and audit storage. Choosing Edit opens the
configured terminal editor and validates the edited text before asking again.

## Progress And Resume

Progress is stored under:

```text
exports/jobs/
```

The progress file records completed Plex rating keys for the selected library
and filter. When `--resume` is supplied, completed albums are skipped.

## Summary Report

At the end of a session the command reports:

- Processed
- Applied
- Skipped
- Failed
- Progress file

If any album fails, the command exits with a non-zero status. No parallel
execution or web interface is implemented.
