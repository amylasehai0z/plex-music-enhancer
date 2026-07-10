# Plex Music Enhancer v1.0 Dokumentation

Willkommen zur deutschsprachigen Dokumentation von **Plex Music Enhancer**. Diese Anleitung richtet sich an alle, die ihre Plex-Musikbibliothek mit besseren deutschen Album- und Künstlertexten pflegen möchten, auch ohne Programmierkenntnisse.

## Was ist Plex Music Enhancer?

Plex Music Enhancer ist ein Kommandozeilenwerkzeug für Musikbibliotheken in Plex. Es liest vorhandene Plex-Metadaten, ergänzt sie mit zuverlässigen Quellen wie MusicBrainz, Wikipedia, Discogs und Last.fm, erzeugt daraus faktenbasierte deutsche Texte und lässt sie vor dem Schreiben sorgfältig prüfen.

Das Programm schreibt niemals ungefragt in Plex. Jede Änderung läuft über Vorschau, Prüfung, Backup, Schreiben, erneutes Laden und Verifikation.

## Warum gibt es dieses Projekt?

Viele Plex-Musikbibliotheken enthalten:

- fehlende Albumtexte
- englische oder schlecht übersetzte Beschreibungen
- unvollständige Künstlerbiografien
- uneinheitliche Schreibweise
- fehlende Quellenkontexte

Plex Music Enhancer hilft, diese Lücken kontrolliert zu schließen. Der Schwerpunkt liegt auf sachlichen, neutralen, gut lesbaren deutschen Texten.

## Hauptfunktionen

| Bereich | Funktion |
| --- | --- |
| Plex | Bibliotheken scannen, Alben und Künstler finden, Metadaten prüfen |
| Quellen | MusicBrainz, Wikipedia, Discogs, Last.fm |
| KI | Deutsche Album- und Künstlertexte mit konfiguriertem Anbieter erzeugen |
| Qualität | Sprache, Länge, Faktenabdeckung, Stil und Platzhalter prüfen |
| Sicherheit | Review, Diff, Backup, Apply-Verifikation und Audit-Protokoll |
| Große Bibliotheken | Batch-, Library-, Cache-, Benchmark- und Resume-Funktionen |

## Bildschirmbeispiele

Für eine spätere Dokumentationswebsite eignen sich Screenshots dieser Ausgaben:

- `plex-enhancer doctor`
- `plex-enhancer preview --artist "Jennifer Rush" --album "Credo"`
- `plex-enhancer review --artist "Jennifer Rush" --album "Credo"`
- `plex-enhancer library plan --library "Music"`
- `plex-enhancer benchmark --library "Music"`

> **Hinweis:** Die Kommandozeile zeigt farbige Tabellen und Abschnitte über Rich. Auf GitHub werden diese Ausgaben als Textbeispiele dokumentiert.

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

## Dokumentation

- [Installation](installation.md)
- [Konfiguration](configuration.md)
- [Erste Schritte](getting-started.md)
- [Befehlsreferenz](commands.md)
- [Workflows](workflows.md)
- [KI-Erzeugung](ai-generation.md)
- [Review-System](review-system.md)
- [Cache](cache.md)
- [Docker, GHCR, Portainer und Synology](docker.md)
- [Problembehebung](troubleshooting.md)
- [FAQ](faq.md)
- [Glossar](glossary.md)
- [Architektur](architecture.md)
- [Entwicklerhandbuch](developer.md)
- [Release Notes](release-notes.md)

## Sicherheitsprinzip

> **Wichtig:** Vorschau, Planung, Analyse und Review sind zunächst lesend. Geschrieben wird nur bei ausdrücklichem Apply. Vor einem Schreibvorgang wird ein Backup erstellt, danach wird das Ergebnis aus Plex erneut geladen und geprüft.

## Empfohlener Einstieg

1. Installation abschließen.
2. `plex-enhancer login` ausführen.
3. `plex-enhancer doctor` prüfen.
4. Ein einzelnes Album mit `preview` testen.
5. Mit `review` den Text ansehen.
6. Erst danach `apply` verwenden.
