# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS frontend

WORKDIR /build

COPY web/package.json web/package-lock.json ./web/
WORKDIR /build/web
RUN --mount=type=cache,target=/root/.npm npm ci

WORKDIR /build
COPY web ./web
RUN --mount=type=cache,target=/root/.npm \
    cd web \
    && npm test \
    && npm run build

FROM python:3.12-slim AS runtime

ARG VERSION=0.0.0
ARG REVISION=unknown
ARG CREATED=unknown

LABEL org.opencontainers.image.title="Plex Music Enhancer" \
      org.opencontainers.image.description="Review-first AI-assisted Plex music metadata enhancer with FastAPI web interface." \
      org.opencontainers.image.authors="Steinbecker Softwaredienst" \
      org.opencontainers.image.vendor="Steinbecker Softwaredienst" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://github.com/amylasehai0z/plex-music-enhancer" \
      org.opencontainers.image.source="https://github.com/amylasehai0z/plex-music-enhancer" \
      org.opencontainers.image.documentation="https://github.com/amylasehai0z/plex-music-enhancer#readme" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PUID=10001 \
    PGID=10001 \
    PLEX_ENHANCER_WEB__PORT=8080 \
    PLEX_ENHANCER_CONFIG=/config \
    PLEX_ENHANCER_CACHE=/cache \
    PLEX_ENHANCER_EXPORTS=/config/exports \
    PLEX_ENHANCER_LOG_LEVEL=INFO

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 plexenhancer \
    && useradd --system --uid 10001 --gid plexenhancer --home-dir /home/plexenhancer --create-home plexenhancer \
    && mkdir -p /config/exports /cache /logs /exports /music /home/plexenhancer/.plex-enhancer \
    && chown -R plexenhancer:plexenhancer /config /cache /logs /exports /music /home/plexenhancer

COPY pyproject.toml README.md LICENSE ./
COPY prompts ./prompts
COPY src ./src
COPY --from=frontend /build/src/plex_music_enhancer/web/static ./src/plex_music_enhancer/web/static
COPY docker/entrypoint.sh /usr/local/bin/plex-enhancer-entrypoint

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[web,ai,metadata]" \
    && chmod +x /usr/local/bin/plex-enhancer-entrypoint

VOLUME ["/config", "/cache", "/logs", "/exports", "/music"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/api/v1/system/health', timeout=3).read()"

ENTRYPOINT ["plex-enhancer-entrypoint"]
CMD ["serve", "--host", "0.0.0.0"]
