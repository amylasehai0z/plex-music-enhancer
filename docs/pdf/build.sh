#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${DOCS_DIR}/.." && pwd)"
OUTPUT="${ROOT_DIR}/Plex-Music-Enhancer-Handbuch-v1.0.pdf"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "Pandoc wurde nicht gefunden. Bitte installieren Sie Pandoc und starten Sie das Skript erneut." >&2
  exit 127
fi

pandoc \
  --metadata-file="${SCRIPT_DIR}/metadata.yaml" \
  --toc \
  --toc-depth=3 \
  --number-sections \
  --pdf-engine=xelatex \
  -o "${OUTPUT}" \
  "${DOCS_DIR}/handbuch/00-titel.md" \
  "${DOCS_DIR}/handbuch/01-einleitung.md" \
  "${DOCS_DIR}/handbuch/02-installation.md" \
  "${DOCS_DIR}/handbuch/03-erste-schritte.md" \
  "${DOCS_DIR}/handbuch/04-konfiguration.md" \
  "${DOCS_DIR}/handbuch/05-cli-befehle.md" \
  "${DOCS_DIR}/handbuch/06-workflows.md" \
  "${DOCS_DIR}/handbuch/07-ki-und-editorial-engine.md" \
  "${DOCS_DIR}/handbuch/08-review-system.md" \
  "${DOCS_DIR}/handbuch/09-provider.md" \
  "${DOCS_DIR}/handbuch/10-cache.md" \
  "${DOCS_DIR}/handbuch/11-fehlersuche.md" \
  "${DOCS_DIR}/handbuch/12-faq.md" \
  "${DOCS_DIR}/handbuch/13-glossar.md" \
  "${DOCS_DIR}/handbuch/14-anhang.md"

echo "PDF erstellt: ${OUTPUT}"
