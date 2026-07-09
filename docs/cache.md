# Cache

Plex Music Enhancer verwendet lokale Caches, damit wiederholte Läufe schneller und zuverlässiger sind.

## Was wird gecacht?

| Bereich | Beispiele |
| --- | --- |
| MusicBrainz | Künstler- und Album-Metadaten, Matches |
| Wikipedia | Artikelzusammenfassungen |
| Discogs | Releases, Credits, Künstlerdaten |
| Last.fm | Biografien, Tags, Album-Wikis |
| Knowledge Cache | normalisierte Provider-Ergebnisse |

## Warum gibt es einen Cache?

Der Cache:

- reduziert Netzwerkanfragen
- beschleunigt große Bibliotheken
- respektiert Provider-Rate-Limits
- macht wiederholte Reviews konsistenter
- erlaubt inkrementelle Verarbeitung

## Speicherort

```text
~/.plex-enhancer/cache/
```

Projektbezogene Exportdateien liegen dagegen unter:

```text
exports/
```

## Lebensdauer

Standard:

```text
30 Tage
```

Abgelaufene Einträge werden ignoriert und bei Bedarf neu geladen.

## Cache-Status anzeigen

```bash
plex-enhancer cache stats
```

Zeigt:

- Gesamtzahl
- frische Einträge
- abgelaufene Einträge
- Verteilung nach Quelle

## Cache-Einträge auflisten

```bash
plex-enhancer cache list
```

## Cache löschen

```bash
plex-enhancer cache clear
```

> **Warnung:** Danach müssen Providerdaten neu geladen werden. Der nächste Lauf kann deutlich länger dauern.

## Performance

Kalter Cache:

- viele Netzwerkanfragen
- langsamer
- stärker von Provider-Limits abhängig

Warmer Cache:

- weniger Netzwerkanfragen
- schneller
- ideal für wiederholte Library-Läufe

## Cache und Prompt-Versionen

Einige Cache- und Verarbeitungsdaten speichern Schema-, Provider- oder Prompt-Versionen. Nach Upgrades können Einträge automatisch als veraltet gelten.

## Typische Probleme

| Symptom | Lösung |
| --- | --- |
| Alte Daten erscheinen | Cache löschen oder Ablauf abwarten |
| Lauf ist langsam | Cache mit `cache stats` prüfen |
| Provider liefert neue Daten nicht | passenden Cache löschen |
| Sehr große Bibliothek dauert lange | Warmcache aufbauen und inkrementell arbeiten |

