# Installation

Diese Anleitung führt Schritt für Schritt durch die Installation von Plex Music Enhancer. Sie setzt keine Programmiererfahrung voraus.

## Voraussetzungen

Sie benötigen:

- einen Plex Media Server mit Musikbibliothek
- Python 3.12 oder neuer
- Git
- Zugriff auf ein Terminal
- optional einen OpenAI API Key

## 1. Python installieren

### macOS

Empfohlen ist die Installation über Homebrew:

```bash
brew install python
python3 --version
```

Die Ausgabe sollte mindestens `Python 3.12` anzeigen.

### Windows

1. Öffnen Sie <https://www.python.org/downloads/>.
2. Laden Sie Python 3.12 oder neuer herunter.
3. Aktivieren Sie während der Installation **Add Python to PATH**.
4. Prüfen Sie die Installation:

```powershell
python --version
```

### Linux

Unter Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
python3 --version
```

> **Tipp:** Wenn Ihre Distribution nur ältere Python-Versionen liefert, nutzen Sie `pyenv` oder die Pakete Ihrer Distribution für Python 3.12+.

## 2. Git installieren

macOS:

```bash
brew install git
git --version
```

Windows:

Laden Sie Git von <https://git-scm.com/download/win> herunter und installieren Sie es mit den Standardoptionen.

Linux:

```bash
sudo apt install git
git --version
```

## 3. Repository klonen

```bash
git clone https://github.com/amylasehai0z/plex-music-enhancer.git
cd plex-music-enhancer
```

Wenn Sie den Quellcode bereits lokal haben, wechseln Sie einfach in den Projektordner.

## 4. Virtuelle Umgebung erstellen

Eine virtuelle Umgebung hält die Python-Abhängigkeiten dieses Projekts getrennt vom restlichen System.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Wenn die Aktivierung funktioniert, sehen Sie meist `(.venv)` am Anfang der Terminalzeile.

## 5. Abhängigkeiten installieren

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev,ai,metadata]"
```

Erwartete Ausgabe:

```text
Successfully installed ...
```

## 6. Plex Token vorbereiten

Plex Music Enhancer benötigt eine Plex-URL und ein Token.

Typische Plex-URL:

```text
http://localhost:32400
```

Wenn Plex auf einem anderen Gerät läuft, verwenden Sie dessen IP-Adresse:

```text
http://192.168.1.20:32400
```

Ein Plex Token erhalten Sie über Plex Web, indem Sie eine XML-Ansicht eines Mediums öffnen und den Parameter `X-Plex-Token` aus der URL kopieren.

> **Warnung:** Behandeln Sie das Plex Token wie ein Passwort. Teilen Sie es nicht öffentlich.

## 7. OpenAI API Key vorbereiten

Für echte KI-Erzeugung setzen Sie:

macOS/Linux:

```bash
export OPENAI_API_KEY="sk-..."
export PLEX_ENHANCER_AI__PROVIDER="openai"
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:PLEX_ENHANCER_AI__PROVIDER="openai"
```

Ohne OpenAI API Key kann der lokale `dummy`-Anbieter verwendet werden. Er ist für Tests gedacht und ruft kein Netzwerk auf.

## 8. Login ausführen

```bash
plex-enhancer login
```

Das Programm fragt:

```text
Plex server URL:
Plex token:
```

Das Token wird versteckt eingegeben. Bei Erfolg wird eine lokale `.env` Datei aktualisiert.

Erwartete Ausgabe:

```text
Plex login saved successfully.
```

Danach startet automatisch `doctor`.

## 9. Installation prüfen

```bash
plex-enhancer version
plex-enhancer doctor
```

Erwartete Version:

```text
plex-enhancer 1.0.0
```

## Häufige Installationsprobleme

| Problem | Lösung |
| --- | --- |
| `python: command not found` | Python installieren oder `python3` verwenden |
| `pip` fehlt | `python -m ensurepip` oder Python neu installieren |
| Aktivierung unter Windows blockiert | PowerShell als Benutzer öffnen und Ausführungsrichtlinie prüfen |
| Plex nicht erreichbar | URL, Port und Firewall prüfen |
| OpenAI Fehler | API Key und Provider-Konfiguration prüfen |

## Nächster Schritt

Weiter mit [Erste Schritte](getting-started.md).

