#!/bin/sh
set -eu

APP_USER="plexenhancer"
APP_GROUP="plexenhancer"
PUID="${PUID:-10001}"
PGID="${PGID:-10001}"

if [ -n "${PLEX_URL:-}" ] && [ -z "${PLEX_ENHANCER_PLEX_URL:-}" ]; then
  export PLEX_ENHANCER_PLEX_URL="$PLEX_URL"
fi

if [ -n "${PLEX_TOKEN:-}" ] && [ -z "${PLEX_ENHANCER_PLEX_TOKEN:-}" ]; then
  export PLEX_ENHANCER_PLEX_TOKEN="$PLEX_TOKEN"
fi

CONFIG_FILE="${PLEX_ENHANCER_CONFIG:-/config/.env}"
if [ -d "$CONFIG_FILE" ]; then
  CONFIG_FILE="${CONFIG_FILE%/}/.env"
fi
if [ -f "$CONFIG_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
  set +a
fi

CONFIG_PATH="${PLEX_ENHANCER_CONFIG:-/config}"
CONFIG_DIR="$CONFIG_PATH"
if [ -d "$CONFIG_DIR" ]; then
  CONFIG_DIR="${CONFIG_DIR%/}"
else
  case "$CONFIG_DIR" in
    *.env) CONFIG_DIR="$(dirname "$CONFIG_DIR")" ;;
  esac
fi
CACHE_DIR="${PLEX_ENHANCER_CACHE:-/cache}"
EXPORTS_DIR="${PLEX_ENHANCER_EXPORTS:-${CONFIG_DIR%/}/exports}"
export PLEX_ENHANCER_EXPORTS="$EXPORTS_DIR"

if [ "$(id -u)" = "0" ]; then
  if [ "$(getent group "$APP_GROUP" | cut -d: -f3)" != "$PGID" ]; then
    groupmod -o -g "$PGID" "$APP_GROUP"
  fi
  if [ "$(id -u "$APP_USER")" != "$PUID" ]; then
    usermod -o -u "$PUID" "$APP_USER"
  fi
  mkdir -p "$CONFIG_DIR" "$CACHE_DIR" "$EXPORTS_DIR" /exports /logs /home/plexenhancer/.plex-enhancer
  chown -R "$APP_USER:$APP_GROUP" "$CONFIG_DIR" "$CACHE_DIR" "$EXPORTS_DIR" /exports /logs /home/plexenhancer
else
  mkdir -p "$CONFIG_DIR" "$CACHE_DIR" "$EXPORTS_DIR" /logs /home/plexenhancer/.plex-enhancer
fi

if [ ! -e /home/plexenhancer/.plex-enhancer/cache ]; then
  ln -s "$CACHE_DIR" /home/plexenhancer/.plex-enhancer/cache
fi

touch /logs/plex_review.log /logs/openai_prompt.txt /logs/openai_prompt_meta.json
ln -sf /logs/plex_review.log /tmp/plex_review.log
ln -sf /logs/openai_prompt.txt /tmp/openai_prompt.txt
ln -sf /logs/openai_prompt_meta.json /tmp/openai_prompt_meta.json

if [ "${1:-}" = "plex-enhancer" ]; then
  shift
fi

if [ "$(id -u)" = "0" ]; then
  exec gosu "$APP_USER" plex-enhancer "$@"
fi

exec plex-enhancer "$@"
