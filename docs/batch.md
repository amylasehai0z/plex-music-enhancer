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
3. Runs the planner against the current Plex summary.
4. Invokes AI only for `CREATE`, `TRANSLATE`, and `IMPROVE`.
5. Skips `SKIP` items automatically.
6. Asks the user for `REVIEW` items without generating text automatically.
7. Builds the same `AlbumContext` used by preview and review when generation is required.
8. Runs quality validation.
9. Displays the album, current summary, and generated summary.
10. Prompts for a decision:

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

Choosing Apply reuses the existing apply workflow, including backup creation,
Plex write, reload verification, and audit storage. Choosing Edit opens the
configured terminal editor and validates the edited text before asking again.

Planner actions map to prompts as follows:

- `CREATE`: `album_summary`
- `TRANSLATE`: `album_translate`
- `IMPROVE`: `album_improve`
- `REVIEW`: manual decision, no automatic AI call
- `SKIP`: no AI call

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
