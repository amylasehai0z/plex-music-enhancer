# MusicBrainz Matching

The MusicBrainz matcher is a read-only service implemented in
`src/plex_music_enhancer/services/musicbrainz_matcher.py`.

## Input

The matcher accepts Plex album identity fields:

- artist name
- album title
- release year, when available

It does not modify Plex and does not use AI.

## Workflow

1. Search MusicBrainz artists.
2. Select the best artist candidate using:
   - exact artist-name match
   - alias match
   - disambiguation text
   - MusicBrainz search score
3. Search MusicBrainz release groups using the selected artist name and album
   title.
4. Score each release-group candidate using:
   - artist similarity
   - album-title similarity
   - release-year proximity
   - release type
   - MusicBrainz search score
5. Return the highest-confidence `MatchResult`.

## Fuzzy Matching

The matcher uses `rapidfuzz` for string similarity. Scores are normalized onto a
0-100 scale. A small stdlib fallback exists only so local tests can run in
restricted environments before dependencies are installed; production installs
use `rapidfuzz`.

Artist candidates are rejected below a confidence of `70`.

Release-group matches are rejected below a confidence of `75`.

## Score Breakdown

`MatchResult.score_breakdown` includes:

- `artist_candidate`
- `artist_similarity`
- `album_similarity`
- `release_year`
- `release_type`
- `musicbrainz_score`

This is intended to make every match auditable before future write workflows use
the result.

## Caching

Match results are cached transparently.

- Cache directory: `~/.plex-enhancer/cache/musicbrainz/matches/`
- Cache key: SHA-256 of normalized artist, album, and release year
- Cache lifetime: 30 days

The matcher cache stores both successful and rejected results. This avoids
repeating MusicBrainz searches for the same Plex album during repeated scans.

## CLI

The public matching command runs the same read-only workflow:

```bash
plex-enhancer match --artist "Nina Simone" --album "Pastel Blues"
```

It prints a Rich report containing:

- artist
- album
- confidence
- MusicBrainz artist ID
- release-group ID
- release ID
- release year
- primary type
- secondary types
- warnings

To print the complete `MatchResult` model:

```bash
plex-enhancer match --artist "Nina Simone" --album "Pastel Blues" --json
```

The command uses the existing MusicBrainz provider, which uses `httpx`, enforces
the MusicBrainz User-Agent, retries transient failures, respects rate limits,
and performs transparent caching. It does not write to Plex.
