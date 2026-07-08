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
- Translate only; do not summarize or condense the text.
- Preserve all factual information from the current summary.
- Do not omit factual information.
- Remove awkward wording and make the German prose natural.
- Keep an encyclopedic, neutral style.
- Do not invent facts or add claims that are not supported.
- Keep artist names, album titles, song titles, label names, and proper names in their original language.
- Translate prose only.
- Preserve release dates and track titles exactly.
- Do not use bullet lists or Markdown formatting.
- Return only the translated German album summary.
