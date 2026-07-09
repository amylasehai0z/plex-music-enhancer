# Erste Schritte

Dieses Tutorial zeigt einen vollständigen Durchlauf mit einem einzelnen Album.

Beispiel:

- Künstler: `Jennifer Rush`
- Album: `Credo`

> **Hinweis:** Sie können jedes Album aus Ihrer Plex-Musikbibliothek verwenden. Die Beispiele nutzen `Jennifer Rush` und `Credo`, damit die Befehle konkret bleiben.

## 1. Umgebung aktivieren

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 2. Version prüfen

```bash
plex-enhancer version
```

Erwartet:

```text
plex-enhancer 1.0.0
```

## 3. Verbindung prüfen

```bash
plex-enhancer doctor
```

`doctor` prüft:

- Python-Version
- Plex-Konfiguration
- Plex-URL
- Verbindung zu Plex
- AI-Anbieter
- Cache-Status
- Prompt-Version

Gute Ausgabe:

```text
Python version ........ OK
Plex configuration .... OK
Plex connection ....... OK
AI provider ........... openai
```

Wenn `AI provider` auf `dummy` steht, erzeugt das Programm nur deterministische Testtexte.

## 4. Login bei Bedarf erneut ausführen

```bash
plex-enhancer login
```

Geben Sie die Plex-URL und das Token ein. Das Token wird nicht angezeigt.

## 5. Vorschau erzeugen

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo"
```

Die Vorschau zeigt zuerst den erzeugten Text und danach wichtige technische Details.

Typische Abschnitte:

```text
GENERATED SUMMARY
Provider
Model
Prompt version
Warnings
```

Mit ausführlichen Details:

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --verbose
```

Dann sehen Sie zusätzlich:

- Plex-Metadaten
- MusicBrainz-Match
- Wikipedia-Status
- Prompt-Variablen
- Fact Verification
- Token-Nutzung

## 6. Review starten

```bash
plex-enhancer review --artist "Jennifer Rush" --album "Credo"
```

Das Review zeigt:

- aktuelle Plex-Zusammenfassung
- generierte Zusammenfassung
- Unified Diff
- Qualitätsprüfung
- Stilprüfung
- Faktenprüfung

Danach fragt das Programm:

```text
[A] Apply  [E] Edit  [S] Skip  [Q] Quit
```

Optionen:

| Auswahl | Bedeutung |
| --- | --- |
| `A` | geprüften Text sicher nach Plex schreiben |
| `E` | Text im Editor bearbeiten |
| `S` | überspringen |
| `Q` | beenden |

## 7. Apply ausführen

Direkt ohne interaktive Review-Schleife:

```bash
plex-enhancer apply --artist "Jennifer Rush" --album "Credo"
```

Das Apply macht:

1. Review-Dokument erzeugen.
2. Qualität prüfen.
3. Backup des aktuellen Plex-Textes speichern.
4. Neue Zusammenfassung schreiben.
5. Album aus Plex neu laden.
6. Ergebnis vergleichen.
7. Audit-Datei speichern.

Erfolgreiche Ausgabe:

```text
Backup created .... yes
Write successful .. yes
Verification passed yes
Audit stored ...... yes
```

## 8. JSON speichern

Vorschau speichern:

```bash
plex-enhancer preview --artist "Jennifer Rush" --album "Credo" --save
plex-enhancer preview artist --artist "Jennifer Rush" --save
```

Datei:

```text
exports/previews/Jennifer-Rush-Credo.json
exports/previews/artists/Artist-Preview-Jennifer-Rush-YYYYMMDD-HHMMSS.json
```

## 9. Was tun bei Fehlern?

| Symptom | Nächster Schritt |
| --- | --- |
| Album nicht gefunden | Schreibweise in Plex prüfen |
| Kein MusicBrainz-Match | `plex-enhancer match` ausprobieren |
| DummyProvider wird verwendet | `PLEX_ENHANCER_AI__PROVIDER=openai` setzen |
| Review lehnt Text ab | Text bearbeiten oder Prompt/Quellen prüfen |
| Apply schlägt fehl | Backup und Audit-Datei prüfen |

Weiterführend:

- [Befehlsreferenz](commands.md)
- [Review-System](review-system.md)
- [Problembehebung](troubleshooting.md)
