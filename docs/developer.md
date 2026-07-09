# Entwicklerhandbuch

Diese Seite richtet sich an Personen, die Plex Music Enhancer erweitern oder warten möchten.

## Entwicklungsumgebung

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev,ai,metadata]"
pre-commit install
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".[dev,ai,metadata]"
```

## Wichtige Befehle

```bash
black .
ruff check .
pytest
```

Mit Makefile:

```bash
make format
make lint
make test
make validate
```

## Provider hinzufügen

1. Neues Modul unter `src/plex_music_enhancer/providers/` erstellen.
2. Typed Context-Modelle ergänzen, falls nötig.
3. Provider lesend implementieren.
4. Fehler isolieren und leere Kontextobjekte zurückgeben.
5. Cache nutzen.
6. Pipeline integrieren.
7. Tests mit gemockten Antworten schreiben.
8. Dokumentation aktualisieren.

Provider dürfen keine Plex-Metadaten verändern.

## Command hinzufügen

1. Fachlogik als Service implementieren.
2. CLI nur für Eingabe, Ausgabe und Exit-Code verwenden.
3. JSON-Ausgabe anbieten, wenn strukturierte Daten entstehen.
4. Fehlertexte ohne Secrets ausgeben.
5. Tests für Erfolg und Fehlerfälle schreiben.
6. `docs/commands.md` aktualisieren.

## Prompt hinzufügen

1. Markdown-Datei unter `prompts/` anlegen.
2. Platzhalter in `PromptRegistry` unterstützen.
3. Prompt-Version setzen.
4. Rendering-Tests schreiben.
5. Dokumentation aktualisieren.

## Tests schreiben

Regeln:

- keine echten Netzwerkaufrufe
- keine echten Plex-Schreibzugriffe
- temporäre Pfade mit `tmp_path`
- Secrets nicht in Assertions ausgeben
- klare Testnamen

Beispiel:

```bash
pytest tests/test_providers.py
```

## Qualitätschecks

Vor jedem Release:

```bash
black .
ruff check .
pytest
```

Optional:

```bash
pytest --cov
```

## Versionierung

Die kanonische Version steht in:

```text
src/plex_music_enhancer/constants.py
```

`pyproject.toml` liest die Version dynamisch über Hatchling.

## Release Workflow

1. Version erhöhen.
2. Changelog aktualisieren.
3. Dokumentation prüfen.
4. Tests und Lint ausführen.
5. Paket bauen.
6. Git Tag erstellen.
7. GitHub Release veröffentlichen.
8. Optional PyPI Release durchführen.

Details stehen in:

```text
RELEASE.md
```

## Sicherheitsregeln

- Plex-Schreibzugriffe nur über Apply oder expliziten Probe.
- Vor Schreibzugriffen Backup erzeugen.
- Nach Schreibzugriffen reloaden und verifizieren.
- Providerfehler dürfen Workflows nicht unnötig abbrechen.
- Keine Tokens oder API Keys loggen.
- Generated Text muss reviewbar bleiben.

