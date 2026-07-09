# Album Improvement Prompt

Improve the existing German Plex album summary as concise music encyclopedia prose.

Artist: {{artist}}
Album: {{album}}
Release date: {{release_date}}
Genres: {{genres}}

Current German Plex summary:
{{current_summary}}

Supporting reference extract:
{{wikipedia_extract}}

Requirements:

- Preserve every factual statement, name, date, title, label, and catalog detail.
- Do not invent, remove, soften, or reinterpret facts.
- Remove repetition and awkward phrasing.
- Improve readability, transitions, rhythm, and paragraph flow.
- Prefer natural German over literal or AI-style wording.
- Keep a neutral, encyclopedic music-reference tone.
- Preserve producer, songwriter, lyricist, arranger, engineer, label, recording, studio, chart,
  certification, and guest musician information when already present.
- Preserve track information, singles, album-structure details, concept-album context, and editorial
  context when already present.
- Do not use bullet lists, Markdown formatting, or marketing language.
- Return only the improved German album summary.
