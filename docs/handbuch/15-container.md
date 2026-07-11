# 15. Container, Portainer und Synology

Plex Music Enhancer kann als vollständig containerisierte Anwendung betrieben
werden. Der Container startet die bestehende Weboberfläche über:

```bash
plex-enhancer serve --host 0.0.0.0
```

Der interne Port ist `8080`. Auf Synology kann beispielsweise Host-Port `1008`
auf Container-Port `8080` gemappt werden.

## 15.1 Docker Image

Das Image wird über GitHub Container Registry veröffentlicht:

```text
ghcr.io/amylasehai0z/plex-music-enhancer
```

GitHub Actions erzeugt Tags für `latest`, `main`, optional `develop` und
Git-Versionstags.

Veröffentlichte Images werden für diese Plattformen gebaut:

- `linux/amd64`
- `linux/arm64`

Damit läuft dasselbe Image auf Intel-/AMD-Systemen und auf ARM-basierten
Synology-Systemen.

Wichtige Tags:

| Tag | Zweck |
| --- | --- |
| `latest` | aktuelles Image des Standard-Branches |
| `main` | aktuelles Image des `main`-Branches |
| `develop` | optionales Integrations-Image |
| `v1.0.0` | unveränderliches Release-Image |

## 15.2 Docker Compose

Das Repository enthält eine produktionsnahe `docker-compose.yml`.
Die Datei kann ohne Anpassungen als Portainer Stack importiert werden.

Wichtige Einstellungen:

| Einstellung | Wert |
| --- | --- |
| Containername | `plex-music-enhancer` |
| Restart Policy | `unless-stopped` |
| Portmapping | `1008:8080` |
| Healthcheck | `/api/v1/system/health` |

Start:

```bash
docker compose up -d
```

Lokale Docker-Validierung:

```bash
docker build -t plex-music-enhancer:local .
docker compose config
docker run --rm plex-music-enhancer:local plex-enhancer --help
docker run --rm plex-music-enhancer:local plex-enhancer serve --help
docker compose up -d
until curl --fail --silent http://127.0.0.1:1008/api/v1/system/health; do sleep 1; done
docker compose down
```

Der Healthcheck verwendet einen bestehenden REST-Endpunkt. Es ist keine
zusätzliche API erforderlich.

## 15.3 Volumes

| Containerpfad | Zweck |
| --- | --- |
| `/config` | Konfiguration und optionale `.env` |
| `/cache` | Provider- und Knowledge-Cache |
| `/config/exports` | Apply-Backups und Audit-Datensätze |
| `/logs` | Prompt- und Review-Debugdateien |
| `/music` | optionaler read-only Musikpfad |

## 15.4 Umgebungsvariablen

| Variable | Zweck |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API-Key |
| `PLEX_URL` | Kurzform für Plex URL |
| `PLEX_TOKEN` | Kurzform für Plex Token |
| `PLEX_ENHANCER_PLEX_URL` | Plex URL |
| `PLEX_ENHANCER_PLEX_TOKEN` | Plex Token |
| `PLEX_ENHANCER_CONFIG` | Konfigurationsordner oder `.env`-Datei, Standard `/config` |
| `PLEX_ENHANCER_CACHE` | Cachepfad, Standard `/cache` |
| `PLEX_ENHANCER_EXPORTS` | persistenter Exportpfad für Backups und Audits, Standard `/config/exports` |
| `PLEX_ENHANCER_LOG_LEVEL` | Log-Level |
| `PLEX_ENHANCER_WEB__PORT` | interner Webport, Standard `8080` |
| `PUID` | Laufzeit-User-ID für beschreibbare Volumes, Standard `10001` |
| `PGID` | Laufzeit-Gruppen-ID für beschreibbare Volumes, Standard `10001` |

Secrets gehören nicht ins Image. Verwenden Sie Container-Environment oder
`/config/.env`.

## 15.5 Portainer

Portainer ist die empfohlene Verwaltungsoberfläche für den Docker-Betrieb von
Plex Music Enhancer. Aktualisierungen erfolgen bewusst manuell: Sie entscheiden,
wann ein neues Image aus GHCR übernommen und der Container neu gestartet wird.
Automatische Container-Updates werden nicht empfohlen.

Der offizielle Ablauf lautet:

