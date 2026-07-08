# Smart Enrichment Planning

The planner decides which enrichment strategy is safest before any metadata is generated.

## Command

```bash
plex-enhancer plan
plex-enhancer plan --library "Music"
plex-enhancer plan --json
```

The report shows:

- album
- detected current language
- current summary length
- recommended action
- reason

## Actions

`CREATE`

: The album has no summary. The default album metadata prompt should create a new German summary.

`TRANSLATE`

: The existing summary appears to be English. The translation prompt should use the Plex summary as
the primary source and preserve factual content.

`IMPROVE`

: The existing summary appears to be German, but its quality score is below `60`. The improvement
prompt should preserve facts while improving readability and flow.

`SKIP`

: The existing German summary scores above `80`. No generation is needed.

`REVIEW`

: The summary language is unknown, neither clearly German nor English, or German content scores from
`60` through `80`. Batch review asks for a manual decision instead of silently choosing generation.

## Content Quality

German summaries are scored from `0` to `100` before an action is chosen. The analyzer checks:

- detected language
- summary length
- readability
- placeholder text
- duplicated phrases
- machine-translation-like wording
- excessive whitespace
- Markdown or list formatting
- incomplete sentence endings

Quality levels are:

- `EXCELLENT`
- `GOOD`
- `FAIR`
- `POOR`

## Batch Review

`plex-enhancer batch review --all` uses the planner automatically:

- `CREATE` uses `album_summary`
- `TRANSLATE` uses `album_translate`
- `IMPROVE` uses `album_improve`
- `SKIP` is recorded without generation
- `REVIEW` asks the user and does not invoke AI automatically

The planner is read-only. It performs no AI calls and no Plex writes.
