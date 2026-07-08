# Review Workflow

The review command lets a user inspect, edit, and approve generated summaries before any Plex write
workflow exists.

```text
plex-enhancer review --artist "Artist" --album "Album"
```

Options:

- `--provider` overrides the configured AI provider.
- `--model` overrides the configured AI model.
- `--json` prints the complete review document without entering the interactive loop.

## Workflow

1. Load the album from Plex through the enrichment pipeline.
2. Build `AlbumContext`.
3. Render the prompt through the prompt engine.
4. Generate a summary through `AIManager`.
5. Compare the generated summary with the current Plex summary.
6. Validate generated text quality.
7. Ask the user to apply, edit, skip, or quit.

## Interactive Choices

- `A` Apply: not implemented yet. If quality does not pass, Apply is blocked.
- `E` Edit: opens the terminal editor, then revalidates and redraws the diff.
- `S` Skip: exits without changes.
- `Q` Quit: exits without changes.

Apply intentionally performs no Plex writes in this milestone.

## Quality Checks

The review workflow creates a `QualityReport` with these checks:

- German-language signal
- configured word-count range
- no Markdown
- no bullet lists
- no placeholder text
- non-empty output

Status values:

- `PASS`: no warnings or failures
- `WARNINGS`: editable issues such as length or language signal
- `FAILED`: output that can never be applied, such as empty text, Markdown, bullets, or placeholders

Generated or edited summaries must pass validation before Apply can ever be enabled.

## Safety

Review is read-only. It does not modify Plex, create backups, apply metadata, or perform rollback.
