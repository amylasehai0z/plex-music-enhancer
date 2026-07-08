# Preview Command

The preview command runs the first end-to-end enrichment flow without modifying Plex.

```text
plex-enhancer preview --artist "Artist" --album "Album"
```

Options:

- `--provider` overrides the configured AI provider for this preview.
- `--model` overrides the configured AI model for this preview.
- `--json` prints the complete preview document.
- `--save` writes `exports/previews/<artist>-<album>.json`.
- `--verbose` shows full Plex, MusicBrainz, Wikipedia, prompt, token, and timing diagnostics.
- `--translate` translates the current Plex summary into natural German.
- `--improve` improves an existing German Plex summary without changing factual content.

## Workflow

1. The command reads the configured Plex album through the enrichment pipeline.
2. The enrichment pipeline builds an `AlbumContext`.
3. `AIManager` loads the configured AI provider.
4. The prompt engine builds a `RenderedPrompt`.
5. The configured provider generates a German preview summary from the rendered prompt.
6. The command displays the generated summary, provider, model, prompt version, and warnings.

## Rewrite Modes

Default preview generates a new summary from the collected Plex, MusicBrainz, and Wikipedia
metadata.

`--translate` uses the current Plex summary as the primary source and asks the model to translate
it into natural German, preserving factual information, removing awkward wording, and avoiding
invented facts.

`--improve` assumes the current Plex summary is already German and asks the model to improve
readability, flow, and repetition while preserving every factual claim.

`--translate` and `--improve` are mutually exclusive. The same prompt modes are also available on
album review and apply:

```text
plex-enhancer review --artist "Artist" --album "Album" --translate
plex-enhancer apply --artist "Artist" --album "Album" --improve
```

Preview and review remain read-only. Apply still uses the existing backup, write verification, and
audit workflow; no Plex write behavior changes were introduced for these modes.

## Output Sections

- `GENERATED SUMMARY`: generated German text.
- `AI`: provider, model, and prompt version.
- `Warnings`: pipeline warnings collected while building context.

Use `--verbose` to also show:

- `PLEX`: local album identity and current summary.
- `MUSICBRAINZ`: match status, MBIDs, release date, and match confidence.
- `WIKIPEDIA`: article status and source details.
- `PROMPT`: prompt name, version, and variables used.
- Detailed `AI`: token usage and generation time.

## Prompt Behavior

The production album prompt asks the configured model to:

- write in German
- use an encyclopedic, neutral style
- use only supplied facts
- never invent information
- produce approximately 80-120 words
- avoid bullet lists
- avoid marketing language

If the supplied information is insufficient, the generated text should state only verifiable facts.

## Saved Preview

Saved preview JSON includes:

- `context`: the full `AlbumContext`
- `rendered_prompt`: the exact `RenderedPrompt`
- `generated_summary`: the provider output
- `generation_time_seconds`: measured generation time

## Safety

Preview is read-only. It does not apply metadata, create backups, call Plex write APIs, or modify
any Plex object. When using `DummyProvider`, no AI network calls are made. When using
`OpenAIProvider`, only the rendered prompt is sent to OpenAI.
