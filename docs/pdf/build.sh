#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${DOCS_DIR}/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/assets/pdf"
BUILD_DIR="${SCRIPT_DIR}/.build"
OUTPUT="${OUTPUT_DIR}/Plex-Music-Enhancer-Handbuch.pdf"
TITLE_PAGE="${SCRIPT_DIR}/titlepage.md"
METADATA_FILE="${SCRIPT_DIR}/metadata.yaml"
VARIABLES_FILE="${SCRIPT_DIR}/variables.yaml"
TEMPLATE_FILE="${SCRIPT_DIR}/eisvogel.tex"
RESOLVED_VARIABLES_FILE="${BUILD_DIR}/resolved-variables.yaml"
HANDBOOK_DIR="${DOCS_DIR}/handbuch"
LOGO_FILE="${ROOT_DIR}/assets/logo/plex-music-enhancer-logo.pdf"

CHAPTERS=(
  "00-titel.md"
  "01-einleitung.md"
  "02-installation.md"
  "03-erste-schritte.md"
  "04-konfiguration.md"
  "05-cli-befehle.md"
  "06-workflows.md"
  "07-ki-und-editorial-engine.md"
  "08-review-system.md"
  "09-provider.md"
  "10-cache.md"
  "11-fehlersuche.md"
  "12-faq.md"
  "13-glossar.md"
  "14-anhang.md"
)

log() {
  printf '==> %s\n' "$1"
}

fail() {
  printf 'Fehler: %s\n' "$1" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

font_available() {
  local font_name="$1"
  local font_test_dir
  local font_test_file
  local font_test_log

  font_test_dir="$(mktemp -d "${BUILD_DIR}/font-test.XXXXXX")"
  font_test_file="${font_test_dir}/font-test.tex"
  font_test_log="${font_test_dir}/font-test.log"

  cat >"$font_test_file" <<EOF
\\documentclass{article}
\\usepackage{fontspec}
\\begin{document}
\\IfFontExistsTF{${font_name}}{\\typeout{PME_FONT_FOUND}}{\\typeout{PME_FONT_MISSING}}
\\end{document}
EOF

  xelatex -interaction=batchmode -halt-on-error -output-directory="$font_test_dir" "$font_test_file" >/dev/null 2>&1 || return 1
  grep -q "PME_FONT_FOUND" "$font_test_log"
}

choose_font() {
  local font_name

  for font_name in "$@"; do
    if font_available "$font_name"; then
      printf '%s\n' "$font_name"
      return 0
    fi
  done

  printf '\n'
}

verify_command() {
  local command_name="$1"
  local install_hint="$2"

  if ! command_exists "$command_name"; then
    fail "${command_name} wurde nicht gefunden. ${install_hint}"
  fi
}

verify_file() {
  local path="$1"

  [[ -f "$path" ]] || fail "Erforderliche Datei fehlt: ${path}"
}

cleanup() {
  rm -rf "$BUILD_DIR"
}

trap cleanup EXIT

log "Pruefe Build-Werkzeuge"
verify_command "pandoc" "Installieren Sie Pandoc: https://pandoc.org/installing.html"
verify_command "xelatex" "Installieren Sie eine TeX-Distribution mit XeLaTeX, zum Beispiel MacTeX oder TeX Live."

log "Pruefe Dokumentationsdateien"
verify_file "$TITLE_PAGE"
verify_file "$METADATA_FILE"
verify_file "$VARIABLES_FILE"
verify_file "$TEMPLATE_FILE"
verify_file "$LOGO_FILE"

INPUT_FILES=("$TITLE_PAGE")
for chapter in "${CHAPTERS[@]}"; do
  chapter_path="${HANDBOOK_DIR}/${chapter}"
  verify_file "$chapter_path"
  INPUT_FILES+=("$chapter_path")
done
verify_file "${SCRIPT_DIR}/appendix.md"
INPUT_FILES+=("${SCRIPT_DIR}/appendix.md")

log "Bereite Ausgabeordner vor"
mkdir -p "$OUTPUT_DIR" "$BUILD_DIR"
rm -f "$OUTPUT"

MAIN_FONT="$(choose_font "Noto Serif" "TeX Gyre Pagella" "DejaVu Serif")"
SANS_FONT="$(choose_font "Noto Sans" "TeX Gyre Heros" "DejaVu Sans")"
MONO_FONT="$(choose_font "JetBrains Mono" "DejaVu Sans Mono" "Inconsolata")"

log "Verwende Schriften: ${MAIN_FONT:-XeLaTeX-Standard}, ${SANS_FONT:-XeLaTeX-Standard}, ${MONO_FONT:-XeLaTeX-Standard}"
: >"$RESOLVED_VARIABLES_FILE"
if [[ -n "$MAIN_FONT" ]]; then
  printf 'mainfont: "%s"\n' "$MAIN_FONT" >>"$RESOLVED_VARIABLES_FILE"
fi
if [[ -n "$SANS_FONT" ]]; then
  printf 'sansfont: "%s"\n' "$SANS_FONT" >>"$RESOLVED_VARIABLES_FILE"
fi
if [[ -n "$MONO_FONT" ]]; then
  printf 'monofont: "%s"\n' "$MONO_FONT" >>"$RESOLVED_VARIABLES_FILE"
fi

log "Erzeuge PDF"
pandoc \
  --from=markdown+smart+fenced_divs+link_attributes+implicit_figures \
  --template="$TEMPLATE_FILE" \
  --metadata-file="$METADATA_FILE" \
  --metadata-file="$VARIABLES_FILE" \
  --metadata-file="$RESOLVED_VARIABLES_FILE" \
  --toc-depth=3 \
  --number-sections \
  --syntax-highlighting=tango \
  --pdf-engine=xelatex \
  --pdf-engine-opt=-shell-escape \
  --resource-path="${ROOT_DIR}:${DOCS_DIR}:${SCRIPT_DIR}" \
  -o "$OUTPUT" \
  "${INPUT_FILES[@]}"

cleanup

if [[ ! -s "$OUTPUT" ]]; then
  fail "PDF wurde nicht erzeugt: ${OUTPUT}"
fi

log "PDF erfolgreich erstellt"
printf 'Datei: %s\n' "$OUTPUT"
printf 'Logo: %s\n' "$LOGO_FILE"
printf 'Kapitel: %s\n' "${#CHAPTERS[@]}"
printf 'Format: A4, XeLaTeX, klickbares Inhaltsverzeichnis, Kopf- und Fusszeilen\n'
