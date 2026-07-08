# Planner

The planner classifies every album into the safest workflow before generation. It reuses the same
album candidates collected by batch review and never modifies Plex.

## Actions

`CREATE`

: The album has no usable summary. The normal album-summary prompt can create a new German
description from collected metadata.

`TRANSLATE`

: The existing summary appears to be English. The translation workflow uses the current Plex summary
as the primary source and preserves factual content.

`IMPROVE`

: The existing summary appears to be German but has a quality score below `60`. The improvement
workflow improves wording only and preserves every factual statement.

`REVIEW`

: The summary is ambiguous, another language, or German with a quality score from `60` through `80`.
The user decides whether to skip, edit, or continue manually.

`SKIP`

: The existing German summary scores above `80`, so generation is unnecessary.

## Batch Behavior

`plex-enhancer batch review` executes the planner automatically:

- `CREATE` uses `prompts/album_summary.md`
- `TRANSLATE` uses `prompts/album_translate.md`
- `IMPROVE` uses `prompts/album_improve.md`
- `REVIEW` asks the user and does not call AI automatically
- `SKIP` records the item as skipped

This keeps batch processing predictable and avoids unnecessary provider calls for summaries that are
already good enough or need human classification first.

## Command

```bash
plex-enhancer plan --library "Music"
plex-enhancer plan --json
```

The command displays the album, detected language, current summary length, recommended action, and
reason. JSON output includes the full `ContentQualityReport`.
