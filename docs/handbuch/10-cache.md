# 10. Cache

Der Cache speichert Providerdaten lokal.

## 10.1 Zweck

Der Cache reduziert:

- Wartezeit
- Netzwerkanfragen
- Rate-Limit-Probleme
- wiederholte identische Provideraufrufe

## 10.2 Speicherorte

```text
~/.plex-enhancer/cache/
~/.plex-enhancer/processing.sqlite3
```

## 10.3 Lebensdauer

Standard:

```text
30 Tage
```

## 10.4 Cache prüfen

```bash
plex-enhancer cache stats
plex-enhancer cache list
```

## 10.5 Cache löschen

```bash
plex-enhancer cache clear
```

> **Warnung:** Danach dauert der nächste Lauf länger.

## 10.6 Cache neu aufbauen

Führen Sie Preview, Plan oder Library-Workflows erneut aus. Der Cache füllt sich automatisch.

## 10.7 Wann löschen?

Sinnvoll bei:

- veralteten Providerdaten
- beschädigten Cachedateien
- Tests mit neuen Quellen
- unerklärlichen Wiederholungsfehlern

Nicht sinnvoll vor jedem Lauf.

## 10.8 Performance-Beispiele

| Situation | Erwartung |
| --- | --- |
| kalter Cache | langsamer, viele Netzwerkanfragen |
| warmer Cache | schneller, weniger Netzwerkanfragen |
| große Bibliothek | zuerst Benchmark und Plan verwenden |

