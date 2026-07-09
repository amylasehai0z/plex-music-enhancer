# Plex Music Enhancer v1.0

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

## PDF-Handbuch

Die PDF-Konfiguration liegt unter [docs/pdf](pdf/). Wenn Pandoc installiert ist, kann das Handbuch mit folgendem Befehl erzeugt werden:

```bash
docs/pdf/build.sh
```

Die Ausgabedatei heißt:

```text
docs/pdf/Plex-Music-Enhancer-Handbuch-v1.0.pdf
```

