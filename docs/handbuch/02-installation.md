# 2. Installation

Dieses Kapitel beschreibt die Installation für Personen ohne Programmiererfahrung.

## 2.1 Voraussetzungen

Sie benötigen:

- Python 3.12 oder neuer
- Git
- eine Plex-Musikbibliothek
- Plex-URL und Plex-Token
- optional einen OpenAI API Key

## 2.2 Python installieren

### macOS

```bash
brew install python
python3 --version
```

### Windows

Installieren Sie Python von <https://www.python.org/downloads/>. Aktivieren Sie während der Installation die Option **Add Python to PATH**.

Prüfung:

```powershell
python --version
```

### Linux

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
python3 --version
```

## 2.3 Git installieren

macOS:

```bash
brew install git
```

Windows:

Installieren Sie Git von <https://git-scm.com/download/win>.

Linux:

```bash
sudo apt install git
```

## 2.4 Repository klonen

```bash
git clone https://github.com/amylasehai0z/plex-music-enhancer.git
cd plex-music-enhancer
```

## 2.5 Virtuelle Umgebung erstellen

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

## 2.6 Abhängigkeiten installieren

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev,ai,metadata]"
```

## 2.7 OpenAI API Key

Für echte KI-Erzeugung:

```bash
export PLEX_ENHANCER_AI__PROVIDER=openai
export OPENAI_API_KEY="sk-..."
```

Windows PowerShell:

```powershell
$env:PLEX_ENHANCER_AI__PROVIDER="openai"
$env:OPENAI_API_KEY="sk-..."
```

Ohne OpenAI API Key verwendet das Programm standardmäßig `dummy`. Dieser Anbieter eignet sich nur für Tests.

## 2.8 Plex Token

Sie benötigen:

- Plex Server URL, zum Beispiel `http://localhost:32400`
- Plex Token

> **Warnung:** Ein Plex Token ist ein Geheimnis. Speichern Sie es nicht in öffentlichen Screenshots oder Issues.

## 2.9 Login

```bash
plex-enhancer login
```

Erwartete Eingaben:

```text
Plex server URL:
Plex token:
```

Das Token wird versteckt eingegeben. Bei Erfolg speichert das Programm die Werte in `.env`.

## 2.10 Doctor

```bash
plex-enhancer doctor
```

Doctor prüft Installation, Plex, AI-Konfiguration und Cache.

## 2.11 Verifikation

```bash
plex-enhancer version
```

Ausgabe:

```text
plex-enhancer 1.0.0
```

## 2.12 Häufige Fehler

| Fehler | Lösung |
| --- | --- |
| Python wird nicht gefunden | Python installieren oder `python3` verwenden |
| Aktivierung der Umgebung schlägt fehl | Terminal neu öffnen und Pfad prüfen |
| Plex ist nicht erreichbar | URL, Token, Port und Firewall prüfen |
| OpenAI wird nicht genutzt | `PLEX_ENHANCER_AI__PROVIDER=openai` setzen |

