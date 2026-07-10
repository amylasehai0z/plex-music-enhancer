"""Containerization and deployment configuration tests."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_multistage_non_root_web_runtime() -> None:
    """Dockerfile should build frontend assets and run the web app as non-root."""
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:22-bookworm-slim AS frontend" in dockerfile
    assert "npm test" in dockerfile
    assert "npm run build" in dockerfile
    assert "FROM python:3.12-slim AS runtime" in dockerfile
    assert 'python -m pip install ".[web,ai,metadata]"' in dockerfile
    assert "USER plexenhancer" in dockerfile
    assert 'CMD ["serve", "--host", "0.0.0.0"]' in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "org.opencontainers.image.source" in dockerfile
    assert "org.opencontainers.image.authors" in dockerfile
    assert "PLEX_ENHANCER_CONFIG=/config" in dockerfile


def test_docker_compose_maps_synology_port_and_volumes() -> None:
    """Compose should map host port 1008 to container port 8080 with persisted volumes."""
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["plex-music-enhancer"]

    assert service["image"] == "ghcr.io/amylasehai0z/plex-music-enhancer:latest"
    assert service["container_name"] == "plex-music-enhancer"
    assert service["restart"] == "unless-stopped"
    assert "${PLEX_ENHANCER_HOST_PORT:-1008}:8080" in service["ports"]
    assert "./docker/config:/config" in service["volumes"]
    assert "./docker/cache:/cache" in service["volumes"]
    assert "./docker/logs:/logs" in service["volumes"]
    assert service["environment"]["PLEX_ENHANCER_WEB__PORT"] == 8080
    assert service["environment"]["PLEX_ENHANCER_CONFIG"] == "${PLEX_ENHANCER_CONFIG:-/config}"
    assert service["labels"]["io.portainer.accesscontrol.public"] == "false"
    assert "healthcheck" in service


def test_env_example_documents_portainer_container_defaults() -> None:
    """Example environment should include the recommended Portainer variables."""
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    expected_variables = [
        "OPENAI_API_KEY=",
        "PLEX_URL=http://plex:32400",
        "PLEX_TOKEN=",
        "PLEX_ENHANCER_WEB__PORT=8080",
        "PLEX_ENHANCER_LOG_LEVEL=INFO",
        "PLEX_ENHANCER_CONFIG=/config",
        "PLEX_ENHANCER_CACHE=/cache",
    ]

    for variable in expected_variables:
        assert variable in env_example


def test_container_entrypoint_supports_synology_environment_aliases() -> None:
    """Entrypoint should map concise Synology variables to app-specific variables."""
    entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

    assert "PLEX_URL" in entrypoint
    assert "PLEX_TOKEN" in entrypoint
    assert "PLEX_ENHANCER_CONFIG" in entrypoint
    assert "PLEX_ENHANCER_CACHE" in entrypoint
    assert "/logs/plex_review.log" in entrypoint


def test_ghcr_workflow_builds_and_publishes_container() -> None:
    """GitHub Actions should build, test, and publish the GHCR image."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "ghcr.io/amylasehai0z/plex-music-enhancer" in workflow
    assert "docker/build-push-action" in workflow
    assert "docker/metadata-action" in workflow
    assert "docker/setup-qemu-action" in workflow
    assert "docker/setup-buildx-action" in workflow
    assert "linux/amd64,linux/arm64" in workflow
    assert "sbom: true" in workflow
    assert "provenance: true" in workflow
    assert "actions/upload-artifact" in workflow
    assert "actions/download-artifact" in workflow
    deterministic_install = " ".join(
        [
            "python -m pip install",
            "--no-cache-dir",
            "--force-reinstall",
            '".[dev,web,ai,metadata]"',
        ]
    )
    assert deterministic_install in workflow
    assert "python-dist" in workflow
    assert "build-reports" in workflow
    assert "artifacts/build_report.txt" in workflow
    assert "artifacts/docker_analysis.txt" in workflow
    assert "artifacts/release_readiness_report.txt" in workflow
    assert "docker run --rm plex-music-enhancer:smoke plex-enhancer --help" in workflow
    assert "docker run --rm plex-music-enhancer:smoke plex-enhancer serve --help" in workflow
    assert "http://127.0.0.1:18080/api/v1/system/health" in workflow
    assert "docker rm -f plex-music-enhancer-smoke" in workflow
    assert "refs/heads/develop" in workflow
    assert "Create GitHub release" in workflow
    assert "gh release create" in workflow
    assert "gh release edit" in workflow
    assert "npm test" in workflow
    assert "pytest" in workflow


def test_deployment_docs_recommend_portainer_without_automatic_updater() -> None:
    """Deployment documentation should recommend Portainer and avoid legacy auto-updaters."""
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "docker.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "handbuch" / "15-container.md").read_text(encoding="utf-8"),
        ]
    )

    assert "Portainer" in docs
    assert "linux/amd64" in docs
    assert "linux/arm64" in docs
    assert "SBOM" in docs
    assert "docker build -t plex-music-enhancer:local ." in docs
    assert "docker run --rm plex-music-enhancer:local plex-enhancer --help" in docs
    assert "docker compose config" in docs
    legacy_updater_name = "Watch" + "tower"
    assert legacy_updater_name not in docs
    assert legacy_updater_name.lower() not in docs