```text
Git Push
↓
GitHub Actions
↓
Tests
↓
Docker Image Build
↓
Push nach GHCR
↓
Portainer
↓
Pull des neuen Images
↓
Container neu starten
```

### Deployment als Stack

1. Portainer öffnen.
2. **Stacks** auswählen.
3. Einen Stack mit dem Namen `plex-music-enhancer` anlegen.
4. Die `docker-compose.yml` aus dem Repository einfügen oder hochladen.
5. Environment-Variablen in Portainer setzen oder eine Env-Datei verwenden.
6. Stack deployen.
7. Weboberfläche über `http://<host>:1008/` öffnen.

### Deployment als einzelner Container

1. In Portainer **Containers** öffnen.
2. Image `ghcr.io/amylasehai0z/plex-music-enhancer:latest` auswählen.
3. Container-Port `8080` setzen.
4. Host-Port `1008` auf Container-Port `8080` mappen.
5. Volumes für `/config`, `/cache`, `/config/exports` und `/logs` einhängen.
6. Environment-Variablen setzen.
7. Restart Policy `unless-stopped` verwenden.
8. Container starten und Healthcheck prüfen.

### GHCR-Image

Für aktuelle Releases verwenden Sie:

```text
ghcr.io/amylasehai0z/plex-music-enhancer:latest
```

Für Rollbacks kann stattdessen ein älterer Release-Tag verwendet werden, zum
Beispiel:

```text
ghcr.io/amylasehai0z/plex-music-enhancer:v1.0.1
```

### Volumes

| Containerpfad | Zweck |
| --- | --- |
| `/config` | Konfiguration und optionale `.env` |
| `/cache` | Provider- und Knowledge-Cache |
| `/config/exports` | Apply-Backups und Audit-Datensätze |
| `/logs` | Prompt- und Review-Debugdateien |
| `/music` | optionaler read-only Musikpfad |

### Environment-Variablen

```text
OPENAI_API_KEY=
PLEX_URL=http://plex:32400
PLEX_TOKEN=
PLEX_ENHANCER_WEB__PORT=8080
PLEX_ENHANCER_LOG_LEVEL=INFO
PLEX_ENHANCER_CONFIG=/config
PLEX_ENHANCER_CACHE=/cache
PLEX_ENHANCER_EXPORTS=/config/exports
PUID=10001
PGID=10001
```

### Port-Mapping und Healthcheck

Empfohlenes Port-Mapping:

```text
1008:8080
```

Der Healthcheck verwendet:

```text
http://127.0.0.1:8080/api/v1/system/health
```

### Container aktualisieren

1. Stack oder Container in Portainer öffnen.
2. Neues Image aus GHCR pullen.
3. Container neu erstellen oder neu starten.
4. Healthcheck prüfen.
5. Weboberfläche öffnen und Version kontrollieren.

### Rollback, Logs und Neustart

Für ein Rollback wird in Portainer ein älterer GHCR-Tag gesetzt und der Stack
oder Container erneut deployt. Logs sind in Portainer direkt auf der
Container-Detailseite sichtbar. Der Container kann dort auch manuell neu
gestartet werden.

## 15.6 Synology Container Manager

1. Container Manager öffnen.
2. Image `ghcr.io/amylasehai0z/plex-music-enhancer:latest` verwenden oder das
   Compose-Projekt importieren.
3. Port `1008` auf `8080` mappen.
4. `/config`, `/cache` und `/logs` als persistente Ordner einhängen.
5. `PLEX_URL`, `PLEX_TOKEN` und `OPENAI_API_KEY` setzen.
6. Neustartregel `unless-stopped` verwenden.
7. Healthcheck prüfen.
8. Weboberfläche öffnen: `http://<synology>:1008/`.

## 15.7 CI/CD

Der GitHub Actions Workflow führt Tests, Linting, Frontend-Build, Paket-Build,
Docker-Smoke-Build, Container-Smoke-Tests, Health-Endpunkt-Smoke-Test,
Multi-Arch-Build, SBOM, Provenance und GHCR-Veröffentlichung aus.

Veröffentlicht werden Container-Images nur für:

- `main`
- `develop`
- Release-Tags wie `v1.0.0`

Pull Requests und Feature-Branches validieren ohne Image-Veröffentlichung. So
bleiben Tests zuverlässig, während Portainer nur bewusst freigegebene Images
übernimmt.
