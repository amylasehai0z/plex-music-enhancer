# Prompt Engine

The prompt engine separates prompt construction from AI providers. Providers receive a
`RenderedPrompt` and do not need to know how Plex, MusicBrainz, or Wikipedia metadata is assembled.

## Files

Prompt engine code lives in:

```text
src/plex_music_enhancer/prompts/
```

Markdown templates live in:

```text
prompts/
```

Current templates:

- `album_summary.md`
- `artist_summary.md`

## Supported Placeholders

Templates may use:

- `{{artist}}`
- `{{album}}`
- `{{genres}}`
- `{{release_date}}`
- `{{wikipedia_extract}}`
- `{{current_summary}}`
- `{{language}}`

The registry rejects unsupported template variables. The renderer fails when a template references a
required variable that has not been supplied.

## Components

`PromptLoader` reads Markdown templates from disk.

`PromptRegistry` discovers templates, validates variables, and caches loaded templates.

`PromptRenderer` substitutes variables while preserving Markdown formatting.

`PromptBuilder` converts typed context models, such as `AlbumContext`, into `RenderedPrompt`.

## Provider Boundary

AI providers consume `RenderedPrompt` instead of `AlbumContext`. This keeps provider
implementations independent from Plex and metadata-provider model changes.

`AIManager` owns the bridge:

1. Receive `AlbumContext`.
2. Build a rendered prompt with `PromptBuilder`.
3. Dispatch the prompt to the configured AI provider.
4. Return `GeneratedSummary`.

## Safety

The prompt engine performs no networking and does not modify Plex. It only reads local Markdown
templates and renders text.
