# Artist Biography Prompt

Write a concise German music encyclopedia biography about the artist.

Use approximately 90-140 words in one or two fluent paragraphs. The text should read like a
professionally edited reference article, not like promotional copy or a generic AI response.

Artist: {{artist}}
Genres: {{genres}}
Active or birth date context: {{release_date}}

Additional verified artist context:
{{additional_metadata}}

Current Plex biography:
{{current_summary}}

Reference extract:
{{wikipedia_extract}}

Shape the biography naturally from the available facts. Do not add headings, labels, or sections,
but let the prose follow this editorial arc when information exists:

1. Introduction: verified identity, origin, and role in music history.
2. Origins: birth name, birthplace, nationality, and early context when supplied.
3. Career development: active years, milestones, musical evolution, and major phases.
4. Musical style: genres, style signals, occupations, and performance character.
5. Major albums: notable albums or works only when explicitly supplied.
6. Collaborations: members, associated acts, labels, or partnerships when supplied.
7. Influence and legacy: influence, awards, and historical relevance only when verified.
8. Closing: a concise classification of the artist's documented place in music.

Writing style:

- Write idiomatic, natural German with varied sentence openings.
- Build a coherent narrative with natural transitions between origins, career, style, and legacy.
- Prefer concise, information-rich encyclopedia language.
- Integrate facts naturally; never output metadata lists or field/value prose.
- Use Last.fm community tags only as supporting style context.
- Avoid fan language, marketing language, subjective praise, and filler.
- Do not use bullet lists or Markdown formatting.

Factual safety:

- Use only the supplied metadata.
- Emphasize highly verified information.
- Use probable facts carefully and weak facts only as background context.
- Never resolve conflicting facts by guessing.
- Never invent missing facts.
- Never invent awards, collaborations, influence, milestones, labels, or notable albums.
- If data is missing, omit that aspect silently.
- If the supplied information is sparse, write a polished but restrained biography.

Return only the finished German artist biography.
