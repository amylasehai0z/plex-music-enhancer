# PDF publishing

The handbook PDF is built with Pandoc and XeLaTeX.

Logo sources are intentionally split by output target:

- `assets/logo/plex-music-enhancer-logo.svg` is for GitHub, README and web assets.
- `assets/logo/plex-music-enhancer-logo.pdf` is the single logo source for LaTeX handbook generation.

The PDF template loads the logo with `\includegraphics`. It must not draw a
fallback logo and does not require Inkscape, the LaTeX `svg` package or
`includesvg`.

Build the handbook with:

```bash
make pdf
```

The stable output path is:

```text
assets/pdf/Plex-Music-Enhancer-Handbuch.pdf
```
