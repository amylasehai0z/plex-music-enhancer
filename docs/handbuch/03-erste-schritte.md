# 3. Erste Schritte

Dieses Kapitel führt durch einen vollständigen Einsteigerworkflow mit einem Album.

Beispiel:

- Künstler: `Jennifer Rush`
- Album: `Credo`

## 3.1 Vorbereitung

Aktivieren Sie die virtuelle Umgebung:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 3.2 Doctor ausführen

```bash
plex-enhancer doctor
```

Prüfen Sie, ob Plex-Verbindung und AI-Anbieter stimmen. Wenn `dummy` angezeigt wird, wird keine echte KI-Anfrage gesendet.

## 3.3 Login ausführen

Falls Doctor fehlende Plex-Konfiguration meldet:

```bash
plex-enhancer login
```

Geben Sie Plex-URL und Token ein.

## 3.4 Vorschau erzeugen

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
```

Die Ausgabe zeigt:

- generierte Zusammenfassung
- Provider
- Modell
- Prompt-Version
- Warnungen

Für Details:

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --verbose
```

## 3.5 Review starten

```bash
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
```

Sie sehen:

1. aktuellen Plex-Text
2. neuen Text
3. Diff
4. Qualitätsprüfung
5. Stilprüfung
6. Faktenprüfung

## 3.6 Entscheidung treffen

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

| Auswahl | Wirkung |
| --- | --- |
| `A` | sicher anwenden |
| `E` | Text bearbeiten |
| `S` | überspringen |
| `Q` | abbrechen |

## 3.7 Apply ausführen

Direkt:

```bash
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
```

Apply erstellt ein Backup, schreibt den Text, lädt das Album neu und prüft den gespeicherten Wert.

## 3.8 Ergebnis prüfen

Nach Apply können Sie das Album in Plex öffnen. Zusätzlich liegen Audit- und Backup-Dateien unter:

```text
exports/backups/
exports/audit/
```

## 3.9 Häufige Entscheidungen

| Situation | Empfehlung |
| --- | --- |
| Text ist gut | Apply |
| Text ist fast gut | Edit |
| Quellen wirken falsch | Skip und mit `match` prüfen |
| Sprache ist falsch | `--translate` nutzen |
| Text klingt holprig | `--improve` nutzen |

