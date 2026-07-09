#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf "${SCRIPT_DIR}/.build"
rm -rf "${SCRIPT_DIR}/output"

printf 'Temporäre PDF-Build-Artefakte wurden entfernt.\n'
