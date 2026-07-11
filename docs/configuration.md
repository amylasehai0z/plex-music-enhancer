# Konfiguration

Plex Music Enhancer wird über Umgebungsvariablen und eine lokale `.env` Datei konfiguriert. Alle projektspezifischen Variablen beginnen mit `PLEX_ENHANCER_`.

## Reihenfolge der Konfiguration

1. Direkt gesetzte Umgebungsvariablen.
2. Lokale `.env` Datei im Projektverzeichnis.
3. Eingebaute Standardwerte.

> **Hinweis:** Während automatisierter Tests wird die lokale `.env` Datei ignoriert, damit Tests nicht von einem Entwicklerrechner abhängen.

## Plex

| Variable | Pflicht | Beispiel | Bedeutung |
| --- | --- | --- | --- |
| `PLEX_ENHANCER_PLEX_URL` | ja | `http://localhost:32400` | Basis-URL des Plex Servers |
| `PLEX_ENHANCER_PLEX_TOKEN` | ja | `xxxxxxxx` | Plex Zugriffstoken |
| `PLEX_ENHANCER_REQUEST_TIMEOUT_SECONDS` | nein | `5` | Timeout für Plex-Diagnosen |

Empfohlen:

```bash
plex-enhancer login
```

Der Login schreibt:

```text
PLEX_ENHANCER_PLEX_URL=<url>
PLEX_ENHANCER_PLEX_TOKEN=<token>
```

in `.env` und erhält andere Einträge.

## AI-Anbieter

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `PLEX_ENHANCER_AI__PROVIDER` | `dummy` | AI-Anbieter |
| `PLEX_ENHANCER_AI__MODEL` | `gpt-5.5` | Modellname |
| `PLEX_ENHANCER_AI__TIMEOUT_SECONDS` | `30` | Timeout für AI-Anfragen |
| `PLEX_ENHANCER_AI__MAX_RETRIES` | `2` | Wiederholungen bei temporären Fehlern |
| `PLEX_ENHANCER_AI__MAX_PROMPT_CHARACTERS` | `20000` | Maximale Promptlänge |
| `AI_PROMPT_MAX_CHARS` | `20000` | Kompatible Kurzform für die maximale Promptlänge |
| `OPENAI_API_KEY` | leer | OpenAI API Key |

Die Promptlänge wird automatisch eingehalten. Wenn ein sehr großer Künstlerkontext das Budget
überschreitet, kürzt der Prompt Budget Manager zuerst niedrig priorisierte Quellen wie bestehende
Plex-Biografien, Last.fm-, Discogs- und Wikipedia-Langtexte. Verifizierte strukturierte Metadaten
bleiben erhalten.

`PLEX_ENHANCER_AI__MAX_PROMPT_CHARACTERS` ist die kanonische Einstellung. `AI_PROMPT_MAX_CHARS`
wird aus Umgebungsvariablen und explizit geladenen `.env` Dateien weiterhin unterstützt, damit
bestehende Setups nicht angepasst werden müssen.

Anbieter:

| Anbieter | Einsatz |
| --- | --- |
| `dummy` | lokaler Testmodus ohne Netzwerk |
| `openai` | echte Texterzeugung mit OpenAI |
| `ollama` | reservierter Name, in v1.0 nicht verfügbar |

Beispiel:

```bash
export PLEX_ENHANCER_AI__PROVIDER=openai
export PLEX_ENHANCER_AI__MODEL=gpt-5.5
export OPENAI_API_KEY="sk-..."
```

## Metadatenanbieter

MusicBrainz und Wikipedia benötigen keine Zugangsdaten.

Optionale Anbieter:

| Variable | Bedeutung |
| --- | --- |
| `PLEX_ENHANCER_DISCOGS__TOKEN` | Discogs Personal Access Token |
| `PLEX_ENHANCER_DISCOGS__TIMEOUT_SECONDS` | Timeout für Discogs |
| `PLEX_ENHANCER_DISCOGS__MAX_RETRIES` | Wiederholungen |
| `PLEX_ENHANCER_DISCOGS__RATE_LIMIT_SECONDS` | Mindestabstand zwischen Anfragen |
| `PLEX_ENHANCER_LASTFM__API_KEY` | Last.fm API Key |
| `PLEX_ENHANCER_LASTFM__TIMEOUT_SECONDS` | Timeout für Last.fm |
| `PLEX_ENHANCER_LASTFM__MAX_RETRIES` | Wiederholungen |
| `PLEX_ENHANCER_LASTFM__RATE_LIMIT_SECONDS` | Mindestabstand zwischen Anfragen |

Fehlen Zugangsdaten, werden diese Anbieter automatisch übersprungen.

## Qualität

| Variable | Beispiel | Bedeutung |
| --- | --- | --- |
| `PLEX_ENHANCER_QUALITY__MINIMUM_QUALITY_SCORE` | `85` | Mindestwert für Apply |

Wenn ein generierter Text darunter liegt, wird Apply blockiert. Einzelne Apply-Befehle können mit `--force` bewusst überschrieben werden.

## Performance

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS` | `4` | parallele Provider-Aufgaben |
| `PLEX_ENHANCER_PERFORMANCE__PROVIDER_TIMEOUT` | `30` | Standard-Provider-Timeout |
| `PLEX_ENHANCER_PERFORMANCE__RETRY_ATTEMPTS` | `3` | Wiederholungen |
| `PLEX_ENHANCER_PERFORMANCE__CACHE_EXPIRATION_DAYS` | `30` | Cache-Lebensdauer |
| `PLEX_ENHANCER_PERFORMANCE__BATCH_SIZE` | `100` | empfohlene Batch-Größe |
| `PLEX_ENHANCER_PERFORMANCE__DATABASE_LOCATION` | `~/.plex-enhancer/processing.sqlite3` | SQLite Statusdatenbank |
| `PLEX_ENHANCER_PERFORMANCE__QUALITY_THRESHOLD` | leer | Schwelle für inkrementelle Verarbeitung |
| `PLEX_ENHANCER_PERFORMANCE__INCREMENTAL_MODE` | `true` | unveränderte Alben überspringen |

## Cache und Exporte

Cache:

```text
~/.plex-enhancer/cache/
```

Verarbeitungsdatenbank:

```text
~/.plex-enhancer/processing.sqlite3
```

Projektbezogene Exporte:

```text
/config/exports/
```

Darin liegen zum Beispiel:

- `/config/exports/previews/`
- `/config/exports/backups/`
- `/config/exports/audit/`
- `/config/exports/library/`
- `/config/exports/context/`

Im Container ist `/config/exports` der Standard, damit Backups und Audit-Daten
nicht vom aktuellen Arbeitsverzeichnis abhängen. Der Pfad kann mit
`PLEX_ENHANCER_EXPORTS` überschrieben werden.

## Prompt-Versionen

Jede Prompt-Vorlage hat eine Version. Die Version wird in Vorschau-, Review- und Audit-Daten gespeichert. Wenn sich Prompts ändern, kann die inkrementelle Verarbeitung erkennen, dass ein neuer Text sinnvoll ist.

## Diagnose

```bash
plex-enhancer doctor
```

`doctor` zeigt sofort, ob Plex, AI-Anbieter, API Key, Cache und Prompt-Version plausibel konfiguriert sind.
