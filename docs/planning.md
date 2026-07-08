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

: The existing summary appears to be German but is shorter than the configured threshold. The
improvement prompt should preserve facts while improving readability and flow.

`SKIP`

: The existing German summary appears complete enough. No generation is needed.

`REVIEW`

: The summary language is unknown or neither clearly German nor English. Batch review keeps the item
available for manual review instead of silently choosing a translation or improvement strategy.

## Batch Review

`plex-enhancer batch review --all` uses the planner automatically:

- `CREATE` uses `album_summary`
- `TRANSLATE` uses `album_translate`
- `IMPROVE` uses `album_improve`
- `SKIP` is recorded without generation
- `REVIEW` uses the default album summary prompt and leaves the final decision to the user

The planner is read-only. It performs no AI calls and no Plex writes.
