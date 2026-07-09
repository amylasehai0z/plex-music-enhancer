# Developer Mode

Der Developer Mode richtet sich an Entwickler und Power-User, die Prompt-,
Review- und QA-Ergebnisse nachvollziehen möchten. Er führt keine AI-Anfragen
erneut aus und verändert keine Plex-Daten.

Alle Befehle lesen ausschließlich vorhandene Debug-Dateien:

- `/tmp/openai_prompt.txt`
- `/tmp/openai_prompt_meta.json`
- `/tmp/plex_review.log`

## Prompt anzeigen

```bash
plex-enhancer debug prompt --stats
```

Optionen:

- `--copy` kopiert den Prompt in die Zwischenablage, wenn ein unterstütztes
  Clipboard-Tool verfügbar ist.
- `--save DATEI` speichert den Prompt.
- `--stats` zeigt Zeichen, Wörter, geschätzte Tokens, Budget und Prompt-Version.
- `--json` gibt den vollständigen Prompt-Debug-Datensatz als JSON aus.

## Prompt-Metadaten anzeigen

```bash
plex-enhancer debug meta
```

Der Befehl zeigt Provider, Modell, Ziel, Prompt-Version, Wortgrenzen,
Promptgröße, geschätzte Tokens, Budgetdiagnostik, Prompt Decisions und Prompt
Efficiency.

## Review-Log anzeigen

```bash
plex-enhancer debug review --summary
plex-enhancer debug review --section coverage
```

`--summary` zeigt nur QA, Editorial, Verification, Coverage und Prompt Quality.
`--section` zeigt einzelne Bereiche wie `prompt`, `editorial`, `verification`
oder `coverage`.

## Erklärung erzeugen

```bash
plex-enhancer debug explain
```

Dieser Modus fasst zusammen, warum eine Biografie so erzeugt wurde:

- Promptgröße
- genutzte und ausgelassene Quellen
- Prompt Decisions
- Budget-Kürzungen
- Evidence Coverage
- Missed Opportunities
- Prompt Quality
- Prompt Efficiency

## Developer Doctor

```bash
plex-enhancer debug doctor
```

Der Doctor prüft, ob alle Debug-Dateien vorhanden sind, ob Prompt-Meta und
Review-Log lesbar sind und welche Empfehlungen sich aus den vorhandenen Daten
ableiten lassen.

Alle Developer-Mode-Befehle unterstützen `--json`, damit Debugdaten leicht in
GitHub-Issues oder externe Analysen übernommen werden können.
