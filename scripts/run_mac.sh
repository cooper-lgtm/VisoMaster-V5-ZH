#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found at ${VENV_DIR}."
  echo "Run: scripts/install_mac.sh"
  exit 1
fi

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
exec python main.py


