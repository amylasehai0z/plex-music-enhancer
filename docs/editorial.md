# Editorial Engine

The editorial layer separates factual data collection from writing guidance. It prepares structured
context for the language model but never generates prose itself.

## Responsibilities

- Prioritize important facts.
- Remove duplicate facts from multiple providers.
- Organize a natural story order.
- Identify missing context that must not be invented.
- Provide German encyclopedia-style writing guidance.

## Album Composition

Album guidance can include:

- opening focus
- career context
- recording context
- musical style
- production and personnel context
- notable tracks
- historical or legacy context
- important facts and avoid topics

## Artist Composition

Artist guidance can include:

- origins
- career development
- musical style
- major albums
- collaborations
- influence and legacy

Unavailable sections are omitted automatically. The prompt should never contain empty sections or
field/value dumps.
