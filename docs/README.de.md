# Plex Music Enhancer v1.1

**Plex Music Enhancer** ist ein Werkzeug für Plex-Musikbibliotheken. Es hilft dabei, fehlende oder schwache Album- und Künstlerbeschreibungen auf Deutsch zu erzeugen, zu prüfen und sicher nach Plex zu übernehmen.

Die Dokumentation richtet sich an Plex-Nutzerinnen und Plex-Nutzer, Musikliebhaber, Sammlerinnen und Einsteiger ohne Programmiererfahrung.

## Wozu dient das Projekt?

Viele Plex-Musikbibliotheken enthalten unvollständige, englische oder stilistisch uneinheitliche Beschreibungen. Plex Music Enhancer sammelt Metadaten aus Plex und unterstützten Quellen, bereitet daraus einen strukturierten Kontext auf und erzeugt daraus eine sachliche deutsche Beschreibung. Vor jeder Übernahme wird der Text geprüft und kann manuell bearbeitet werden.

## Wichtigste Eigenschaften

| Bereich | Funktion |
| --- | --- |
| Sicherheit | Vorschau, Review, Backup, Verifikation und Audit vor und nach Schreibvorgängen |
| Quellen | Plex, MusicBrainz, Wikipedia, Discogs, Last.fm |
| KI | OpenAI-Anbindung und lokaler Testanbieter |
| Qualität | Prüfung von Sprache, Länge, Stil, Faktenabdeckung und Formatierung |
| Bibliotheken | Einzelalbum, Künstler, Batch- und vollständige Library-Workflows |
| Betrieb | Cache, Benchmark, JSON-Exporte und fortsetzbare Sitzungen |

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev,ai,metadata]"
plex-enhancer login
plex-enhancer doctor
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
```

Unter Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".[dev,ai,metadata]"
plex-enhancer login
plex-enhancer doctor
```

## Unterstützte Workflows

- ein einzelnes Album prüfen und anwenden
- Künstlerbiografien erzeugen
- vorhandene englische Texte ins Deutsche übersetzen
- vorhandene deutsche Texte verbessern
- mehrere Alben im Batch prüfen
- eine komplette Musikbibliothek planen, prüfen und anwenden
- Cache und Performance überwachen

## Benutzerhandbuch

- [00 Titel](handbuch/00-titel.md)
- [01 Einleitung](handbuch/01-einleitung.md)
- [02 Installation](handbuch/02-installation.md)
- [03 Erste Schritte](handbuch/03-erste-schritte.md)
- [04 Konfiguration](handbuch/04-konfiguration.md)
- [05 CLI-Befehle](handbuch/05-cli-befehle.md)
- [06 Workflows](handbuch/06-workflows.md)
- [07 KI und Editorial Engine](handbuch/07-ki-und-editorial-engine.md)
- [08 Review-System](handbuch/08-review-system.md)
- [09 Provider](handbuch/09-provider.md)
- [10 Cache](handbuch/10-cache.md)
- [11 Fehlersuche](handbuch/11-fehlersuche.md)
- [12 FAQ](handbuch/12-faq.md)
- [13 Glossar](handbuch/13-glossar.md)
- [14 Anhang](handbuch/14-anhang.md)
- [15 Container, Portainer und Synology](handbuch/15-container.md)
- [16 Release Management](handbuch/16-release-management.md)

## PDF-Handbuch

Die PDF-Konfiguration liegt unter [docs/pdf](pdf/). Das Publishing-System erzeugt ein professionell gesetztes A4-Handbuch mit Pandoc und XeLaTeX.

Voraussetzungen:

- Pandoc
- Eine TeX-Distribution mit `xelatex`, zum Beispiel MacTeX oder TeX Live
- Optional: Noto Serif, Noto Sans und JetBrains Mono

```bash
docs/pdf/build.sh
```

Die Ausgabedatei heißt:

```text
assets/pdf/Plex-Music-Enhancer-Handbuch.pdf
```

Build-Artefakte lassen sich entfernen mit:

```bash
docs/pdf/clean.sh
```

Alternativ stehen Makefile-Ziele bereit:

```bash
make docs
make pdf
make handbook
make clean
```

Wenn der Build fehlschlägt, prüfen Sie zuerst, ob `pandoc` und `xelatex` im Terminal verfügbar sind. Das Skript meldet fehlende Kapitel, fehlende Werkzeuge und nicht erzeugte Ausgabedateien mit verständlichen Fehlermeldungen.

Das Handbuch lädt sein Logo aus `assets/logo/plex-music-enhancer-logo.pdf`.
Die SVG-Datei ist für GitHub, README und Web-Assets gedacht. Für den
LaTeX-Handbuchbuild wird keine SVG-Konvertierung verwendet; Inkscape, das
LaTeX-Paket `svg` und `includesvg` sind nicht erforderlich.
