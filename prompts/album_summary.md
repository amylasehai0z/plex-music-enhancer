# Album Summary Prompt

Write a concise German music encyclopedia article about the album.

Use approximately 80-120 words in one or two fluent paragraphs. The text should explain the album
as a coherent story, not merely summarize facts. It may feel close to a polished entry from
Musikexpress, Rolling Stone, AllMusic, or a high-quality Wikipedia article.

Artist: {{artist}}
Album: {{album}}
Genres: {{genres}}
Release date: {{release_date}}

Additional verified album context:
{{additional_metadata}}

Current Plex summary:
{{current_summary}}

Wikipedia extract:
{{wikipedia_extract}}

Shape the article naturally from the available facts. Do not add headings, labels, or sections, but
let the prose follow this editorial arc:

1. Introduction: release date, artist, verified historical context, and the album's place in the
   artist's catalog.
2. Career context: career phase, discography position, previous album, next album, stylistic
   development, comeback/final/debut status, and years active when supplied.
3. Musical style: genres, stylistic contrasts, influences, development from earlier work, and
   recurring musical ideas when supplied.
4. Production: producer, label, recording context, recording period, recording studios,
   collaborators, and guest musicians when supplied.
5. Notable characteristics: composers, lyricists, important songs, singles, album structure,
   concept-album form, opening or closing tracks, and distinctive musical features when supplied.
6. Closing classification: a concise final sentence that classifies the album's verified role
   within the artist's work or its documented musical context.

Writing style:

- Write idiomatic, natural German with varied sentence openings.
- Build a coherent narrative with natural transitions between career context, style, production,
  and notable characteristics.
- Prefer concise, information-rich encyclopedia language.
- Explain connections between facts instead of presenting the album in isolation.
- Discuss track-level context as part of the album's musical narrative; never enumerate tracks.
- Integrate facts naturally; never output metadata lists or field/value prose.
- Use Last.fm community tags only as supporting context for style signals; never present community
  opinions or listener behavior as objective facts.
- Avoid filler, marketing language, repeated facts, and AI-style wording.
- Avoid repeated sentence starts such as "Das Album ...".
- Avoid phrases like "ist den Genres ... zuzuordnen".
- Do not use bullet lists or Markdown formatting.

Factual safety:

- Use only the supplied metadata.
- Emphasize highly verified information.
- Use probable facts carefully and weak facts only as background context.
- Never resolve conflicting facts by guessing.
- Never invent missing facts.
- Avoid presenting uncertain information as established fact.
- Never invent chart positions, certifications, awards, reviews, commercial success, or influence.
- Never invent career milestones, career phases, commercial success, reception, chart success,
  certifications, collaborations, influence, or legacy.
- Never infer commercial peak or later influence without explicit evidence in the supplied context.
- Never invent singles, hit singles, standout tracks, concept-album status, themes, or track
  significance.
- Never output a track listing.
- If data is missing, omit that aspect silently.
- If the supplied information is sparse, write a polished but restrained description.

Return only the finished German album article.
