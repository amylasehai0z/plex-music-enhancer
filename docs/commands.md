# Befehlsreferenz

Diese Seite beschreibt alle öffentlichen Befehle von Plex Music Enhancer v1.0.

Allgemeines Muster:

```bash
plex-enhancer <befehl> [optionen]
```

Globale Option:

```bash
plex-enhancer --log-level DEBUG doctor
```

## `version`

Zeigt die installierte Version.

```bash
plex-enhancer version
```

Typische Ausgabe:

```text
plex-enhancer 1.0.0
```

## `doctor`

Prüft die lokale Installation und Konfiguration.

```bash
plex-enhancer doctor
```

Prüft:

- Python-Version
- Plex-Konfiguration
- Plex-Verbindung
- AI-Anbieter
- API Key
- Cache-Status
- Prompt-Version

Best Practice: Immer zuerst ausführen, wenn etwas nicht funktioniert.

## `login`

Speichert Plex-URL und Plex-Token in `.env`.

```bash
plex-enhancer login
```

Das Token wird versteckt eingegeben. Andere `.env` Variablen bleiben erhalten.

Fehler:

| Meldung | Bedeutung |
| --- | --- |
| `Invalid Plex URL` | URL ist ungültig |
| `Unable to connect to Plex` | URL, Token oder Netzwerk prüfen |

## `audit`

Analysiert vorhandene Künstler- und Albumtexte in Plex.

```bash
plex-enhancer audit
plex-enhancer audit --export-json
```

Export:

```text
exports/audit.json
```

## `plan`

Plant, welche Alben erstellt, übersetzt, verbessert, geprüft oder übersprungen werden sollten.

```bash
plex-enhancer plan --library "Music"
plex-enhancer plan --library "Music" --json
```

Aktionen:

- `CREATE`
- `TRANSLATE`
- `IMPROVE`
- `REVIEW`
- `SKIP`

## `scan`

Scannt Plex-Musikbibliotheken.

```bash
plex-enhancer scan
plex-enhancer scan --export-json
plex-enhancer scan artists --export-json
plex-enhancer scan albums --export-json
```

Exporte:

- `exports/libraries.json`
- `exports/artists.json`
- `exports/albums.json`

## `metadata album`

Sammelt normalisierte Album-Metadaten ohne Plex zu verändern.

```bash
plex-enhancer metadata album --artist "Jennifer Rush" --album "Credo"
plex-enhancer metadata album --artist "Jennifer Rush" --album "Credo" --json
plex-enhancer metadata album --artist "Jennifer Rush" --album "Credo" --save
```

## `context album`

Erstellt den vollständigen `AlbumContext`.

```bash
plex-enhancer context album --artist "Jennifer Rush" --album "Credo"
plex-enhancer context album --artist "Jennifer Rush" --album "Credo" --json
plex-enhancer context album --artist "Jennifer Rush" --album "Credo" --save
```

Der Kontext enthält Plex-, MusicBrainz-, Wikipedia-, Discogs-, Last.fm-, Verifikations- und Pipeline-Daten.

## `preview`

Erzeugt eine Vorschau für ein Album, ohne in Plex zu schreiben.

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
```

Optionen:

| Option | Bedeutung |
| --- | --- |
| `--provider` | AI-Anbieter überschreiben |
| `--model` | Modell überschreiben |
| `--json` | komplette JSON-Ausgabe |
| `--save` | JSON unter `exports/previews/` speichern |
| `--verbose` | vollständige Diagnose anzeigen |
| `--translate` | vorhandenen Text ins Deutsche übersetzen |
| `--improve` | vorhandenen deutschen Text verbessern |

`--translate` und `--improve` dürfen nicht gemeinsam verwendet werden.

## `preview artist`

Erzeugt eine Künstlerbiografie als Vorschau.

```bash
plex-enhancer preview artist --artist "Jennifer Rush"
plex-enhancer preview artist --artist "Jennifer Rush" --json
```

## `review`

Startet die interaktive Prüfung für ein Album.

```bash
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
```

Optionen:

- `--translate`
- `--improve`
- `--json`
- `--provider`
- `--model`

Interaktive Auswahl:

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

## `review artist`

Interaktive Prüfung einer Künstlerbiografie.

```bash
plex-enhancer review artist --artist "Jennifer Rush"
```

## `apply`

Erzeugt, prüft und schreibt eine Album-Zusammenfassung sicher nach Plex.

```bash
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
plex-enhancer apply --artist "Jennifer Rush" --album "Credo" --json
```

Optionen:

- `--translate`
- `--improve`
- `--provider`
- `--model`
- `--json`
- `--force`

> **Warnung:** `--force` überschreibt nur die konfigurierte QA-Schwelle. Es überspringt nicht Backup, Write-Verifikation oder Audit.

## `apply artist`

Schreibt eine geprüfte Künstlerbiografie sicher nach Plex.

```bash
plex-enhancer apply artist --artist "Jennifer Rush"
```

## `batch review`

Bearbeitet mehrere Alben in einer interaktiven Sitzung.

```bash
plex-enhancer batch review --library "Music" --missing-only --limit 25
plex-enhancer batch review --library "Music" --resume
```

Optionen:

| Option | Bedeutung |
| --- | --- |
| `--library` | Bibliothek auswählen |
| `--missing-only/--all` | nur fehlende Texte oder alle |
| `--limit` | maximale Anzahl |
| `--provider` | AI-Anbieter |
| `--model` | Modell |
| `--resume` | Sitzung fortsetzen |
| `--json` | Abschlussbericht als JSON |

## `library`

Vollständige Bibliotheksworkflows.

```bash
plex-enhancer library plan --library "Music"
plex-enhancer library review --library "Music"
plex-enhancer library resume --library "Music"
plex-enhancer library apply --library "Music"
plex-enhancer library report --library "Music" --export-json
```

## `cache`

Lokalen Wissenscache verwalten.

```bash
plex-enhancer cache stats
plex-enhancer cache list
plex-enhancer cache clear
```

`clear` löscht den lokalen Cache. Danach müssen Providerdaten neu abgerufen werden.

## `match`

Sucht den passenden MusicBrainz Release Group Match.

```bash
plex-enhancer match --artist "Jennifer Rush" --album "Credo"
plex-enhancer match --artist "Jennifer Rush" --album "Credo" --json
```

Nützlich bei falschen oder fehlenden MusicBrainz-Treffern.

## `probe write`

Prüft Plex-Schreibfähigkeit.

```bash
plex-enhancer probe write --artist "Jennifer Rush" --album "Credo"
plex-enhancer probe write --artist "Jennifer Rush" --album "Credo" --execute
```

Ohne `--execute` wird nicht geschrieben. Mit `--execute` wird ein temporärer Testwert geschrieben und wiederhergestellt.

## `inspect`

Zeigt rohe Plex-Objekte und Attribute.

```bash
plex-enhancer inspect library --name "Music"
plex-enhancer inspect artist --name "Jennifer Rush"
plex-enhancer inspect album --name "Credo"
plex-enhancer inspect track --name "Credo"
```

Optionen:

- `--id`
- `--name`
- `--json`
- `--save`

## `capabilities`

Analysiert, welche Plex-Metadaten verfügbar und schreibbar wirken.

```bash
plex-enhancer capabilities
```

Export:

```text
exports/capabilities.json
```

## `benchmark`

Misst Lese- und Cache-Performance.

```bash
plex-enhancer benchmark --library "Music"
plex-enhancer benchmark --library "Music" --json
```

Zeigt:

- gescannte Alben
- Durchsatz
- Speicherverbrauch
- Cache-Zustand
- Empfehlungen

