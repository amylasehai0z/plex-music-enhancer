# Verification

The verification engine evaluates collected metadata before it reaches prompt construction. It does
not contact external services. It only compares facts already collected from Plex and configured
providers.

## Fact States

- `verified`: strong agreement from authoritative or multiple sources
- `probable`: reliable but not fully corroborated
- `weak`: low-confidence or community-only support
- `conflicting`: provider values disagree
- `unknown`: no reliable value is available

## Outputs

`FactCollection` contains:

- verified facts
- conflicts
- missing factual categories

The editorial and QA layers use this information to emphasize reliable facts and avoid guessing
when provider data disagrees.

## Safety Rules

- Conflicts are exposed instead of silently resolved.
- Missing facts are not invented.
- Weak facts may be used as context but should not be presented as established claims.
