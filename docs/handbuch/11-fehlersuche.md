# 11. Fehlersuche

Dieses Kapitel ist nach Symptomen geordnet.

## 11.1 Keine Verbindung zu Plex

Symptome:

- `Unable to connect to Plex`
- Doctor meldet Plex-Fehler

Ursachen:

- Server läuft nicht
- URL falsch
- Firewall blockiert
- Token falsch

Lösung:

```bash
plex-enhancer login
plex-enhancer doctor
```

## 11.2 Authentifizierung fehlgeschlagen

Prüfen Sie Plex Token und Konto. Erzeugen Sie bei Bedarf ein neues Token.

## 11.3 Album nicht gefunden

Ursachen:

- Titel anders geschrieben
- Künstlername anders geschrieben
- Album liegt nicht in Musikbibliothek

Hilfen:

```bash
plex-enhancer scan albums --export-json
plex-enhancer inspect album --name "Credo"
```

## 11.4 MusicBrainz nicht verfügbar

Nutzen Sie:

```bash
plex-enhancer match --artist "Jennifer Rush" --album "Credo"
```

Wenn kein Match gefunden wird, prüfen Sie Schreibweise und Jahr.

## 11.5 Wikipedia nicht verfügbar

Das ist nicht immer kritisch. Manche Alben oder Künstler haben keinen passenden Artikel.

## 11.6 OpenAI Timeout

Lösungen:

- später erneut versuchen
- Timeout erhöhen
- Netzwerk prüfen

```bash
export PLEX_ENHANCER_AI__TIMEOUT_SECONDS=60
```

## 11.7 Rate Limits

Reduzieren Sie parallele Worker:

```bash
export PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS=2
```

## 11.8 Providerfehler

Optionale Provider können ausfallen. Prüfen Sie Zugangsdaten und Cache.

## 11.9 Cache-Probleme

```bash
plex-enhancer cache stats
plex-enhancer cache clear
```

## 11.10 Review fehlgeschlagen

Ursachen:

- Text zu kurz
- falsche Sprache
- Markdown
- Bullet-Liste
- offene Template- oder Testtexte

Lösung:

- im Review `E` wählen
- Prompt und Quellen prüfen

## 11.11 Apply fehlgeschlagen

Prüfen Sie:

- Backup vorhanden?
- Write successful?
- Verification passed?
- Audit stored?

Die Ausgabe des Apply-Workflows zeigt diese Punkte als Tabelle.

## 11.12 Konfigurationsfehler

Nutzen Sie:

```bash
plex-enhancer doctor
```

## 11.13 API Key fehlt

Setzen Sie:

```bash
export OPENAI_API_KEY="sk-..."
```

## 11.14 Netzwerkprobleme

Prüfen:

- Internetverbindung
- DNS
- Proxy
- Firewall
- Providerstatus

