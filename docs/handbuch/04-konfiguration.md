# 4. Konfiguration

Plex Music Enhancer nutzt Umgebungsvariablen und eine lokale `.env` Datei. Alle projektbezogenen Variablen beginnen mit `PLEX_ENHANCER_`.

## 4.1 Konfigurationsdateien

Die Datei `.env` liegt im Projektordner. Sie wird durch `plex-enhancer login` angelegt oder aktualisiert.

Beispiel:

```text
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=...
PLEX_ENHANCER_AI__PROVIDER=openai
```

## 4.2 Umgebungsvariablen

Direkt gesetzte Umgebungsvariablen haben Vorrang vor `.env`.

macOS/Linux:

```bash
export PLEX_ENHANCER_AI__PROVIDER=openai
```

Windows PowerShell:

```powershell
$env:PLEX_ENHANCER_AI__PROVIDER="openai"
```

## 4.3 Plex-Konfiguration

| Variable | Bedeutung |
| --- | --- |
| `PLEX_ENHANCER_PLEX_URL` | URL des Plex Servers |
| `PLEX_ENHANCER_PLEX_TOKEN` | Plex Token |
| `PLEX_ENHANCER_REQUEST_TIMEOUT_SECONDS` | Timeout für Diagnosen |

## 4.4 Provider-Auswahl

Metadatenanbieter:

- MusicBrainz
- Wikipedia
- Discogs
- Last.fm

Optionale Zugangsdaten:

```text
PLEX_ENHANCER_DISCOGS__TOKEN
PLEX_ENHANCER_LASTFM__API_KEY
```

## 4.5 Modell-Auswahl

```text
PLEX_ENHANCER_AI__PROVIDER=openai
PLEX_ENHANCER_AI__MODEL=gpt-5.5
OPENAI_API_KEY=...
```

Pro Befehl kann das Modell überschrieben werden:

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --model "gpt-5.5"
```

## 4.6 Prompt-Versionen

Prompts liegen unter:

```text
prompts/
```

Jede generierte Zusammenfassung speichert:

- Prompt-Name
- Prompt-Version
- Modell
- Anbieter

Das hilft bei Nachvollziehbarkeit und späterer Regeneration.

## 4.7 Logging

Global:

```bash
plex-enhancer --log-level DEBUG doctor
```

Standard:

```text
INFO
```

Nutzen Sie `DEBUG` nur zur Fehlersuche.

## 4.8 Cache

Standardort:

```text
~/.plex-enhancer/cache/
```

Status:

```bash
plex-enhancer cache stats
```

Löschen:

```bash
plex-enhancer cache clear
```

## 4.9 Exportordner

```text
exports/
    audit/
    backups/
    context/
    inspect/
    library/
    metadata/
    previews/
```

Diese Dateien sind hilfreich für Diagnose, Backups und Nachvollziehbarkeit.

## 4.10 Secrets

Geheime Werte:

- Plex Token
- OpenAI API Key
- Discogs Token
- Last.fm API Key

> **Warnung:** Secrets nicht in Git committen, nicht in Screenshots zeigen und nicht in Issues posten.

## 4.11 Best Practices

- `login` für Plex-Zugangsdaten verwenden.
- OpenAI API Key als Umgebungsvariable setzen.
- Cache nicht unnötig löschen.
- Bei großen Bibliotheken zuerst `benchmark` ausführen.
- Vor Apply immer Review-Ausgabe prüfen.

