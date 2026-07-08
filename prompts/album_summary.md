# Album Summary Prompt

Write a professionally crafted encyclopedic album description in natural {{language}}.

Use approximately 80-120 words in one fluent paragraph. The text should read like an
original encyclopedia entry, not like a compressed or translated Wikipedia extract.

Artist: {{artist}}
Album: {{album}}
Genres: {{genres}}
Release date: {{release_date}}

Current Plex summary:
{{current_summary}}

Wikipedia extract:
{{wikipedia_extract}}

Structure the paragraph naturally:

1. Introduce the album and artist.
2. Describe musical style, sound, or production only when supported by the metadata.
3. Mention notable characteristics without long enumerations.
4. End with a concise closing sentence that summarizes the album's significance or character.

Style requirements:

- Write fluent German prose with varied sentence openings and smooth transitions.
- Keep a neutral, encyclopedic tone.
- Prefer concise wording over lists of facts.
- Avoid wording that sounds translated.
- Avoid repetitive release date references.
- Do not write phrases like "ist den Genres ... zuzuordnen".
- Do not use bullet lists, Markdown formatting, or marketing language.

Factual safety:

- Use only the supplied metadata.
- Never invent facts, reception, personnel, chart positions, awards, or influence.
- If the supplied information is sparse, state only the verifiable facts in polished prose.

Return only the finished German album description.
