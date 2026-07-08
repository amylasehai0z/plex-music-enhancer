# Album Translation Prompt

Translate the current Plex album summary into natural {{language}}.

Artist: {{artist}}
Album: {{album}}
Release date: {{release_date}}
Genres: {{genres}}

Current Plex summary:
{{current_summary}}

Supporting reference extract:
{{wikipedia_extract}}

Requirements:

- Use the current Plex summary as the primary source.
- Preserve all factual information from the current summary.
- Remove awkward wording and make the German prose natural.
- Keep an encyclopedic, neutral style.
- Do not invent facts or add claims that are not supported.
- Do not use bullet lists or Markdown formatting.
- Return only the translated German album summary.
