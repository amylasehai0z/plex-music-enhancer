# Library Workflow

The library workflow processes an entire Plex music library from planning through review and apply.
It reuses the planner, review workflow, prompt engine, AI manager, and apply service.

## Commands

```bash
plex-enhancer library plan --library "Music"
plex-enhancer library review --library "Music"
plex-enhancer library apply --library "Music"
plex-enhancer library resume --library "Music"
plex-enhancer library report --library "Music"
```

## Plan

`library plan` scans the selected music library and groups albums by planner action:

- `CREATE`
- `TRANSLATE`
- `IMPROVE`
- `REVIEW`
- `SKIP`

The report includes counts and estimated processing time. Only `CREATE`, `TRANSLATE`, and
`IMPROVE` have generation time estimates.

## Review

`library review` automatically iterates through albums planned as:

- `CREATE`
- `TRANSLATE`
- `IMPROVE`

For each album it displays:

- artist
- album
- current summary
- generated summary
- planner decision
- quality score

User choices are:

- Apply: approve the generated summary for a later `library apply` run
- Skip: record the item as skipped
- Edit: edit and revalidate the proposed summary
- Quit: pause the session

Review does not write to Plex.

## Apply

`library apply` loads approved review items from the saved session and applies them with the existing
safe apply workflow. Backups, verification, and audit logging are handled by `ApplyService`.

## Resume

`library resume` continues an interrupted review session. Completed rating keys are read from the
session file, so already reviewed albums are not regenerated.

Session files are stored under:

```text
exports/library/
```

## Report

`library report` summarizes the saved session:

- albums processed
- created
- translated
- improved
- skipped
- approved
- applied
- failed
- average quality score
- average generation time

Use `--json` to print JSON or `--export-json` to write:

```text
exports/library/report.json
```

The workflow does not change metadata during planning, review, resume, or report. Plex writes only
occur during `library apply`.
