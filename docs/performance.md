# Production Performance and Scalability

Plex Music Enhancer v0.9 adds infrastructure for large libraries containing tens of
thousands of albums. The milestone does not change generated metadata. It improves
how work is scheduled, measured, resumed and skipped.

## Provider Scheduling

Independent provider lookups are coordinated by `ProviderScheduler`.

- MusicBrainz matching remains authoritative and runs before MusicBrainz metadata lookup.
- Independent supplemental providers such as Wikipedia, Discogs and Last.fm can run with
  bounded concurrency.
- Providers that are not configured are skipped before work is scheduled.
- Provider failures are captured as diagnostics and converted into empty context objects.

Configure concurrency with:

```bash
PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS=4
```

## Incremental Processing

Incremental mode compares a deterministic processing fingerprint against the persisted
processing database. Albums can be skipped when source inputs have not changed.

An album is eligible for regeneration when any of these inputs changes:

- Plex metadata hash
- provider versions
- cache schema/version
- prompt version
- configured model
- quality threshold
- relevant performance/configuration values

Incremental mode is enabled by default:

```bash
PLEX_ENHANCER_PERFORMANCE__INCREMENTAL_MODE=true
```

## Processing Database

Processing state is stored in SQLite. The default location is:

```text
~/.plex-enhancer/processing.sqlite3
```

Each record stores album and artist identifiers, provider versions, metadata and generation
hashes, quality score, generation status, prompt version, model, cache version, processing
duration and errors. Interrupted work can be resumed from records marked `PENDING` or
`FAILED`.

Configure the location with:

```bash
PLEX_ENHANCER_PERFORMANCE__DATABASE_LOCATION=/path/to/processing.sqlite3
```

## Cache Invalidation

The local knowledge cache still uses a time-to-live policy. Entries now also include a
schema version, optional provider version and optional prompt version. Schema upgrades
automatically invalidate older entries. The cache can also be partially cleared by source
from code, while the CLI `cache clear` remains a full clear for backwards compatibility.

## Retry Policy

The shared retry helper supports transient failures, timeouts, connection resets and
exponential backoff. Provider-specific policies can be layered on top without duplicating
retry loops.

Configure default retry attempts with:

```bash
PLEX_ENHANCER_PERFORMANCE__RETRY_ATTEMPTS=3
```

## Benchmark

Run a read-only performance diagnostic:

```bash
plex-enhancer benchmark --library Music
plex-enhancer benchmark --library Music --json
```

The report includes scan duration, throughput, CPU time, memory usage, cache freshness,
provider timings and operational recommendations.

## Expected Performance Ranges

Actual runtime depends on Plex server hardware, provider rate limits, network latency, cache warmth
and AI model latency. Use these ranges as planning guidance and verify with `benchmark` on the
target library.

| Library size | Cold cache expectation | Warm cache expectation | Notes |
| --- | --- | --- | --- |
| 100 albums | interactive planning run | fast repeat planning run | Good size for provider and prompt smoke tests. |
| 1,000 albums | suitable for a scheduled batch session | suitable for routine maintenance | Use resume and JSON reports. |
| 10,000 albums | split into resumable library sessions | incremental mode should skip unchanged albums | Benchmark first and keep provider concurrency conservative. |

Operational guidance:

- Cold cache runs spend most time on provider requests.
- Warm cache runs should mostly exercise Plex scanning, planning and local validation.
- Parallel providers improve latency for independent lookups but must still respect rate limits.
- Incremental mode is the preferred path for repeated maintenance after the first full pass.

## Large Library Guidance

- Use `library plan` before generation-heavy workflows.
- Keep the knowledge cache enabled for repeated runs.
- Use batch limits when testing new prompts or providers.
- Prefer incremental mode for routine maintenance.
- Monitor benchmark output after provider, prompt or model changes.
