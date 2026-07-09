# Problembehebung

Diese Seite ist nach Symptomen geordnet.

## Keine Plex-Verbindung

Symptome:

```text
Unable to connect to Plex
Plex connection failed
```

Prüfen:

1. Läuft der Plex Server?
2. Stimmt die URL?
3. Ist Port `32400` erreichbar?
4. Blockiert eine Firewall?
5. Ist das Token gültig?

Befehl:

```bash
plex-enhancer doctor
```

## Authentifizierungsfehler

Mögliche Ursachen:

- falsches Plex Token
- Token abgelaufen
- Token aus falschem Plex-Konto
- URL zeigt auf falschen Server

Lösung:

```bash
plex-enhancer login
```

## OpenAI Fehler

Symptome:

- API Key fehlt
- Provider bleibt `dummy`
- Timeout
- Rate Limit

Prüfen:

```bash
plex-enhancer doctor
```

Setzen:

```bash
export PLEX_ENHANCER_AI__PROVIDER=openai
export OPENAI_API_KEY="sk-..."
```

## Album nicht gefunden

Symptom:

```text
No Plex album named "Credo" was found
```

Prüfen:

- Schreibweise in Plex
- Künstlername exakt
- Album liegt in Musikbibliothek
- mehrere gleichnamige Künstler

Hilfreich:

```bash
plex-enhancer scan albums --export-json
plex-enhancer inspect album --name "Credo"
```

## Falsche Sprache

Wenn ein Text nicht deutsch ist:

```bash
plex-enhancer preview --artist "..." --album "..." --translate
```

Wenn ein deutscher Text holprig ist:

```bash
plex-enhancer preview --artist "..." --album "..." --improve
```

## Kein MusicBrainz Match

MusicBrainz ist wichtig für zuverlässige Album-Identität.

Diagnose:

```bash
plex-enhancer match --artist "Jennifer Rush" --album "Credo"
```

Mögliche Ursachen:

- Albumtitel weicht ab
- Künstlername anders geschrieben
- Release ist nicht als Release Group gepflegt
- Jahr fehlt oder ist falsch

## Wikipedia nicht verfügbar

Wikipedia kann fehlen, wenn:

- kein Artikel existiert
- deutscher Artikel fehlt
- Suchergebnis nicht eindeutig ist
- Netzwerk oder API nicht erreichbar ist

Das ist nicht zwingend kritisch. MusicBrainz und andere Quellen können weiterhin genutzt werden.

## Discogs oder Last.fm fehlen

Prüfen Sie:

```bash
PLEX_ENHANCER_DISCOGS__TOKEN
PLEX_ENHANCER_LASTFM__API_KEY
```

Ohne Zugangsdaten werden diese Anbieter übersprungen.

## Rate Limits

Symptome:

- Anbieter antwortet langsam
- HTTP 429
- wiederholte Timeouts

Lösungen:

- `MAX_WORKERS` reduzieren
- später erneut ausführen
- Cache nicht unnötig löschen

```bash
export PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS=2
```

## Timeouts

Timeouts können bei langsamen Netzwerken auftreten.

Beispiel:

```bash
export PLEX_ENHANCER_AI__TIMEOUT_SECONDS=60
export PLEX_ENHANCER_DISCOGS__TIMEOUT_SECONDS=30
```

## Cache-Probleme

Status:

```bash
plex-enhancer cache stats
```

Löschen:

```bash
plex-enhancer cache clear
```

> **Hinweis:** Nach dem Löschen dauert der nächste Lauf länger.

## Review lehnt Text ab

Gründe:

- Text ist leer
- Text enthält Markdown
- Text enthält Bullet-Listen
- Text enthält Platzhalter
- Text wirkt nicht deutsch
- Text ist zu kurz oder zu lang

Lösung:

- `E` im Review wählen und Text bearbeiten
- `--verbose` nutzen
- Quellen prüfen

## Apply schlägt fehl

Prüfen:

- Backup wurde erstellt?
- Write successful?
- Verification passed?
- Audit stored?

Wenn Plex nach dem Schreiben einen anderen Text zurückliefert, meldet Apply fehlgeschlagene Verifikation.

## Windows-Pfade

Verwenden Sie in PowerShell Anführungszeichen:

```powershell
$env:PLEX_ENHANCER_PERFORMANCE__DATABASE_LOCATION="$HOME\.plex-enhancer\processing.sqlite3"
```

## Unicode-Probleme

Plex Music Enhancer schreibt JSON-Dateien mit UTF-8. Wenn Umlaute falsch angezeigt werden, prüfen Sie den Editor oder die Terminalkodierung.

