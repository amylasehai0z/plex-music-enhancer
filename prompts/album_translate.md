# Album Translation Prompt

Translate the current Plex album summary into natural German encyclopedia prose.

Artist: {{artist}}
Album: {{album}}
Release date: {{release_date}}
Genres: {{genres}}

Current Plex summary:
{{current_summary}}

Supporting reference extract:
{{wikipedia_extract}}

Requirements:

- Translate meaning, not wording.
- Preserve every factual statement exactly.
- Do not summarize, condense, omit, or add facts.
- Improve sentence flow where needed so the German reads naturally.
- Keep an encyclopedic, neutral tone suitable for a music reference work.
- Preserve artist names, album titles, song titles, label names, dates, catalog information, and
  proper names.
- Preserve producer, songwriter, lyricist, arranger, engineer, label, recording, studio, chart,
  certification, and guest musician information when already present.
- Preserve track information, singles, album-structure details, concept-album context, and editorial
  context when already present.
- Avoid literal English phrasing, filler, marketing language, Markdown, and bullet lists.
- Return only the translated German album summary.
