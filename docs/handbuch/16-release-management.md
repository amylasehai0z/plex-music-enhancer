# 16. Release Management

Plex Music Enhancer verwendet einen tag-basierten Release-Prozess. Ein
Versions-Tag reicht aus, um Tests, Paketbau, Container-Build, GHCR-Publish und
GitHub Release auszulösen.

## 16.1 Empfohlener Release-Prozess

```bash
git tag v1.0.0
git push origin v1.0.0
```

Danach läuft automatisch:

```text
Git Tag
↓
GitHub Actions
↓
Tests
↓
Python Wheel
↓
Source Distribution
↓
Docker Smoke Tests
↓
Multi-Arch Docker Image
↓
GHCR
↓
GitHub Release
↓
Release-Artefakte
```

## 16.2 GitHub Releases

Für Tags wie `v1.0.0` erstellt oder aktualisiert GitHub Actions automatisch ein
GitHub Release. Der Release-Titel folgt dem Schema:

```text
Plex Music Enhancer v1.0.0
```

Release Notes werden aus GitHub-Daten erzeugt und bei erneutem Workflow-Lauf
aktualisiert.

## 16.3 Release-Artefakte

Jedes Release erhält automatisch:

- Python Wheel (`.whl`)
- Source Distribution (`.tar.gz`)
- Build Report
- Docker Analyse
- Release Readiness Report

Diese Dateien werden zusätzlich als GitHub Actions Artifacts gespeichert.

## 16.4 GHCR und Image Tags

Release-Tags erzeugen passende Images in GitHub Container Registry.

Beispiele:

| Tag | Zweck |
| --- | --- |
| `latest` | aktuelles Image des Standard-Branches |
| `main` | aktuelles Image des `main`-Branches |
| `v1.0.0` | unveränderliches Release-Image |
| `1.0` | SemVer-Minor-Tag |

Die Images werden für `linux/amd64` und `linux/arm64` gebaut. Dadurch sind
Intel-/AMD-Systeme und ARM-basierte Synology-Systeme abgedeckt.

## 16.5 Build Report

Der Build Report dokumentiert technische Eckdaten:

- Git Commit
- Branch oder Tag
- Version
- Python Version
- Docker Version
- Docker Compose Version
- Image ID
- Imagegröße
- Wheel- und Source-Distribution-Größe
- OCI Labels
- Multi-Arch, SBOM und Provenance
- Healthcheck
- Smoke-Test-Ergebnis
- Docker-Compose-Test
- Build-Dauer
- Zeitstempel

## 16.6 Docker Analyse

Die Docker Analyse ergänzt:

- Imagegröße
- Anzahl Layer
- größte Layer
- Cache-Konfiguration
- mögliche Optimierungspotentiale

Sie ist rein diagnostisch und verändert das Image nicht.

## 16.7 Release Readiness Report

Der Release Readiness Report bewertet:

- Packaging
- Docker
- Docker Compose
- GitHub Actions
- GHCR
- Portainer
- Deployment
- Dokumentation

Die Bewertung ist bewusst technisch und soll verbleibende Risiken sichtbar
machen, statt künstlich perfekte Ergebnisse zu melden.

## 16.8 Portainer nach dem Release

Nach einem Release zieht der Anwender das neue GHCR-Image in Portainer manuell
und startet den Container neu. Automatische Container-Updates werden nicht
empfohlen. Für Rollbacks wird ein älterer Release-Tag ausgewählt.
