# Docker, GHCR, Portainer and Synology Deployment

Plex Music Enhancer can run as a fully containerized web application. The
container starts the existing CLI command:

```bash
plex-enhancer serve --host 0.0.0.0
```

The internal container port is `8080`. A Synology or local host can map any
external port to it, for example `1008:8080`.

## Image

The published image name is:

```text
ghcr.io/amylasehai0z/plex-music-enhancer
```

Tags are produced by GitHub Actions:

- `latest` for the default branch
- `main` for the default branch
- `develop` for the optional integration branch
- semantic version tags for Git tags such as `v1.0.1`

Images are published for:

- `linux/amd64`
- `linux/arm64`

This supports Intel/AMD hosts as well as ARM-based Synology systems.

Release tags such as `v1.0.1` are immutable deployment candidates and are the
recommended rollback target in Portainer.

## Docker Compose

Start locally:

```bash
docker compose up -d
```

The default compose file maps:

```text
http://127.0.0.1:1008 -> container port 8080
```

Volumes:

| Host path | Container path | Purpose |
| --- | --- | --- |
| `./docker/config` | `/config` | `.env` and persistent configuration |
| `./docker/cache` | `/cache` | provider and knowledge cache |
| `./docker/logs` | `/logs` | prompt and review debug logs |
| `./docker/music` | `/music` | optional read-only music mount |

The compose file can be imported directly as a Portainer Stack. Portainer reads
the same service definition, image name, volume mounts, environment variables,
port mapping and healthcheck.

## Local Docker Validation

Use the same commands locally that the release workflow relies on:

```bash
docker build -t plex-music-enhancer:local .
docker compose config
docker run --rm plex-music-enhancer:local plex-enhancer --help
docker run --rm plex-music-enhancer:local plex-enhancer serve --help
docker compose up -d
until curl --fail --silent http://127.0.0.1:1008/api/v1/system/health; do sleep 1; done
docker compose down
```

The healthcheck uses the existing REST endpoint and does not require a new API.

## Environment

Supported container variables:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API key |
| `PLEX_URL` | short alias for `PLEX_ENHANCER_PLEX_URL` |
| `PLEX_TOKEN` | short alias for `PLEX_ENHANCER_PLEX_TOKEN` |
| `PLEX_ENHANCER_PLEX_URL` | Plex server URL |
| `PLEX_ENHANCER_PLEX_TOKEN` | Plex token |
| `PLEX_ENHANCER_CONFIG` | configuration directory or dotenv file, default `/config` |
| `PLEX_ENHANCER_CACHE` | cache path, default `/cache` |
| `PLEX_ENHANCER_LOG_LEVEL` | logging level |
| `PLEX_ENHANCER_WEB__PORT` | internal web port, default `8080` |

No secrets are built into the image. Use environment variables or `/config/.env`.

## Healthcheck

The container uses the existing API endpoint:

```text
GET /api/v1/system/health
```

No extra business logic is required.

## Portainer

Portainer is the recommended Docker management interface for Plex Music
Enhancer. It keeps updates explicit: the user chooses when a new GHCR image is
pulled and when the container is restarted.

Official workflow:

```text
Git Push
↓
GitHub Actions
↓
Tests
↓
Docker Image Build
↓
Push to GHCR
↓
Portainer
↓
Pull new image
↓
Restart container
```

Automatic container updates are not documented or recommended.

### Deploy as a Stack

1. Open Portainer.
2. Go to **Stacks**.
3. Create a new stack named `plex-music-enhancer`.
4. Paste or upload the repository `docker-compose.yml`.
5. Set environment variables in Portainer or provide an env file.
6. Deploy the stack.
7. Open `http://<host>:1008/`.

### Deploy as a Single Container

1. Open **Containers**.
2. Create a container from `ghcr.io/amylasehai0z/plex-music-enhancer:latest`.
3. Set container port `8080`.
4. Publish host port `1008` to container port `8080`.
5. Mount `/config`, `/cache` and `/logs`.
6. Set environment variables.
7. Enable restart policy `unless-stopped`.
8. Start the container and check the health status.

### Required Portainer Settings

Image:

```text
ghcr.io/amylasehai0z/plex-music-enhancer:latest
```

Volumes:

| Container path | Purpose |
| --- | --- |
| `/config` | configuration and optional `.env` |
| `/cache` | provider cache |
| `/logs` | prompt and review logs |
| `/music` | optional read-only music mount |

Environment:

```text
OPENAI_API_KEY=
PLEX_URL=http://plex:32400
PLEX_TOKEN=
PLEX_ENHANCER_WEB__PORT=8080
PLEX_ENHANCER_LOG_LEVEL=INFO
PLEX_ENHANCER_CONFIG=/config
PLEX_ENHANCER_CACHE=/cache
```

Healthcheck:

```text
http://127.0.0.1:8080/api/v1/system/health
```

### Updating with Portainer

1. Open the stack or container.
2. Pull the latest image from GHCR.
3. Recreate or restart the container.
4. Check the health status.
5. Open the web interface and verify the version.

### Rollback

Use a previous GHCR image tag instead of `latest`, for example a release tag
such as `v1.0.1`. Redeploy the stack or recreate the container with that tag.

### Logs and Restart

Portainer can show container logs directly from the container details page. Use
the restart action to restart the container manually after configuration or image
changes.

## Synology Container Manager

1. Open Container Manager.
2. Create a project from `docker-compose.yml`, or create a container from
   `ghcr.io/amylasehai0z/plex-music-enhancer:latest`.
3. Map host port `1008` to container port `8080`.
4. Mount persistent folders for `/config`, `/cache` and `/logs`.
5. Set `PLEX_URL`, `PLEX_TOKEN` and `OPENAI_API_KEY`.
6. Use restart policy `unless-stopped`.
7. Check the health status and open `http://<synology>:1008/`.

## CI/CD

`.github/workflows/ci.yml` runs:

- Python installation
- Ruff
- Black
- Pytest
- frontend install
- frontend tests
- frontend build
- Python package build
- GitHub Actions artifact upload for wheel and source distribution
- Docker smoke build
- container smoke tests for `plex-enhancer --help` and `plex-enhancer serve --help`
- container health endpoint smoke test
- build report, Docker analysis and release readiness report
- multi-arch Docker build for `linux/amd64` and `linux/arm64`
- SBOM and provenance attestation
- GHCR publish for `main`, `develop` and release tags
- automatic GitHub Release creation for version tags

Pull requests and feature branches run validation without publishing images.
This keeps branch feedback fast while publishing only deployable images.
