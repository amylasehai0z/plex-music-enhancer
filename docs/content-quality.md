# Content Quality

The Content Optimization Engine analyzes existing Plex album summaries before any AI provider is
called. It is deterministic and read-only.

## Quality Report

Each summary receives a `ContentQualityReport`:

- `quality_score`: integer from `0` to `100`
- `quality_level`: `EXCELLENT`, `GOOD`, `FAIR`, or `POOR`
- `issues`: detected quality problems

Supported issue codes:

- `SHORT`
- `PLACEHOLDER`
- `REPETITIVE`
- `MACHINE_TRANSLATION`
- `LOW_READABILITY`
- `UNKNOWN_LANGUAGE`
- `EXCESSIVE_WHITESPACE`
- `FORMATTING_PROBLEMS`
- `INCOMPLETE_SENTENCE`
- `MISSING`

## Checks

The analyzer evaluates:

- detected language
- summary length
- sentence readability
- placeholder markers such as `TODO` or template variables
- repeated three-word phrases
- awkward machine-translation-like German wording
- excessive whitespace
- Markdown, bullet lists, and heading markers
- whether the text ends like a complete sentence

The score intentionally favors conservative decisions. Suspicious text is routed to `IMPROVE` or
`REVIEW` rather than treated as complete.

## Planner Integration

The planner uses the quality report only after language detection:

- no summary: `CREATE`
- English summary: `TRANSLATE`
- German summary below `60`: `IMPROVE`
- German summary from `60` through `80`: `REVIEW`
- German summary above `80`: `SKIP`
- unknown or other language: `REVIEW`

Only `CREATE`, `TRANSLATE`, and `IMPROVE` invoke AI in batch review. `SKIP` is recorded immediately,
and `REVIEW` asks the user without generating text automatically.
