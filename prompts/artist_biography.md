# Artist Biography Prompt

Write a concise German music encyclopedia biography about the artist.

Use {{minimum_words}}-{{maximum_words}} words in two fluent paragraphs. The text should read like a
professionally edited reference article: precise, neutral, and focused on significance rather than
exhaustive biography. When evidence is sparse, stay restrained.

Artist: {{artist}}
Genres: {{genres}}
Active or birth date context: {{release_date}}

Additional verified artist context:
{{additional_metadata}}

Current Plex biography:
{{current_summary}}

Reference extract:
{{wikipedia_extract}}

Write a coherent narrative from the supplied facts. Do not add headings, labels, bullets, or
sections. Prefer explaining why the artist is historically or musically important over listing
events in chronological order.

Every fact already present anywhere in this prompt is usable evidence. This includes structured
facts, Current Plex biography, Reference extract, Wikipedia-derived context, Discogs, Last.fm, and
verified context. Missing structured fields do not forbid using the same topic when it appears in
the narrative sources. When additional documented career developments, historically important
works, or lasting legacy appear later in those sources, naturally incorporate the most relevant
ones without becoming exhaustive.

Editorial focus:

1. Opening: identify the artist through verified origin, style, role, or significance.
2. Career meaning: foreground breakthrough moments, historically important works,
   career-defining achievements, international recognition, and lasting influence when they are
   supplied.
3. Musical development: connect genre, sound, performance character, or artistic influence only
   where it explains the artist's importance.
4. Closing: when evidence supports it, finish with lasting influence, enduring popularity, later
   recognition, later career developments, documented cultural significance, or the artist's place
   in music history. Avoid ending only with sales figures, chart performance, or commercial success
   unless that is genuinely the strongest documented conclusion.

Context priority:

1. Verified metadata and high-confidence probable facts.
2. Structured artist facts and resolved relationships.
3. Current Plex biography.
4. Focused Wikipedia context.
5. Unique Discogs context.
6. Last.fm context only as supporting style or community context.

Writing style:

- Write idiomatic, natural German with varied sentence openings.
- Prefer narrative prose over chronological fact dumping.
- Include only facts that help explain significance, breakthrough, career role, recognized works,
  achievements, influence, or legacy.
- Use genre information only to characterize the artist's musical profile; never let genre lists,
  aliases, script variants, or administrative metadata dominate the biography.
- Avoid generic LLM phrasing such as "zeichnet sich aus", "beeindruckt durch",
  "facettenreich", "vielschichtig", or "nimmt den Hörer mit".
- Avoid dictionary-style openings, fan language, marketing tone, subjective praise, and filler.
- Do not repeat the artist name unnecessarily.
- Do not use bullet lists, Markdown formatting, metadata lists, or field/value prose.

Factual safety:

- Use only facts supplied in this prompt.
- Emphasize verified facts, but treat narrative-source facts as usable evidence too.
- Treat probable facts carefully and weak facts only as background context.
- Never resolve conflicting facts by guessing.
- Never invent unsupported facts.
- Do not invent birth details, nationality, breakthrough moments, major works, collaborations,
  influence, awards, milestones, recognition, or international success when they are absent from
  all supplied context.
- If these topics are present in any supplied source, you may summarize them naturally.
- If information is absent or uncertain, omit it silently.
- If the supplied information is sparse, write a restrained biography based only on verifiable
  facts.

Return only the finished German artist biography.
