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

Die Ausgabedatei hat immer denselben stabilen Pfad:

```text
assets/pdf/Plex-Music-Enhancer-Handbuch.pdf
```

Versionsnummern stehen im Handbuch selbst, aber nicht im Dateinamen.

Das Handbuchlogo wird aus dieser Datei geladen:

```text
assets/logo/plex-music-enhancer-logo.pdf
```

Die SVG-Logo-Datei bleibt für GitHub, README und Web-Darstellung erhalten. Der
PDF-Build nutzt keine SVG-Konvertierung und benötigt kein Inkscape.

## 14.9 Backend-API und REST

Plex Music Enhancer enthält eine interne Backend-API-Schicht unter
`plex_music_enhancer.api`, eine optionale FastAPI-REST-Schicht unter
`plex_music_enhancer.web` und eine erste React-Weboberfläche im
Repository-Verzeichnis `web/`.

Die Schicht definiert:

- versionierte Request- und Response-Modelle für `v1`
- ein zentrales `ReviewDocument`
- Analysemodelle für Prompt, Qualität, Editorial, Verifikation und Debug-Metadaten
- eine gemeinsame Fehlerhierarchie
- interne Service-Adapter wie `ReviewAPIService` und `ApplyAPIService`
- FastAPI-Router für System, Config, Provider, Logs, Review, Preview und Apply

Der REST-Server wird optional installiert und gestartet:

```bash
python -m pip install ".[web]"
plex-enhancer serve
```

Wichtige URLs:

| URL | Inhalt |
| --- | --- |
| `http://127.0.0.1:1008/` | Weboberfläche |
| `http://127.0.0.1:1008/api/v1/docs` | Swagger UI |
| `http://127.0.0.1:1008/api/v1/redoc` | ReDoc |
| `http://127.0.0.1:1008/api/v1/openapi.json` | OpenAPI JSON |
| `/api/v1/system/health` | Health Check |
| `/api/v1/review/artist` | Artist Review |
| `/api/v1/review/album` | Album Review |
| `/api/v1/preview` | Preview |
| `/api/v1/apply` | Apply |

CLI, JSON-Ausgabe und Weboberfläche arbeiten auf denselben Backend-Services. Die
Weboberfläche enthält keine Geschäftslogik und konsumiert ausschließlich die
REST-API.

Geplante Phasen:

1. Architektur und Contracts
2. interne Backend-API
3. FastAPI
4. REST-Endpunkte
5. React-Oberfläche (erste Version umgesetzt)
6. Desktop-App

## 14.10 Developer Mode

Der Developer Mode hilft bei Prompt-Entwicklung, Review-Analyse und
Qualitätsdiagnose. Er führt keine AI-Anfragen erneut aus und liest nur bereits
vorhandene Debug-Dateien.

Wichtige Dateien:

| Datei | Inhalt |
| --- | --- |
| `/tmp/openai_prompt.txt` | letzter an OpenAI gesendeter Prompt |
| `/tmp/openai_prompt_meta.json` | Prompt-Metadaten, Budget und Decisions |
| `/tmp/plex_review.log` | strukturierter Review-Debug-Log |

Befehle:

```bash
plex-enhancer debug prompt --stats
plex-enhancer debug meta
plex-enhancer debug review --summary
plex-enhancer debug review --section coverage
plex-enhancer debug explain
plex-enhancer debug doctor
```

`debug explain` fasst zusammen, welche Quellen genutzt wurden, welche Evidence
entfernt oder gekürzt wurde, wie die Prompt Efficiency aussieht und welche
Missed Opportunities im Ergebnis sichtbar sind.

Alle Developer-Mode-Befehle unterstützen `--json`, damit Debugdaten leicht in
GitHub-Issues übernommen werden können.
