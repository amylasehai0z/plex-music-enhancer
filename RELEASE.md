# Release Checklist

Use this checklist for every public release.

## 1. Version

- Confirm the canonical version in `src/plex_music_enhancer/constants.py`.
- Confirm `plex-enhancer version` prints the same version.
- Confirm `pyproject.toml` uses Hatchling dynamic versioning from the canonical file.

## 2. Changelog

- Update `CHANGELOG.md` using Keep a Changelog format.
- Move unreleased notes into the release version.
- Confirm user-visible changes, fixes and compatibility notes are included.

## 3. Validation

Run:

```bash
black .
ruff check .
pytest
```

Optional coverage:

```bash
pytest --cov
```

## 4. Documentation Review

- README quick start works on a clean environment.
- Configuration documentation matches current settings.
- Provider documentation is current.
- Review, apply, batch and library docs match CLI behavior.
- Performance guide includes current benchmark guidance.

## 5. Benchmark

Run a read-only benchmark against a representative library:

```bash
plex-enhancer benchmark --library "Music"
plex-enhancer benchmark --library "Music" --json
```

Record cold-cache and warm-cache observations in release notes when relevant.

## 6. Packaging

```bash
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```

Inspect package metadata:

- license
- project URLs
- classifiers
- entry points
- README rendering

## 7. Git

```bash
git status
git tag v1.0.0
git push origin main --tags
```

Use the actual version tag for non-v1.0 releases.

## 8. GitHub Release

- Create a release from the tag.
- Paste changelog highlights.
- Attach artifacts if the release process produces them.

## 9. PyPI Release

```bash
twine upload dist/*
```

Verify installation:

```bash
python -m pip install plex-music-enhancer
plex-enhancer version
```
