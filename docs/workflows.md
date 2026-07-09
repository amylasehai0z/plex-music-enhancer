# Workflows

Diese Seite beschreibt vollständige Arbeitsabläufe für typische Aufgaben.

## Einzelnes Album neu beschreiben

Ziel: Ein fehlender oder schlechter Albumtext soll neu erzeugt werden.

```bash
plex-enhancer doctor
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
```

Im Review wählen Sie:

- `A`, wenn der Text gut ist
- `E`, wenn Sie ihn anpassen möchten
- `S`, wenn dieses Album übersprungen werden soll
- `Q`, wenn Sie abbrechen möchten

Direkter Apply:

```bash
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
```

## Künstlerbiografie erzeugen

```bash
plex-enhancer preview artist --artist "Jennifer Rush"
plex-enhancer review artist --artist "Jennifer Rush"
plex-enhancer apply artist --artist "Jennifer Rush"
```

Der Ablauf entspricht dem Albumworkflow, verwendet aber einen `ArtistContext`.

## Englischen Albumtext übersetzen

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --translate
plex-enhancer review --artist "Jennifer Rush" --album "Credo" --translate
```

Regeln:

- Fakten bleiben erhalten.
- Titel, Namen und Daten werden nicht verändert.
- Nur die Sprache und Lesbarkeit werden verbessert.

## Deutschen Albumtext verbessern

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --improve
plex-enhancer review --artist "Jennifer Rush" --album "Credo" --improve
```

Geeignet für:

- holprige Übersetzungen
- Wiederholungen
- zu kurze Texte
- uneinheitlichen Stil

## Planung für eine Bibliothek

```bash
plex-enhancer plan --library "Music"
```

Die Planung sortiert Alben nach:

| Aktion | Bedeutung |
| --- | --- |
| `CREATE` | kein Text vorhanden |
| `TRANSLATE` | englischer Text vorhanden |
| `IMPROVE` | deutscher Text ist schwach |
| `REVIEW` | unklare Lage, Benutzerentscheidung nötig |
| `SKIP` | Text ist gut genug |

## Batch-Verarbeitung

```bash
plex-enhancer batch review --library "Music" --missing-only --limit 50
```

Nützlich, wenn Sie mehrere Alben nacheinander prüfen möchten.

Fortsetzen:

```bash
plex-enhancer batch review --library "Music" --resume
```

## Library-Modus

Für große Bibliotheken:

```bash
plex-enhancer library plan --library "Music"
plex-enhancer library review --library "Music"
plex-enhancer library apply --library "Music"
plex-enhancer library report --library "Music" --export-json
```

Empfohlene Reihenfolge:

1. Plan erstellen.
2. Review-Sitzung durchführen.
3. Nur genehmigte Einträge anwenden.
4. Report archivieren.

## Cache vor großen Läufen prüfen

```bash
plex-enhancer cache stats
plex-enhancer benchmark --library "Music"
```

Wenn viele Cache-Einträge abgelaufen sind, dauert der nächste Lauf länger.

## Sicherer Produktionsablauf

```bash
plex-enhancer doctor
plex-enhancer audit --export-json
plex-enhancer library plan --library "Music"
plex-enhancer benchmark --library "Music"
plex-enhancer library review --library "Music"
plex-enhancer library apply --library "Music"
plex-enhancer library report --library "Music" --export-json
```

> **Tipp:** Beginnen Sie bei einer großen Bibliothek mit `--limit 10` oder `--limit 25`, bis Konfiguration und Stil passen.

