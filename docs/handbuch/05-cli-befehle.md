# 5. CLI-Befehle

Dieses Kapitel beschreibt alle öffentlichen Befehle. Die tatsächliche Befehlsliste kann mit folgendem Befehl angezeigt werden:

```bash
plex-enhancer --help
```

## 5.1 Globale Optionen

| Option | Bedeutung |
| --- | --- |
| `--log-level TEXT` | Logging-Level, Standard `INFO` |
| `--help` | Hilfe anzeigen |

## 5.2 `version`

Zweck: installierte Version anzeigen.

```bash
plex-enhancer version
```

Typische Ausgabe:

```text
plex-enhancer 1.0.0
```

## 5.3 `doctor`

Zweck: Installation und Konfiguration prüfen.

```bash
plex-enhancer doctor
```

Mögliche Fehler:

- fehlende Plex-URL
- fehlendes Token
- OpenAI Key fehlt
- Plex nicht erreichbar

Best Practice: vor jeder größeren Sitzung ausführen.

## 5.4 `login`

Zweck: Plex-Zugangsdaten lokal speichern.

```bash
plex-enhancer login
```

Eingaben:

- Plex Server URL
- Plex Token

## 5.5 `audit`

Zweck: vorhandene Metadatenqualität prüfen.

```bash
plex-enhancer audit
plex-enhancer audit --export-json
```

Export:

```text
exports/audit.json
```

## 5.6 `plan`

Zweck: notwendige Aktionen für Alben planen.

```bash
plex-enhancer plan --library "Music"
plex-enhancer plan --library "Music" --json
```

Aktionen: `CREATE`, `TRANSLATE`, `IMPROVE`, `REVIEW`, `SKIP`.

## 5.7 `benchmark`

Zweck: Performance einer Bibliothek prüfen.

```bash
plex-enhancer benchmark --library "Music"
plex-enhancer benchmark --library "Music" --json
```

## 5.8 `capabilities`

Zweck: Plex-Metadatenfähigkeiten analysieren.

```bash
plex-enhancer capabilities
```

Export:

```text
exports/capabilities.json
```

## 5.9 `match`

Zweck: MusicBrainz Release Group finden.

```bash
plex-enhancer match --artist "Jennifer Rush" --album "Credo"
plex-enhancer match --artist "Jennifer Rush" --album "Credo" --json
```

## 5.10 `scan`

Zweck: Plex-Musikbibliothek lesen.

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

## 5.11 `inspect`

Zweck: Plex-Objekte detailliert untersuchen.

```bash
plex-enhancer inspect library --name "Music"
plex-enhancer inspect artist --name "Jennifer Rush"
plex-enhancer inspect album --name "Credo"
plex-enhancer inspect track --name "Titel"
```

Optionen:

| Option | Bedeutung |
| --- | --- |
| `--id` | Rating Key oder ID |
| `--name` | Name/Titel |
| `--json` | JSON ausgeben |
| `--save` | JSON speichern |

## 5.12 `probe write`

Zweck: Schreibfähigkeit prüfen.

```bash
plex-enhancer probe write --artist "Jennifer Rush" --album "Credo"
plex-enhancer probe write --artist "Jennifer Rush" --album "Credo" --execute
```

Ohne `--execute` wird nicht geschrieben.

## 5.13 `metadata album`

Zweck: normalisierte Album-Metadaten erzeugen.

```bash
plex-enhancer metadata album --artist "Jennifer Rush" --album "Credo"
plex-enhancer metadata album --artist "Jennifer Rush" --album "Credo" --json
plex-enhancer metadata album --artist "Jennifer Rush" --album "Credo" --save
```

## 5.14 `context album`

Zweck: vollständigen AlbumContext erzeugen.

```bash
plex-enhancer context album --artist "Jennifer Rush" --album "Credo"
plex-enhancer context album --artist "Jennifer Rush" --album "Credo" --json
plex-enhancer context album --artist "Jennifer Rush" --album "Credo" --save
```

## 5.15 `preview`

Zweck: Textvorschau erzeugen.

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
```

Optionen:

| Option | Bedeutung |
| --- | --- |
| `--provider` | AI-Anbieter überschreiben |
| `--model` | Modell überschreiben |
| `--json` | JSON ausgeben |
| `--save` | Vorschau speichern |
| `--verbose` | Details anzeigen |
| `--translate` | vorhandenen Text übersetzen |
| `--improve` | deutschen Text verbessern |

## 5.16 `preview artist`

```bash
plex-enhancer preview artist --artist "Jennifer Rush"
plex-enhancer preview artist --artist "Jennifer Rush" --json
plex-enhancer preview artist --artist "Jennifer Rush" --verbose
plex-enhancer preview artist --artist "Jennifer Rush" --save
```

`--verbose` zeigt die vollständige Künstlerdiagnose mit Plex-Biografie, MusicBrainz,
Wikipedia, Discogs, Last.fm, Faktenprüfung, Stilbewertung, Qualitätsanalyse und Prompt-Daten.
`--save` speichert die Vorschau unter `exports/previews/artists/`.

Die Diagnose unterscheidet `available`, `missing` und `unknown`. Karrierejahre werden nicht aus
Geburtsdaten abgeleitet. Discogs wird nur angezeigt, wenn es zusätzliche Informationen liefert;
andernfalls steht dort `No additional artist information available.`.
Außerdem zeigt `--verbose` das Prompt-Budget, die ursprüngliche und gekürzte Promptgröße sowie die
Beiträge der einzelnen Quellen.

## 5.17 `review album`

```bash
plex-enhancer review album --artist "Jennifer Rush" --album "Credo"
```

Optionen:

- `--provider`
- `--model`
- `--json`
- `--translate`
- `--improve`

Die ältere Form `plex-enhancer review --artist ... --album ...` bleibt weiterhin gültig.

## 5.18 `review artist`

```bash
plex-enhancer review artist --artist "Jennifer Rush"
```

## 5.19 `apply`

```bash
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
plex-enhancer apply --artist "Jennifer Rush" --album "Credo" --json
```

Optionen:

- `--provider`
- `--model`
- `--json`
- `--translate`
- `--improve`
- `--force`

## 5.20 `apply artist`

```bash
plex-enhancer apply artist --artist "Jennifer Rush"
```

## 5.21 `batch review`

```bash
plex-enhancer batch review --library "Music" --missing-only --limit 25
plex-enhancer batch review --library "Music" --resume
```

## 5.22 `library`

```bash
plex-enhancer library plan --library "Music"
plex-enhancer library review --library "Music"
plex-enhancer library resume --library "Music"
plex-enhancer library apply --library "Music"
plex-enhancer library report --library "Music" --export-json
```

## 5.23 `cache`

```bash
plex-enhancer cache stats
plex-enhancer cache list
plex-enhancer cache clear
```

## 5.24 Fehlerbehebung bei Befehlen

| Symptom | Lösung |
| --- | --- |
| Befehl unbekannt | `plex-enhancer --help` prüfen |
| Option unbekannt | `plex-enhancer <befehl> --help` prüfen |
| Plex-Konfiguration fehlt | `plex-enhancer login` |
| Album fehlt | Schreibweise und Bibliothek prüfen |
| Apply blockiert | Review-Qualität prüfen |
