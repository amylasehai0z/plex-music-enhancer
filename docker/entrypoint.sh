#!/bin/sh
set -eu

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

CACHE_DIR="${PLEX_ENHANCER_CACHE:-/cache}"
mkdir -p "$CACHE_DIR" /logs /home/plexenhancer/.plex-enhancer
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

exec plex-enhancer "$@"
