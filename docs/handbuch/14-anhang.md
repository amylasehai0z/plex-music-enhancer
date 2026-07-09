# 14. Anhang

Der Anhang sammelt Befehlsmuster, Dateipfade und praktische Checklisten.

## 14.1 Wichtige Befehle

```bash
plex-enhancer version
plex-enhancer doctor
plex-enhancer login
plex-enhancer scan
plex-enhancer plan --library "Music"
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
plex-enhancer cache stats
```

## 14.2 Häufige Exportpfade

| Pfad | Inhalt |
| --- | --- |
| `exports/libraries.json` | Bibliotheksstatistik aus `scan --export-json`. |
| `exports/artists.json` | Künstlerexport aus `scan artists --export-json`. |
| `exports/albums.json` | Albumexport aus `scan albums --export-json`. |
| `exports/audit/` | Audit-Datensätze aus Apply- und Analyseabläufen. |
| `exports/backups/` | Sicherungen alter Plex-Zusammenfassungen. |
| `exports/context/` | Gespeicherte Kontextdokumente. |
| `exports/previews/` | Gespeicherte Preview-Dokumente. |
| `exports/jobs/` | Fortschrittsdaten für Resume-fähige Abläufe. |

## 14.3 Konfigurationsbeispiele

Minimale Plex-Konfiguration:

```env
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=IhrPlexToken
```

OpenAI-Konfiguration:

```env
PLEX_ENHANCER_AI__PROVIDER=openai
PLEX_ENHANCER_AI__MODEL=gpt-5.5
OPENAI_API_KEY=IhrOpenAIKey
```

## 14.4 Sicherer Einzelalbum-Ablauf

1. `plex-enhancer doctor`
2. `plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --verbose`
3. `plex-enhancer review --artist "Jennifer Rush" --album "Credo"`
4. Text prüfen und bei Bedarf bearbeiten.
5. `plex-enhancer apply --artist "Jennifer Rush" --album "Credo"`
6. Audit- und Backup-Dateien aufbewahren.

## 14.5 Sicherer Bibliotheksablauf

1. `plex-enhancer library plan --library "Music"`
2. CREATE, TRANSLATE, IMPROVE, REVIEW und SKIP prüfen.
3. Mit kleinem Limit oder Review-Session starten.
4. Regelmäßig Reports erzeugen.
5. Backups nicht löschen, bevor die Ergebnisse geprüft wurden.

## 14.6 Exit-Code-Orientierung

Ein erfolgreicher Befehl beendet sich mit Status 0. Fehlerhafte Konfiguration, Verbindungsprobleme oder nicht erfüllte Voraussetzungen führen zu einem Fehlerstatus und einer erklärenden Meldung.

## 14.7 Empfehlungen für produktive Nutzung

- Beginnen Sie mit wenigen Alben.
- Nutzen Sie `--verbose`, wenn ein Ergebnis unerwartet wirkt.
- Verwenden Sie `--json` oder `--save`, wenn Ergebnisse archiviert werden sollen.
- Löschen Sie Backups erst nach manueller Prüfung.
- Halten Sie Provider-Schlüssel privat.
- Prüfen Sie große Bibliotheken zuerst mit `plan`, nicht direkt mit Apply.

## 14.8 PDF-Erstellung

Das PDF-Skript liegt unter:

```bash
docs/pdf/build.sh
```

Es setzt Pandoc voraus und kombiniert die Kapitel in numerischer Reihenfolge.

