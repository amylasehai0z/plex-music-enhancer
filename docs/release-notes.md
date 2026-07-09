# Release Notes

## Version 1.0.0

Plex Music Enhancer v1.0.0 ist der erste stabile öffentliche Release. Der Schwerpunkt liegt auf sicherer Anwendung, nachvollziehbaren Workflows, deutschsprachiger Texterzeugung und Produktionsreife für reale Plex-Musikbibliotheken.

## Hauptfunktionen

### Plex-Grundlage

- Verbindung zu Plex über URL und Token
- Musikbibliotheken scannen
- Künstler, Alben und Tracks lesen
- Metadaten inspizieren
- Audit vorhandener Texte
- Capability-Analyse

### Metadatenanbieter

Unterstützt:

- MusicBrainz
- Wikipedia
- Discogs
- Last.fm

MusicBrainz und Wikipedia funktionieren ohne Zugangsdaten. Discogs und Last.fm sind optional.

### MusicBrainz Matching

- Artist-Matching
- Release-Group-Matching
- Fuzzy Matching
- Confidence Score
- Warnungen bei schwachen Treffern

### Enrichment Pipeline

- `AlbumContext`
- `ArtistContext`
- Zusammenführung aller Quellen
- Knowledge Graph
- Faktenprüfung
- fehlende Felder und Warnungen

### KI-Erzeugung

- Provider-unabhängige AI-Schicht
- DummyProvider für Tests
- OpenAIProvider für Produktion
- Prompt Engine mit Markdown-Vorlagen
- Prompt-Versionierung

### Deutsche Editorial Engine

- professionelle deutsche Musiklexikon-Sprache
- strukturierte Schreibführung
- Stilprüfung
- Vermeidung von Listen und Marketington
- vorsichtige Faktenintegration

### Review-System

- Current Summary
- Generated Summary
- Unified Diff
- Qualitätsprüfung
- Stilprüfung
- Faktenübersicht
- interaktive Auswahl Apply/Edit/Skip/Quit

### Sicherer Apply Workflow

- Backup vor Änderung
- Schreiben über PlexAPI
- Reload aus Plex
- Verifikation des geschriebenen Textes
- Audit-Protokoll
- strukturierte Fehlerergebnisse

### Batch und Library

- Batch Review
- Library Plan
- Library Review
- Library Resume
- Library Apply
- Library Report
- Fortschrittsspeicherung

### Performance

- lokaler Cache
- Provider Scheduling
- Retry Framework
- SQLite Processing Database
- Benchmark-Befehl
- inkrementelle Verarbeitung

## Wichtige Befehle

```bash
plex-enhancer doctor
plex-enhancer scan
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
plex-enhancer library plan --library "Music"
plex-enhancer benchmark --library "Music"
```

## Sicherheitsmodell

v1.0.0 schreibt nie unbeabsichtigt in Plex. Schreibvorgänge sind explizit, gesichert und verifiziert.

## Bekannte Grenzen

- Kein automatischer Rollback-Befehl als Hauptworkflow.
- `ollama` ist als AI-Anbietername reserviert, aber nicht verfügbar.
- Providerdaten können je nach öffentlicher Datenlage fehlen.
- Review bleibt notwendig, weil KI-Texte trotz Schutzmaßnahmen geprüft werden müssen.

## Upgrade-Hinweise

Vor großen Läufen:

```bash
plex-enhancer doctor
plex-enhancer cache stats
plex-enhancer benchmark --library "Music"
```

Wenn sich Prompts oder Providerdaten stark geändert haben, kann ein Cache-Refresh sinnvoll sein.

