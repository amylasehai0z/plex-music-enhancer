# Quality Engine

The Editorial Quality Assurance engine evaluates generated German album and artist descriptions
before approval or write-back. It is deterministic, reproducible and does not call AI.

## What It Measures

- metadata completeness
- verified fact coverage
- verification confidence
- editorial structure
- German-language signal
- readability
- style consistency
- formatting
- missing opportunities

## Outputs

`QualityReport` includes:

- overall score and level
- scored checks
- recommendations
- warnings
- missing topics
- style metrics
- verification metrics
- metadata coverage
- editorial metrics
- timestamp

## Apply Safety

Apply can enforce a configured minimum QA score:

```bash
PLEX_ENHANCER_QUALITY__MINIMUM_QUALITY_SCORE=85
```

The `--force` option exists for explicit operator override on single apply commands. Batch and
library workflows should use configured thresholds conservatively.
